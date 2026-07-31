import PyOpenColorIO as ocio
import os
import sys
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless/script usage
import matplotlib.pyplot as plt

def get_lut_size_from_file(lut_path):
    """Reads the LUT_3D_SIZE from a .cube file header."""
    try:
        with open(lut_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                # Use regex to find LUT_3D_SIZE followed by a number
                match = re.match(r'^LUT_3D_SIZE\s+(\d+)', line, re.IGNORECASE)
                if match:
                    return int(match.group(1))
                # Stop reading after finding the first non-comment, non-empty line
                # if it wasn't the LUT size (or if we found it).
                # Assumes LUT_3D_SIZE is near the top.
                if not line.startswith('DOMAIN_MIN') and not line.startswith('DOMAIN_MAX') and not line.startswith('TITLE'):
                     break # Avoid reading the whole data table
    except Exception as e:
        print(f"Warning: Could not read LUT size from {lut_path}: {e}")
    return None # Return None if size not found or error occurs

def _create_ocio_processor(lut_path):
    """Create an OCIO CPUProcessor that applies the LUT as a forward transform.

    Args:
        lut_path (str): Path to a .cube LUT file.

    Returns:
        ocio.CPUProcessor: Processor that applies the LUT to RGB arrays.
    """
    config = ocio.Config()
    raw_cs = ocio.ColorSpace(name="raw")
    config.addColorSpace(raw_cs)
    config.setRole(ocio.ROLE_SCENE_LINEAR, "raw")

    lut_cs = ocio.ColorSpace(name="lut_cs")
    ft = ocio.FileTransform(lut_path, interpolation=ocio.INTERP_LINEAR)
    lut_cs.setTransform(ft, ocio.COLORSPACE_DIR_FROM_REFERENCE)
    config.addColorSpace(lut_cs)

    processor = config.getProcessor("raw", "lut_cs")
    return processor.getDefaultCPUProcessor()


def compute_roundtrip_error(forward_path, reversed_path, grid_size):
    """Compute the round-trip error for every grid point in a 3D LUT.

    For each grid point (r,g,b) in [0,1]^3:
        1. Apply the forward LUT to get (r',g',b')
        2. Apply the reversed LUT to (r',g',b') to get (r'',g'',b'')
        3. Error = Euclidean distance between (r,g,b) and (r'',g'',b'')

    Args:
        forward_path (str): Path to the original .cube LUT file.
        reversed_path (str): Path to the reversed .cube LUT file.
        grid_size (int): The resolution of the LUT grid (N).

    Returns:
        tuple: (error_3d, original, forward, roundtrip)
            error_3d  — (N, N, N) array of Euclidean errors, indexed [R][G][B]
            original  — (N, N, N, 3) array of original grid coordinates
            forward   — (N, N, N, 3) array of forward LUT outputs
            roundtrip — (N, N, N, 3) array of round-tripped values
    """
    print("Loading forward LUT processor...")
    fwd_cpu = _create_ocio_processor(forward_path)
    print("Loading reversed LUT processor...")
    rev_cpu = _create_ocio_processor(reversed_path)

    # Generate all grid points as a flat array of shape (N^3, 3)
    grid = np.linspace(0.0, 1.0, grid_size, dtype=np.float32)
    R, G, B = np.meshgrid(grid, grid, grid, indexing='ij')
    points = np.stack([R.ravel(), G.ravel(), B.ravel()], axis=1)

    print(f"Evaluating {len(points)} grid points (forward pass)...")
    fwd_output = points.copy()
    fwd_cpu.applyRGB(fwd_output)

    print(f"Evaluating {len(points)} grid points (reverse pass)...")
    rev_output = fwd_output.copy()
    rev_cpu.applyRGB(rev_output)

    # Euclidean distance per point
    diff = points - rev_output
    errors = np.sqrt(np.sum(diff ** 2, axis=1))

    # Reshape to 3D grid indexed as [R][G][B]
    shape_3d = (grid_size, grid_size, grid_size)
    shape_4d = (grid_size, grid_size, grid_size, 3)

    return (errors.reshape(shape_3d),
            points.reshape(shape_4d),
            fwd_output.reshape(shape_4d),
            rev_output.reshape(shape_4d))


def generate_irreversibility_map(error_3d, grid_size, output_dir, lut_name):
    """Generate grayscale PNG slices showing irreversibility across the LUT.

    Creates one PNG per blue-channel slice, plus a max-projection summary
    image and an error histogram.

    Args:
        error_3d (np.ndarray): (N, N, N) array of Euclidean errors [R][G][B].
        grid_size (int): The resolution of the LUT grid (N).
        output_dir (str): Directory to save the PNG files.
        lut_name (str): Base name of the LUT (used in filenames).
    """
    os.makedirs(output_dir, exist_ok=True)
    global_max = float(np.max(error_3d))
    global_mean = float(np.mean(error_3d))

    print(f"  Error range: [{float(np.min(error_3d)):.6f}, {global_max:.6f}]")
    print(f"  Mean error:  {global_mean:.6f}")

    # --- Per-blue-slice grayscale images ---
    for b in range(grid_size):
        slice_data = error_3d[:, :, b]
        blue_val = b / (grid_size - 1)

        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(slice_data, cmap='gray', vmin=0, vmax=global_max,
                       origin='lower', aspect='equal', interpolation='nearest')
        cbar = plt.colorbar(im, ax=ax, label='Round-trip error (Euclidean)')
        cbar.ax.yaxis.label.set_color('white')
        cbar.ax.tick_params(colors='white')
        ax.set_xlabel('Red index', color='white')
        ax.set_ylabel('Green index', color='white')
        ax.set_title(f'Blue = {blue_val:.3f}', color='white', fontsize=11)
        ax.tick_params(colors='white')
        fig.patch.set_facecolor('#1e1e1e')
        ax.set_facecolor('#1e1e1e')

        slice_path = os.path.join(output_dir, f'{lut_name}_slice_b{b:03d}.png')
        fig.savefig(slice_path, dpi=150, bbox_inches='tight',
                    facecolor='#1e1e1e', edgecolor='none')
        plt.close(fig)

    print(f"  Saved {grid_size} slice images to: {output_dir}")

    # --- Max-projection summary image ---
    max_proj = np.max(error_3d, axis=2)  # max across blue axis
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(max_proj, cmap='gray', vmin=0, vmax=global_max,
                   origin='lower', aspect='equal', interpolation='nearest')
    cbar = plt.colorbar(im, ax=ax, label='Max round-trip error (Euclidean)')
    cbar.ax.yaxis.label.set_color('white')
    cbar.ax.tick_params(colors='white')
    ax.set_xlabel('Red index', color='white')
    ax.set_ylabel('Green index', color='white')
    ax.set_title('Max error across all blue slices', color='white', fontsize=11)
    ax.tick_params(colors='white')
    fig.patch.set_facecolor('#1e1e1e')
    ax.set_facecolor('#1e1e1e')

    summary_path = os.path.join(output_dir, f'{lut_name}_max_projection.png')
    fig.savefig(summary_path, dpi=150, bbox_inches='tight',
                facecolor='#1e1e1e', edgecolor='none')
    plt.close(fig)
    print(f"  Saved max-projection summary: {summary_path}")

    # --- Error histogram ---
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(error_3d.ravel(), bins=100, color='#888888', edgecolor='none')
    ax.axvline(global_mean, color='white', linestyle='--', linewidth=1,
               label=f'Mean = {global_mean:.6f}')
    ax.set_xlabel('Round-trip error', color='white')
    ax.set_ylabel('Frequency', color='white')
    ax.set_title('Error distribution', color='white', fontsize=11)
    ax.legend(loc='upper right', facecolor='#1e1e1e', edgecolor='none',
              labelcolor='white')
    ax.tick_params(colors='white')
    fig.patch.set_facecolor('#1e1e1e')
    ax.set_facecolor('#1e1e1e')

    hist_path = os.path.join(output_dir, f'{lut_name}_error_histogram.png')
    fig.savefig(hist_path, dpi=150, bbox_inches='tight',
                facecolor='#1e1e1e', edgecolor='none')
    plt.close(fig)
    print(f"  Saved error histogram: {hist_path}")


def reverse_lut(input_lut_path, output_lut_path, cube_size=33):
    """
    Reverses a 3D LUT file using OpenColorIO.

    Args:
        input_lut_path (str): Path to the input .cube LUT file.
        output_lut_path (str): Path to save the reversed .cube LUT file.
        cube_size (int): The resolution of the output reversed LUT.
    """
    if not os.path.exists(input_lut_path):
        print(f"Error: Input LUT file not found: {input_lut_path}")
        return

    try:
        # Create an empty config
        config = ocio.Config()

        # Define a basic "raw" color space to act as the reference
        raw_cs_name = "raw"
        raw_cs = ocio.ColorSpace(name=raw_cs_name, description="Linear reference space")
        config.addColorSpace(raw_cs)
        # Assign the scene_linear role to our "raw" space
        config.setRole(ocio.ROLE_SCENE_LINEAR, raw_cs_name)

        # Define the forward transform (reading the LUT)
        forward_transform = ocio.FileTransform(input_lut_path, interpolation=ocio.INTERP_LINEAR)

        # Create a temporary color space
        temp_cs_name = "temp_lut_colorspace"
        temp_cs = ocio.ColorSpace(name=temp_cs_name)
        # Set the transform FROM reference (raw) TO this space using the forward LUT
        temp_cs.setTransform(forward_transform, ocio.COLORSPACE_DIR_FROM_REFERENCE)
        config.addColorSpace(temp_cs)

        # Create a Baker
        baker = ocio.Baker()
        baker.setConfig(config)
        baker.setFormat("cinespace")
        baker.setCubeSize(cube_size)

        # Set the input space to the temporary space and target to the reference (raw/scene_linear).
        # Baking FROM temp_cs TO raw will now generate the inverse of the forward_transform.
        baker.setInputSpace(temp_cs_name)
        baker.setTargetSpace(ocio.ROLE_SCENE_LINEAR)

        # Bake the LUT data using the cinespace format
        baked_output_string = baker.bake()

        # --- Filter the baked output to get only numerical data lines ---
        numerical_data_lines = []
        for line in baked_output_string.splitlines():
            line = line.strip()
            # Skip lines that look like LUT size declarations (e.g. "4 4 4")
            if re.match(r'^\d+\s+\d+\s+\d+$', line):
                continue
            # Basic check: does the line contain roughly 3 space-separated numbers?
            parts = line.split()
            if len(parts) == 3:
                try:
                    # Attempt to convert to float to ensure they are numbers
                    float(parts[0])
                    float(parts[1])
                    float(parts[2])
                    numerical_data_lines.append(line)
                except ValueError:
                    # Line parts are not all numbers, skip
                    continue
        # Join the valid lines back together
        cleaned_lut_data = "\n".join(numerical_data_lines)
        # --- End Filtering ---

        # Construct a minimal standard .cube header
        input_filename_base = os.path.basename(input_lut_path)
        title = f"Reversed - {input_filename_base}"
        header = f"""TITLE "{title}"
# Created by LUTReverser script

LUT_3D_SIZE {cube_size}
DOMAIN_MIN 0.0 0.0 0.0
DOMAIN_MAX 1.0 1.0 1.0
""" # Ends with a newline

        # Write the header and the cleaned numerical data to the output file using CRLF line endings
        with open(output_lut_path, 'w', newline='\r\n') as f:
            f.write(header)
            # Add the blank line separator if the header doesn't end with one (it does)
            # f.write('\n') # Header already ends with \n
            f.write(cleaned_lut_data)
            # Ensure the file ends with a newline
            if not cleaned_lut_data.endswith('\n'):
                 f.write('\n')

        print(f"Successfully reversed LUT saved to: {output_lut_path}")

    except Exception as e:
        print(f"An error occurred during LUT reversal: {e}")

if __name__ == "__main__":
    def print_usage():
        print("""
Usage: python lut_reverser.py <input_lut> [output_lut] [cube_size] [--map [output_dir]]

Arguments:
    input_lut       - Path to the input .cube LUT file
    output_lut      - (Optional) Path to save the reversed .cube LUT file
    cube_size       - (Optional) Resolution of the output LUT (default: 33)
    --map [dir]     - (Optional) Generate a monochromatic irreversibility map.
                      If dir is omitted, saves to '<input_name>_analysis/'.

Examples:
    python lut_reverser.py input.cube
    python lut_reverser.py input.cube output_reversed.cube 64
    python lut_reverser.py input.cube --map
    python lut_reverser.py input.cube output.cube 64 --map analysis_dir
""")

    default_cube_size = 33
    input_filename = None
    output_filename = None
    output_cube_size = None
    map_output_dir = None  # None means no map generation

    # Parse arguments, handling --map flag
    args = sys.argv[1:]  # skip script name
    # Check for --map and extract its value
    if '--map' in args:
        map_idx = args.index('--map')
        # Remove --map and its optional argument from args
        args.pop(map_idx)
        if map_idx < len(args) and not args[map_idx].startswith('-'):
            map_output_dir = args.pop(map_idx)
        else:
            map_output_dir = ''  # Will be resolved to default later
        # Reconstruct sys.argv-like list for remaining parsing
        remaining = [sys.argv[0]] + args
    else:
        remaining = sys.argv

    # Check command line arguments (using filtered args)
    if len(remaining) == 1:
        print("Error: No input file specified.")
        print_usage()
        sys.exit(1)
    elif len(remaining) == 2:
        input_filename = remaining[1]
        base, ext = os.path.splitext(input_filename)
        output_filename = f"{base}_reversed{ext}"
        print(f"Output filename not provided. Using: '{output_filename}'")
    else:
        input_filename = remaining[1]
        output_filename = remaining[2]
        if len(remaining) > 3:
            try:
                output_cube_size = int(remaining[3])
                print(f"Using specified cube size: {output_cube_size}")
            except ValueError:
                print(f"Warning: Invalid cube size argument '{remaining[3]}'. Will attempt to read from input or use default.")
                output_cube_size = None

    # --- Determine Paths ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(input_filename):
        input_lut_path = os.path.join(script_dir, input_filename)
    else:
        input_lut_path = input_filename

    if not os.path.isabs(output_filename):
        output_lut_path = os.path.join(script_dir, output_filename)
    else:
        output_lut_path = output_filename

    # Check if input file exists
    if not os.path.exists(input_lut_path):
        print(f"Error: Input LUT file not found: {input_lut_path}")
        print_usage()
        sys.exit(1)

    # --- Determine Cube Size ---
    if output_cube_size is None: # If not specified via command line
        print(f"Attempting to read cube size from input file: {input_lut_path}")
        if os.path.exists(input_lut_path):
            read_size = get_lut_size_from_file(input_lut_path)
            if read_size:
                output_cube_size = read_size
                print(f"Using cube size from input file: {output_cube_size}")
            else:
                output_cube_size = default_cube_size
                print(f"Could not read cube size from input file. Using default: {output_cube_size}")
        else:
             output_cube_size = default_cube_size
             print(f"Input file not found yet. Using default cube size: {output_cube_size}")
    # --- End Determine Cube Size ---


    # Reverse the LUT using the determined size
    reverse_lut(input_lut_path, output_lut_path, output_cube_size)

    # --- Generate irreversibility map if requested ---
    if map_output_dir is not None:
        # Resolve output directory
        if not map_output_dir:
            input_base = os.path.splitext(os.path.basename(input_lut_path))[0]
            map_output_dir = os.path.join(script_dir, f"{input_base}_analysis")
        elif not os.path.isabs(map_output_dir):
            map_output_dir = os.path.join(script_dir, map_output_dir)

        print(f"\nGenerating irreversibility map in: {map_output_dir}")
        print("Computing round-trip error analysis...")
        try:
            error_3d, original, fwd, rnd = compute_roundtrip_error(
                input_lut_path, output_lut_path, output_cube_size
            )
            lut_name = os.path.splitext(os.path.basename(input_lut_path))[0]
            generate_irreversibility_map(error_3d, output_cube_size,
                                         map_output_dir, lut_name)
            print("Irreversibility map generation complete.")
        except Exception as e:
            print(f"Error generating irreversibility map: {e}")

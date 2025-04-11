import PyOpenColorIO as ocio
import os
import sys

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
    # Check if enough arguments are provided
    if len(sys.argv) < 3:
        print("Usage: python lut_reverser.py <input_lut_path> <output_lut_path> [cube_size]")
        # Use default filenames if no arguments are given, for backward compatibility or direct run
        print("Using default filenames: 'filename.cube' and 'filename_reversed.cube'")
        input_filename = "filename.cube" # Default input
        output_filename = "filename_reversed.cube" # Default output
        output_cube_size = 33 # Default cube size
    else:
        # Get input and output filenames from command line arguments
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
        # Optionally get cube size from the third argument
        output_cube_size = int(sys.argv[3]) if len(sys.argv) > 3 else 33


    # Construct full paths (assuming the script is run from the LUTReverser directory
    # or paths provided are absolute/relative to the CWD)
    # If relative paths are provided as args, they are relative to the CWD
    # If running from VS Code debugger, CWD is usually the workspace root.
    script_dir = os.path.dirname(os.path.abspath(__file__)) # Keep this for context if needed

    # Determine if provided filenames are absolute paths
    if not os.path.isabs(input_filename):
        input_lut_path = os.path.join(script_dir, input_filename) # Assume relative to script dir if not absolute
    else:
        input_lut_path = input_filename

    if not os.path.isabs(output_filename):
        output_lut_path = os.path.join(script_dir, output_filename) # Assume relative to script dir if not absolute
    else:
        output_lut_path = output_filename


    # --- Placeholder Check ---
    # In a real scenario, you would have the input file available.
    # This check might need adjustment depending on whether you expect
    # the script to create a dummy file when run with arguments.
    # For now, we only create the dummy if using the *default* filename and it's missing.
    if input_filename == "filename.cube" and not os.path.exists(input_lut_path):
        print(f"Warning: Default input file '{input_filename}' not found. Creating a dummy identity LUT for demonstration.")
        try:
            identity_lut_content = """# Created by LUTReverser Placeholder
TITLE "Identity 1D LUT"
LUT_1D_SIZE 2
0.0 0.0 0.0
1.0 1.0 1.0
"""
            with open(input_lut_path, 'w') as f:
                f.write(identity_lut_content)
            print(f"Created dummy LUT: {input_lut_path}")
        except Exception as e:
            print(f"Error creating dummy LUT: {e}")
            sys.exit(1) # Exit if we can't even create the dummy file
    # --- End Placeholder Check ---


    # Set the desired cube size for the output LUT (already set based on args or default)
    # output_cube_size = 33 # Removed, now set above

    # Reverse the LUT
    reverse_lut(input_lut_path, output_lut_path, output_cube_size)

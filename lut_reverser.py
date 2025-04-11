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
        # We need the forward transform to define the 'to_reference' direction
        # for our temporary color space. The baker will then invert this path.
        forward_transform = ocio.FileTransform(input_lut_path, interpolation=ocio.INTERP_LINEAR)
        # Note: We don't set direction to inverse here. We define a space using the forward LUT.

        # Create a temporary color space representing the output of the forward LUT
        temp_cs_name = "temp_lut_colorspace"
        temp_cs = ocio.ColorSpace(name=temp_cs_name)
        temp_cs.setTransform(forward_transform, ocio.COLORSPACE_DIR_TO_REFERENCE) # Applies LUT going TO reference (raw)
        config.addColorSpace(temp_cs)

        # Create a Baker
        baker = ocio.Baker()
        baker.setConfig(config)
        baker.setFormat("cinespace") # Format for .cube files
        baker.setCubeSize(cube_size)

        # Set the input space to the temporary space and target to the reference (raw/scene_linear).
        # This tells the baker to generate a LUT that transforms FROM temp_cs TO raw,
        # effectively reversing the original forward_transform.
        baker.setInputSpace(temp_cs_name)
        baker.setTargetSpace(ocio.ROLE_SCENE_LINEAR) # Use the role we just defined

        # Bake the LUT to a string
        # This will bake the inverse of the transform defined in temp_cs
        baked_lut_string = baker.bake()

        # Write the baked LUT string to the output file
        with open(output_lut_path, 'w') as f:
            f.write(baked_lut_string)

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

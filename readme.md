# LUTReverser

LUTReverser is a Python-based tool for reversing 3D LUT (Look-Up Table) files in `.cube` format. It uses the OpenColorIO library to process LUTs and generate reversed LUTs with customizable resolution.

## Features

- Reverse `.cube` LUT files to create their inverse.
- Automatically detect the LUT size from the input file or specify a custom size.
- Generate a minimal `.cube` file with a standard header.
- Includes a placeholder identity LUT for testing purposes.

## Requirements

- Python 3.6 or higher
- [OpenColorIO](https://opencolorio.org/) library
- A `.cube` LUT file to process

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/LUTReverser.git
   cd LUTReverser
   ```

2. Install the required dependencies:
   ```bash
   pip install PyOpenColorIO
   ```

3. Verify the installation by running the script:
   ```bash
   python lut_reverser.py
   ```

## Usage

### Command-Line Arguments

The script can be run from the command line with the following arguments:

```bash
python lut_reverser.py <input_lut> <output_lut> [cube_size]
```

- `<input_lut>`: Path to the input `.cube` LUT file.
- `<output_lut>`: Path to save the reversed `.cube` LUT file.
- `[cube_size]` (optional): Resolution of the output LUT. If not provided, the script will attempt to read the size from the input file or use the default size of 33.

### Examples

1. Reverse a LUT with default settings:
   ```bash
   python lut_reverser.py input.cube output_reversed.cube
   ```

2. Reverse a LUT with a custom cube size:
   ```bash
   python lut_reverser.py input.cube output_reversed.cube 64
   ```

3. Run the script without arguments (uses default filenames):
   ```bash
   python lut_reverser.py
   ```

### Placeholder Identity LUT

If the input LUT file is missing and the default filename (`filename.cube`) is used, the script will generate a placeholder identity LUT for demonstration purposes.

## How It Works

1. **Input Validation**: The script checks if the input LUT file exists. If not, it creates a placeholder LUT if using the default filename.
2. **LUT Size Detection**: Attempts to read the `LUT_3D_SIZE` from the input file. If unavailable, defaults to a size of 33.
3. **Reversal Process**: Uses OpenColorIO to reverse the LUT and bake the output.
4. **Output Generation**: Writes the reversed LUT to the specified output file with a standard `.cube` header.

## Notes

- The script assumes that the input LUT file is in `.cube` format and follows standard conventions.
- The output LUT file is saved with CRLF line endings for compatibility with most LUT processing tools.

## Troubleshooting

- **Error: Input LUT file not found**: Ensure the input file path is correct and the file exists.
- **Warning: Could not read LUT size**: The input file may not contain a valid `LUT_3D_SIZE` header. Specify the cube size manually as a command-line argument.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgments

- [OpenColorIO](https://opencolorio.org/) for providing the tools to process LUTs.
- The Python community for their support and resources.


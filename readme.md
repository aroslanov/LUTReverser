# LUTReverser

> **Disclaimer**: In most cases, applying a LUT irreversibly alters the original colors due to the lossy nature of LUT transformations. LUTs map input colors to output colors in a finite resolution grid, and intermediate values are interpolated. This process can result in loss of detail and color information, making a full and accurate reversal impossible. LUTReverser attempts to approximate the inverse transformation, but the results may not perfectly restore the original image.

## Features

- Reverse `.cube` LUT files to create their inverse.
- Automatically detect the LUT size from the input file or specify a custom size.
- Generate a minimal `.cube` file with a standard header.
- **Irreversibility map** — visualize where the LUT loses information using color heatmaps (`--map` flag, `--grayscale` for monochrome).

## Requirements

- Python 3.6 or higher
- [OpenColorIO](https://opencolorio.org/) library
- [NumPy](https://numpy.org/) and [Matplotlib](https://matplotlib.org/) (for `--map` feature)
- A `.cube` LUT file to process

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/LUTReverser.git
   cd LUTReverser
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify the installation by running the script:
   ```bash
   python lut_reverser.py
   ```

## Usage

### Command-Line Arguments

The script can be run from the command line with the following arguments:

```bash
python lut_reverser.py <input_lut> [output_lut] [cube_size] [--map [output_dir]] [--grayscale]
```

- `<input_lut>`: Path to the input `.cube` LUT file.
- `[output_lut]` (optional): Path to save the reversed `.cube` LUT file. Defaults to `<input>_reversed.cube`.
- `[cube_size]` (optional): Resolution of the output LUT. If not provided, the script will attempt to read the size from the input file or use the default size of 33.
- `--map [output_dir]` (optional): After reversal, perform a round-trip error analysis and generate an **irreversibility map** — a set of PNG images showing where the LUT loses information. Uses a color heatmap (`inferno` colormap) by default. If `output_dir` is omitted, images are saved to `<input_name>_analysis/`.
- `--grayscale` (optional): Use grayscale instead of the default color heatmap. Only meaningful with `--map`.

### Examples

1. Reverse a LUT with default settings:
   ```bash
   python lut_reverser.py input.cube
   ```

2. Reverse a LUT with a custom cube size:
   ```bash
   python lut_reverser.py input.cube output_reversed.cube 64
   ```

3. Reverse a LUT and generate an irreversibility map (color heatmap):
   ```bash
   python lut_reverser.py input.cube --map
   ```

4. Reverse and generate a grayscale irreversibility map:
   ```bash
   python lut_reverser.py input.cube --map --grayscale
   ```

5. Reverse and save the map to a custom directory:
   ```bash
   python lut_reverser.py input.cube output.cube 64 --map my_analysis
   ```

## How It Works

1. **Input Validation**: The script checks if the input LUT file exists.
2. **LUT Size Detection**: Attempts to read the `LUT_3D_SIZE` from the input file. If unavailable, defaults to a size of 33.
3. **Reversal Process**: Uses OpenColorIO to reverse the LUT and bake the output.
4. **Output Generation**: Writes the reversed LUT to the specified output file with a standard `.cube` header.
5. **Irreversibility Map** (`--map`): Performs a **round-trip error analysis** — for every grid point in the 3D LUT, it applies the forward LUT, then the reversed LUT, and measures the Euclidean distance between the original and the round-tripped value. The result is rendered as PNG images (color heatmap by default, add `--grayscale` for monochrome):
   - **Slice images**: One per blue-channel level, showing error across the red-green plane.
   - **Max-projection summary**: The maximum error across all blue slices.
   - **Error histogram**: Distribution of all round-trip errors.

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


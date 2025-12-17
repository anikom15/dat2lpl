# dat2lpl

This tool converts DAT XML files (such as those used by No-Intro) into LPL JSON playlists compatible with RetroArch.

## Current Limitations
- **Designed for No-Intro style sets only**: The script expects the input DAT and ROM directory structure to follow the conventions of No-Intro sets. It is not tested on multifile ROM sets (like MAME) and may not work with other DAT formats.
- Only the first ROM entry per game is used in the playlist.
- Input path must be specified via command-line arguments.

## Usage


```
python dat2lpl.py <input_dat.xml> --input-path <ROM_ROOT_PATH> [--archive-format {None,.zip,.7z}] [-s {Non-merged,Split,Merged}] [-o output.lpl] [-r] [--map MAPFILE] [--map-world] [-v] [--enable-network-validation]
```

- `<input_dat.xml>`: Path to the No-Intro style DAT XML file.
- `--input-path`: Root directory where ROMs are stored (required).
- `--archive-format`: Archive format for ROMs (`None`, `.zip`, or `.7z`). Default is `.7z`.
- `-s`, `--storage-mode`: ROM storage mode: `Non-merged`, `Split`, or `Merged`. Default is `Merged`.
- `-o`, `--output`: Output LPL file name. Default is `output.lpl`.
- `-r`, `--region-split`: Produce separate output files by region.
- `--map`: JSON file mapping country/region to output value (requires `-r`).
- `--map-world`: Treat 'World' like any other region (do not add to all output files).
- `-v`, `--verbose`: Enable verbose output.
- `--enable-network-validation`: Allow network access for XML schema validation.

## Example

```
python dat2lpl.py sample.dat --input-path ".\ROM\Nintendo - Super Nintendo Entertainment System" --archive-format .7z -s Merged -v
```


Region split example:

```
python dat2lpl.py sample.dat --input-path ".\ROM\Nintendo - Super Nintendo Entertainment System" --archive-format .7z -r --map snes-country2standard.json -v
```

To treat 'World' as a normal region (not added to all outputs):

```
python dat2lpl.py sample.dat --input-path ".\ROM\Nintendo - Super Nintendo Entertainment System" --archive-format .7z -r --map snes-country2standard.json --map-world -v
```

## Output
- Produces an LPL playlist file suitable for use with RetroArch.
- If `--region-split` is used, produces one LPL file per region (according to the mapping file), plus a file for games with no region.

## License
See COPYING for license information.

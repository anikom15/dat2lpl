# dat2lpl

This tool converts DAT XML files (such as those used by No-Intro) into LPL JSON playlists compatible with RetroArch.

## Current Limitations
- **Designed for merged No-Intro style sets only**: The script expects the input DAT and ROM directory structure to follow the conventions of merged No-Intro sets. It is not intended for split or non-merged sets, or for other DAT formats.
- Only the first ROM entry per game is used in the playlist.
- Archive format and input path must be specified via command-line arguments.

## Usage

```
python dat2lpl.py <input_dat.xml> --input-path <ROM_ROOT_PATH> [--archive-format {None,.zip,.7z}] [-o output.lpl] [-v]
```

- `<input_dat.xml>`: Path to the No-Intro style DAT XML file.
- `--input-path`: Root directory where ROMs are stored (required).
- `--archive-format`: Archive format for ROMs (`None`, `.zip`, or `.7z`). Default is `.7z`.
- `-o`: Output LPL file name. Default is `output.lpl`.
- `-v`: Enable verbose output.

## Example

```
python dat2lpl.py sample.dat --input-path "E:\ROM\No-Intro\Nintendo - Super Nintendo Entertainment System" --archive-format .7z -v
```

## Output
- Produces an LPL playlist file suitable for use with RetroArch.

## License
See COPYING for license information.

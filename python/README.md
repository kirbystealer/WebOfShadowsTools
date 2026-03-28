### About

This is a Python CLI tool/library for reading Spiderman: Web of Shadows files. 

### Quickstart
I'll assume you're using uv, but of course you don't have to.

You can install the latest version of this library directly from the wheel in the Releases section:

`uv pip install "https://github.com/kirbystealer/WebOfShadowsTools/releases/latest/download/wos-0.2.0-py3-none-any.whl"`

Or to install from source, you can clone the repo and run:

`uv pip install -e "path/to/this/src/dir"`

#### Some example commands:
List all the files in `MEGACITY.PCPACK`:

`uv run unpack_wos "path\to\MEGACITY.PCPACK"`

List all the files in all PACKS in a directory, including APKs:

`uv run unpack_wos -apk "path\to\spiderman\image\pc\packs"`

Extract all the files from all PACKS in a directory, including APKs and prepending file index:

`uv run unpack_wos -apk -pfi -e "path\to\spiderman\image\pc\packs" "your\extraction\path"`

### Features

| Pack Type | Unpack | Unpack APKs | Repack |
|-----------|--------|----------------------|--------|
| PCPACK    | ✔      | ✔                    | ✖      |
| XEPACK    | ✔      | ✔                    | ✖      |
| PS3PACK   | ✔      | ✖                    | ✖      |

### Dependencies

You will need `python-lzo` from `https://github.com/jd-boyd/python-lzo` to decompress PACK files. 
You can find my fork with prebuilt wheels here (Windows only): https://github.com/kirbystealer/python-lzo/releases/tag/v1.16
If you need wheels for another version/platform, you will have to clone the repo and run the appropriate release tasks yourself.

For example, for Python 3.13, run:
`uv pip install https://github.com/kirbystealer/python-lzo/releases/download/v1.16/python_lzo-1.16-cp313-cp313-win_amd64.whl`


### Using the unpack tool

If you include the `-apk` option, files inside APKs will be extracted to a .APK directory as standalone WRAP files.
These WRAP files contain all the pointer fixups and references from the parent APK file.

```cmd
uv run unpack_wos -h
usage: unpack_wos [-h] [-e] [-f] [-q] [-pfi] [-apk] input [out_dir]

Unpack or list PACK files from a file or a directory.

positional arguments:
  input                 .PACK file or directory of .PACK files
  out_dir               Output directory

optional arguments:
  -h, --help            show this help message and exit
  -e, --extract         Extract contents instead of listing
  -f, --force           Overwrite existing files
  -q, --quiet           Suppress non-error output
  -pfi, --prepend-file-index
                        Prepend file index in names.
  -apk, --with-apk      Also list/extract apk files

```

### Using the wos library
To iterate over files in a PACK:

```Python
import pathlib
import wos.pack

filename = "path/to/GAME.PCPACK"
buffer = pathlib.Path(filename).read_bytes()
archive = wos.pack.PCPACKArchive(buffer)
for f in archive.files:    
    print(f.filename, f.dataSize, f.data[:100])
``` 

### Repacking

Not yet implemented. More work needs to be done on figuring the file structures of APK, PACK and amalga.toc.

### Experimental Repacking

There is now an experimental template-based repacker for `PCPACK` and `XEPACK` archives:

`python repack-wos.py "path/to/original.XEPACK" "path/to/extracted_dir" "path/to/output.XEPACK"`

Or, if installed as a package:

`repack_wos "path/to/original.XEPACK" "path/to/extracted_dir" "path/to/output.XEPACK"`

Current scope and caveats:

- It rebuilds the outer `PCPACK/XEPACK` container from an `unpack_wos -e` directory.
- It preserves the original pack header/table fields where possible and rewrites file offsets, sizes, and NCH-compressed blocks.
- It has been validated locally on `GLOBALTEXT_ENGLISH.XEPACK` for unchanged round-trips and edited top-level payloads.
- It does **not** yet rebuild non-empty inner `PCAPK/XEAPK` archives from extracted `WRAP` files.
- The unknown `NCH` block header fields are currently copied from the template blocks when possible; this is good enough for parser round-trips, but game/runtime validation is still unknown.

### Using the unpack tool

You will need `python-lzo` from `https://github.com/jd-boyd/python-lzo` to decompress PCPACK files. 

Run `pip install --only-binary=:all: python-lzo` to install the precompiled wheel from PyPI.

If you include the `-apk` option, raw pcapk components will be extracted to a .PCAPK directory as well.
Files in a PCAPK can be one component (data) or two components (header + data).

```cmd
uv run .\unpack-wos.py -h
usage: unpack_wos [-h] [-e] [-f] [-q] [-pfi] [-apk] input [out_dir]

Unpack or list PCPACK files from a file or a directory.

positional arguments:
  input                 .PCPACK file or directory of .PCPACK files
  out_dir               Output directory

options:
  -h, --help            show this help message and exit
  -e, --extract         Extract contents instead of listing
  -f, --force           Overwrite existing files
  -q, --quiet           Suppress non-error output
  -pfi, --prepend-file-index
                        Prepend file index in names.
  -apk, --with-pcapk    Also list/extract .pcapk files

```

So to extract all the files in `packs`, including PCAPKs and using file index:

`python unpack-wos.py -apk -pfi -e "path\to\spiderman\image\pc\packs" "path\to\spiderman\extracted"`

### Using the wos library
To iterate over files in a PCPACK:

```Python
import pathlib
import wos.pcpack as pcpack

filename = "path/to/GAME.PCPACK"
buffer = pathlib.Path(filename).read_bytes()
archive = pcpack.PCPACKArchive(buffer)
for f in archive.files:    
    print(f.filename, f.dataSize, f.data[:100])
``` 

### Repacking

Not yet implemented. More work needs to be done on figuring the file structures of PCAPK, PCPACK and amalga.toc.
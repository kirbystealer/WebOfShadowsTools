# ruff: noqa
"""
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
"""

import argparse, os, sys, string
import pathlib

from . import pcpack
from . import pcapk

args = None


def iter_pcpack_entries(pcpack_path: str):
    archive = pcpack.PCPACKArchive(pathlib.Path(pcpack_path).read_bytes())
    return archive.files


def format_entry_filename(entry) -> str:
    with_file_index = args.prepend_file_index

    safe = {
        "hash": entry.filenameHash,
        "fileindex": entry.index + 1,
        "filetypeid": entry.fileTypeId,
        "name": entry.actualFilename,
        "ext": entry.fileExt,
    }

    if entry.actualFilename:
        pattern = "0x{hash:08X}.{name}.{ext}"
    else:
        pattern = "0x{hash:08X}.{ext}"

    if with_file_index:
        pattern = "F{fileindex:03}." + pattern

    fname = pattern.format_map(safe)

    # Disallow directories in output name
    if os.path.basename(fname) != fname:
        raise ValueError(f"Pattern produced a path, not a file name: {fname}")

    return fname


def list_pcpack(file_path: str, quiet: bool, with_pcapk: bool):
    if not quiet:
        print(f"[LIST] {file_path}")
    try:
        for e in iter_pcpack_entries(file_path):
            filename = format_entry_filename(e)
            (
                print(f"{e.index + 1:04}\t\t{e.dataSize: >10}\t\t{filename:<100}")
                if not quiet
                else None
            )

            if with_pcapk and e.fileExt == "pcapk":
                pcapk_file = pcapk.APKFArchive(e.data)

                for f in pcapk_file.files():
                    for i, c in enumerate(f.components):
                        fileType = f.fileType.lower()
                        if len(f.components) > 1:
                            fileType = f"{i}.{fileType}"

                        filename = f"{f.filenameHash}.{f.filename}.{fileType}"
                        print(f"\t*PCAPK*\t\t{len(c):<20}\t\t{filename}")

    except Exception as ex:
        sys.exit(f"Error listing {file_path}: {ex}")


def extract_pcpack(
    file_path: str, out_dir: str, force: bool, quiet: bool, with_pcapk: bool
):
    pcpack_name = pathlib.Path(file_path).stem
    out_dir = os.path.join(out_dir, pcpack_name)

    if not quiet:
        print(f"[EXTRACT] {file_path} -> {out_dir}")
    os.makedirs(out_dir, exist_ok=True)
    try:
        for e in iter_pcpack_entries(file_path):
            out_name = format_entry_filename(e)
            dst = os.path.join(out_dir, out_name)

            skipped = False
            if not force and os.path.exists(dst):
                if not quiet:
                    print(f"[SKIP] exists: {dst}")
                    skipped = True

            if not skipped:
                with open(dst, "wb") as f:
                    f.write(e.data)
                if not quiet:
                    print(f"[WROTE] {dst}")

            if with_pcapk and e.fileExt == "pcapk":
                pcapk_file = pcapk.APKFArchive(e.data)

                for apk_file in pcapk_file.files():
                    out_dir2 = os.path.join(out_dir, "_" + out_name)
                    os.makedirs(out_dir2, exist_ok=True)

                    for i, c in enumerate(apk_file.components):
                        fileType = apk_file.fileType.lower()

                        if len(apk_file.components) > 1:
                            fileType = f"{i}.{fileType}"

                        out_name2 = (
                            f"{apk_file.filenameHash}.{apk_file.filename}.{fileType}"
                        )
                        dst2 = os.path.join(out_dir2, out_name2)

                        if not force and os.path.exists(dst2):
                            if not quiet:
                                print(f"[SKIP] exists: {dst2}")
                            continue
                        with open(dst2, "wb") as f2:
                            f2.write(c)
                        if not quiet:
                            print(f"[WROTE] {dst2}")

    except Exception as ex:
        import traceback

        print(traceback.format_exc())
        sys.exit(f"Error extracting {file_path}: {ex}")


def scan_pcpack_files(input_path: str):
    if os.path.isdir(input_path):
        for name in sorted(os.listdir(input_path)):
            if name.lower().endswith(".pcpack"):
                yield os.path.join(input_path, name)
    elif os.path.isfile(input_path):
        if input_path.lower().endswith(".pcpack"):
            yield input_path
        else:
            sys.exit("Error: input file is not a .pcpack")
    else:
        sys.exit("Error: input path not found")


def main():
    p = argparse.ArgumentParser(
        prog="unpack_wos",
        description="Unpack or list PCPACK files from a file or a directory.",
    )

    p.add_argument("input", help=".PCPACK file or directory of .PCPACK files")

    p.add_argument("out_dir", help="Output directory", nargs="?")
    p.add_argument(
        "-e",
        "--extract",
        action="store_true",
        default=False,
        help="Extract contents instead of listing",
    )

    p.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing files",
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress non-error output",
    )
    p.add_argument(
        "-pfi",
        "--prepend-file-index",
        default=False,
        dest="prepend_file_index",
        action="store_true",
        help="Prepend file index in names.",
    )
    p.add_argument(
        "-apk",
        "--with-pcapk",
        default=True,
        dest="with_pcapk",
        action="store_true",
        help="Also list/extract .pcapk files",
    )

    global args
    args = p.parse_args()

    input_path = os.path.abspath(args.input)

    packs = list(scan_pcpack_files(input_path))
    if not packs:
        sys.exit("No .pcpack files found.")

    do_extract = args.extract
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else None
    if do_extract:
        if not out_dir:
            sys.exit("--extract requires an output directory path")

    for pack in packs:
        if do_extract:
            extract_pcpack(pack, out_dir, args.force, args.quiet, args.with_pcapk)
        else:
            list_pcpack(pack, args.quiet, args.with_pcapk)


if __name__ == "__main__":
    main()

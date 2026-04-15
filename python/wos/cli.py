"""
usage: unpack_wos [-h] [-e] [-f] [-q] [-pfi] [-apk] input [out_dir]

Unpack or list [PC|XE|PS3]PACK files from a file or a directory.

positional arguments:
  input                 .*PACK file or directory of .*PACK files
  out_dir               Output directory

options:
  -h, --help            show this help message and exit
  -e, --extract         Extract contents instead of listing
  -f, --force           Overwrite existing files
  -q, --quiet           Suppress non-error output
  -pfi, --prepend-file-index
                        Prepend file index in names.
  -apk, --with-apk    Also list/extract .apk files
"""

import argparse
import os
import sys
import pathlib

from . import pack
from . import apk
import wos.utils

args = None

def get_pack_archive(pack_path: str):
    path = pathlib.Path(pack_path)
    cls_map = {
        '.PCPACK': pack.PCPACKArchive,
        '.XEPACK': pack.XEPACKArchive,
        '.PS3PACK': pack.PS3PACKArchive
    }
    archive_cls = cls_map.get(path.suffix.upper(), pack.PCPACKArchive)
    archive = archive_cls(path.read_bytes())
    return archive


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


def list_pack(file_path: str, quiet: bool, with_apk: bool):
    if not quiet:
        print(f"[LIST] {file_path}")
    try:
        archive = get_pack_archive(file_path)
        for e in archive.files:
            filename = format_entry_filename(e)
            (
                print(f"{e.index + 1:04}\t\t{e.dataSize: >10}\t\t{filename:<100}")
                if not quiet
                else None
            )

            if with_apk and e.fileTypeId == 25:
                with wos.utils.endianness(archive.endianness):
                    
                    pcapk_file = apk.APKFArchive(e.data, archiveFilename=e.filename)
    
                    for f in pcapk_file.files():
                        for i, c in enumerate(f.components):
                            fileType = f.fileType.lower()
                            if len(f.components) > 1:
                                fileType = f"{i}.{fileType}"
    
                            filename = f"{f.filenameHash}.{f.filename}.{fileType}"
                            print(f"\t*APK*\t\t{len(c):<20}\t\t{filename}")

    except Exception as ex:
        raise
        sys.exit(f"Error listing {file_path}: {ex}")


def extract_pack(
    file_path: str, out_dir: str, force: bool, quiet: bool, with_apk: bool
):
    pack_name = pathlib.Path(file_path).stem
    out_dir = os.path.join(out_dir, pack_name)

    if not quiet:
        print(f"[EXTRACT] {file_path} -> {out_dir}")
    os.makedirs(out_dir, exist_ok=True)
    try:
        archive = get_pack_archive(file_path)
        for e in archive.files:
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

            if with_apk and e.fileTypeId == 25:
                with wos.utils.endianness(archive.endianness):
                    apk_archive = apk.APKFArchive(e.data, archiveFilename=e.filename)
    
                    for apk_file in apk_archive.files():
                        apk_outdir = os.path.join(out_dir, "_" + out_name)
                        os.makedirs(apk_outdir, exist_ok=True)
                        
                        fileType = apk_file.fileType.lower()
                        apk_file_out_name = (
                            f"{apk_file.filenameHash}.{apk_file.filename}.wrap.{fileType}"
                        )
                        apk_file_out_path = pathlib.Path(apk_outdir, apk_file_out_name)
                        if not force and apk_file_out_path.exists():
                            if not quiet:
                                print(f"[SKIP] exists: {apk_file_out_path}")
                            continue
                        else:
                            apk_file_out_path.write_bytes(apk_file.toStandaloneFile())
                            if not quiet:
                                print(f"[WROTE] {apk_file_out_path}")
                                
    except Exception as ex:
        import traceback

        print(traceback.format_exc())
        sys.exit(f"Error extracting {file_path}: {ex}")


def scan_pack_files(input_path: str):
    path = pathlib.Path(input_path)
    valid_suffixes = {".pcpack", ".xepack", ".ps3pack"}

    if path.is_dir():
        for p in sorted(path.iterdir()):
            if p.suffix.lower() in valid_suffixes:
                yield str(p)
    elif path.is_file():
        if path.suffix.lower() in valid_suffixes:
            yield str(path)
        else:
            sys.exit("Error: input file is not a supported pack file (.pcpack, .xepack, .ps3pack)")
    else:
        sys.exit("Error: input path not found")


def main():
    p = argparse.ArgumentParser(
        prog="unpack_wos",
        description="Unpack or list PACK files from a file or a directory.",
    )

    p.add_argument("input", help=".PACK file or directory of .PACK files")

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
        "--with-apk",
        default=False,
        dest="with_apk",
        action="store_true",
        help="Also list/extract apk files",
    )

    global args
    args = p.parse_args()

    input_path = os.path.abspath(args.input)

    packs = list(scan_pack_files(input_path))
    if not packs:
        sys.exit("No .pack files found.")

    do_extract = args.extract
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else None
    if do_extract:
        if not out_dir:
            sys.exit("--extract requires an output directory path")

    for pack in packs:
        if do_extract:
            extract_pack(pack, out_dir, args.force, args.quiet, args.with_apk)
        else:
            list_pack(pack, args.quiet, args.with_apk)


if __name__ == "__main__":
    main()

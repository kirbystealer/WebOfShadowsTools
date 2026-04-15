import argparse
import ctypes
import pathlib
import struct
import sys
from dataclasses import dataclass


DATA_ALIGN = 0x10
BLOCK_ALIGN = 0x1000
NCH_BLOCK_SIZE = 0x80000


def _ensure_lzo_loaded():
    if sys.platform != "darwin":
        import lzo

        return lzo

    candidates = [
        "/opt/homebrew/opt/lzo/lib/liblzo2.2.dylib",
        "/usr/local/opt/lzo/lib/liblzo2.2.dylib",
    ]
    for path in candidates:
        dylib = pathlib.Path(path)
        if dylib.exists():
            ctypes.CDLL(str(dylib), mode=ctypes.RTLD_GLOBAL)
            break

    import lzo

    return lzo


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


@dataclass
class PackBlockTemplate:
    index: int
    physical_offset: int
    physical_size: int
    compressed_size: int
    decompressed_size: int
    decompressed_offset: int
    a2: int
    a4: int
    a5: int
    a6: int


@dataclass
class PackFileTemplate:
    index: int
    header_offset: int
    raw_words: list[int]
    extra_words: list[int]
    filename_hash: int
    file_type_id: int
    data_offset: int
    data_size: int
    reserved_size: int
    data: bytes


@dataclass
class PackTemplate:
    path: pathlib.Path
    endianness: str
    raw_bytes: bytes
    data: bytes
    header_words: tuple[int, ...]
    blocks: list[PackBlockTemplate]
    files: list[PackFileTemplate]
    data_start: int


def _pack_endianness(path: pathlib.Path) -> str:
    if path.suffix.upper() == ".PCPACK":
        return "<"
    if path.suffix.upper() == ".XEPACK":
        return ">"
    raise ValueError(f"Unsupported repack target: {path.suffix}")


def _parse_nch_blocks(raw_bytes: bytes, endianness: str) -> tuple[list[PackBlockTemplate], bytes]:
    lzo = _ensure_lzo_loaded()
    blocks: list[PackBlockTemplate] = []
    out = bytearray()

    offset = 0
    index = 0
    while offset < len(raw_bytes):
        header = raw_bytes[offset : offset + 32]
        if len(header) < 32:
            raise ValueError(f"Truncated NCH block header at 0x{offset:X}")

        magic, compressed_size, a2, decompressed_size, a4, a5, compressed_end, a6 = struct.unpack(
            f"{endianness}4s7I", header
        )
        if magic != b"NCH\x00":
            raise ValueError(f"Missing NCH header at 0x{offset:X}: {magic!r}")

        compressed_start = offset + (compressed_end - compressed_size)
        compressed_stop = offset + compressed_end
        compressed = raw_bytes[compressed_start:compressed_stop]
        if len(compressed) != compressed_size:
            raise ValueError(f"Bad compressed slice for block {index}")

        decompressed = lzo.decompress(
            compressed, False, decompressed_size, algorithm="LZO1X"
        )
        decompressed_offset = len(out)
        out.extend(decompressed)

        next_offset = min(offset + NCH_BLOCK_SIZE, len(raw_bytes))
        if index == 0 and len(raw_bytes) <= NCH_BLOCK_SIZE:
            next_offset = len(raw_bytes)

        physical_size = next_offset - offset
        blocks.append(
            PackBlockTemplate(
                index=index,
                physical_offset=offset,
                physical_size=physical_size,
                compressed_size=compressed_size,
                decompressed_size=decompressed_size,
                decompressed_offset=decompressed_offset,
                a2=a2,
                a4=a4,
                a5=a5,
                a6=a6,
            )
        )

        offset = next_offset
        index += 1

    return blocks, bytes(out)


def parse_pack_template(path: pathlib.Path) -> PackTemplate:
    endianness = _pack_endianness(path)
    raw_bytes = path.read_bytes()
    blocks, data = _parse_nch_blocks(raw_bytes, endianness)

    header_words = struct.unpack_from(f"{endianness}16I", data, 0)
    file_count = header_words[14]

    file_headers_offset = 0x408 + file_count * 4
    offset = file_headers_offset
    files: list[PackFileTemplate] = []
    positive_offsets: list[int] = []

    for index in range(file_count):
        header_offset = offset
        raw_words = list(struct.unpack_from(f"{endianness}11I", data, offset))
        offset += struct.calcsize(f"{endianness}11I")
        extra_words: list[int] = []
        if raw_words[8] != 0:
            extra_words = list(struct.unpack_from(f"{endianness}8I", data, offset))
            offset += struct.calcsize(f"{endianness}8I")

        data_offset = raw_words[2]
        data_size = raw_words[3]
        file_bytes = data[data_offset : data_offset + data_size] if data_size else b""
        if data_size:
            positive_offsets.append(data_offset)

        files.append(
            PackFileTemplate(
                index=index,
                header_offset=header_offset,
                raw_words=raw_words,
                extra_words=extra_words,
                filename_hash=raw_words[0],
                file_type_id=raw_words[1],
                data_offset=data_offset,
                data_size=data_size,
                reserved_size=0,
                data=file_bytes,
            )
        )

    data_start = min(positive_offsets) if positive_offsets else len(data)
    placed_files = sorted((f for f in files if f.data_size), key=lambda f: (f.data_offset, f.index))
    for index, file in enumerate(placed_files):
        next_offset = len(data)
        if index + 1 < len(placed_files):
            next_offset = placed_files[index + 1].data_offset
        file.reserved_size = max(file.data_size, next_offset - file.data_offset)

    return PackTemplate(
        path=path,
        endianness=endianness,
        raw_bytes=raw_bytes,
        data=data,
        header_words=header_words,
        blocks=blocks,
        files=files,
        data_start=data_start,
    )


def _find_replacement_file(input_dir: pathlib.Path, file_index: int) -> pathlib.Path | None:
    prefix = f"F{file_index + 1:03}."
    matches = sorted(
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.name.startswith(prefix) and not p.name.startswith("._")
    )
    return matches[0] if matches else None


def _collect_replacements(
    template: PackTemplate, input_dir: pathlib.Path
) -> dict[int, bytes]:
    replacements: dict[int, bytes] = {}
    for file in template.files:
        candidate = _find_replacement_file(input_dir, file.index)
        replacements[file.index] = candidate.read_bytes() if candidate else file.data
    return replacements


def _write_file_headers(
    template: PackTemplate, out: bytearray, offset_size_map: dict[int, tuple[int, int]]
) -> None:
    for file in template.files:
        new_offset, new_size = offset_size_map[file.index]
        words = list(file.raw_words)
        words[2] = new_offset
        words[3] = new_size
        words[4] = new_size
        struct.pack_into(
            f"{template.endianness}11I", out, file.header_offset, *words
        )
        if file.extra_words:
            struct.pack_into(
                f"{template.endianness}8I",
                out,
                file.header_offset + struct.calcsize(f"{template.endianness}11I"),
                *file.extra_words,
            )


def _build_reflow_pack_data(template: PackTemplate, replacements: dict[int, bytes]) -> bytes:
    # Preserve the static pack header/table bytes up to the first data blob.
    out = bytearray(template.data[: template.data_start])

    placement_order = sorted(
        (f for f in template.files if replacements.get(f.index, f.data)),
        key=lambda f: (f.data_offset or (1 << 30), f.index),
    )

    current = template.data_start
    offset_size_map: dict[int, tuple[int, int]] = {}
    for file in placement_order:
        file_bytes = replacements[file.index]
        if not file_bytes:
            offset_size_map[file.index] = (0, 0)
            continue

        current = align_up(current, DATA_ALIGN)
        if len(out) < current:
            out.extend(b"\x00" * (current - len(out)))

        offset_size_map[file.index] = (current, len(file_bytes))
        out.extend(file_bytes)
        current += len(file_bytes)

    for file in template.files:
        if file.index not in offset_size_map:
            offset_size_map[file.index] = (0, 0)

    target_len = max(len(template.data), align_up(len(out), DATA_ALIGN))
    if len(out) < target_len:
        out.extend(b"\x00" * (target_len - len(out)))

    _write_file_headers(template, out, offset_size_map)

    return bytes(out)


def build_pack_data(template: PackTemplate, replacements: dict[int, bytes]) -> bytes:
    # Best-effort rebuild: keep original data offsets and surrounding padding when
    # replacements still fit inside their original reserved spans.
    out = bytearray(template.data)
    offset_size_map: dict[int, tuple[int, int]] = {}

    for file in template.files:
        file_bytes = replacements.get(file.index, file.data)
        if not file_bytes:
            offset_size_map[file.index] = (0, 0)
            continue

        if file.data_offset and len(file_bytes) <= file.reserved_size:
            end = file.data_offset + len(file_bytes)
            out[file.data_offset:end] = file_bytes
            offset_size_map[file.index] = (file.data_offset, len(file_bytes))
            continue

        return _build_reflow_pack_data(template, replacements)

    _write_file_headers(template, out, offset_size_map)
    return bytes(out)


def _compress_candidate(raw_chunk: bytes) -> bytes:
    lzo = _ensure_lzo_loaded()
    return lzo.compress(raw_chunk, 9, False, algorithm="LZO1X")


def _fit_chunk(data: bytes, requested_size: int) -> tuple[bytes, int]:
    max_payload = NCH_BLOCK_SIZE - 32

    requested_size = min(requested_size, len(data))
    if requested_size <= 0:
        return b"", 0

    raw = data[:requested_size]
    compressed = _compress_candidate(raw)
    if len(compressed) <= max_payload:
        return compressed, requested_size

    lo, hi = 1, requested_size
    best_size = 0
    best_compressed = b""
    while lo <= hi:
        mid = (lo + hi) // 2
        raw = data[:mid]
        compressed = _compress_candidate(raw)
        if len(compressed) <= max_payload:
            best_size = mid
            best_compressed = compressed
            lo = mid + 1
        else:
            hi = mid - 1

    if best_size == 0:
        raise ValueError("Could not fit even a single byte into an NCH block")

    return best_compressed, best_size


def compress_pack_data(template: PackTemplate, decompressed_data: bytes) -> bytes:
    if decompressed_data == template.data:
        return template.raw_bytes

    blocks = bytearray()
    consumed = 0

    planned_sizes = [block.decompressed_size for block in template.blocks]
    planned_index = 0
    while consumed < len(decompressed_data):
        if planned_index < len(planned_sizes):
            template_block = template.blocks[planned_index]
            requested_size = planned_sizes[planned_index]

            if consumed == template_block.decompressed_offset:
                original_chunk = template.data[
                    template_block.decompressed_offset : template_block.decompressed_offset
                    + template_block.decompressed_size
                ]
                candidate_chunk = decompressed_data[
                    consumed : consumed + template_block.decompressed_size
                ]
                if len(candidate_chunk) == template_block.decompressed_size and candidate_chunk == original_chunk:
                    block_start = template_block.physical_offset
                    block_end = block_start + template_block.physical_size
                    blocks.extend(template.raw_bytes[block_start:block_end])
                    consumed += template_block.decompressed_size
                    planned_index += 1
                    continue
        else:
            requested_size = len(decompressed_data) - consumed

        compressed, actual_size = _fit_chunk(
            decompressed_data[consumed:], requested_size
        )
        raw_chunk = decompressed_data[consumed : consumed + actual_size]

        if planned_index < len(template.blocks):
            template_block = template.blocks[planned_index]
            a2 = template_block.a2
            a4 = template_block.a4
            a5 = template_block.a5
            a6 = template_block.a6
        else:
            a2 = 0
            a4 = 0
            a5 = 0
            a6 = 1

        header = struct.pack(
            f"{template.endianness}4s7I",
            b"NCH\x00",
            len(compressed),
            a2,
            len(raw_chunk),
            a4,
            a5,
            32 + len(compressed),
            a6,
        )
        block = bytearray(header)
        block.extend(compressed)

        consumed += actual_size
        more_blocks = consumed < len(decompressed_data)
        if more_blocks:
            if len(block) > NCH_BLOCK_SIZE:
                raise ValueError("NCH block overflowed 0x80000 bytes")
            if len(block) < NCH_BLOCK_SIZE:
                block.extend(b"\xA1" * (NCH_BLOCK_SIZE - len(block)))
        else:
            final_size = align_up(len(block), BLOCK_ALIGN)
            block.extend(b"\xA1" * (final_size - len(block)))

        blocks.extend(block)
        planned_index += 1

    return bytes(blocks)


def repack_pack(template_path: pathlib.Path, input_dir: pathlib.Path, output_path: pathlib.Path) -> None:
    template = parse_pack_template(template_path)
    replacements = _collect_replacements(template, input_dir)
    new_data = build_pack_data(template, replacements)
    repacked = compress_pack_data(template, new_data)
    output_path.write_bytes(repacked)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repack_wos",
        description="Experimental template-based repacker for PCPACK/XEPACK archives.",
    )
    parser.add_argument("template", help="Original .PCPACK or .XEPACK to use as the template")
    parser.add_argument("input_dir", help="Directory produced by unpack_wos -e")
    parser.add_argument("output", help="Output pack path")
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Overwrite the output file if it already exists",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    template_path = pathlib.Path(args.template).resolve()
    input_dir = pathlib.Path(args.input_dir).resolve()
    output_path = pathlib.Path(args.output).resolve()

    if not template_path.is_file():
        parser.error(f"template path not found: {template_path}")
    if not input_dir.is_dir():
        parser.error(f"input directory not found: {input_dir}")
    if output_path.exists() and not args.force:
        parser.error(f"output exists: {output_path} (use --force)")

    repack_pack(template_path, input_dir, output_path)
    print(f"[WROTE] {output_path}")


if __name__ == "__main__":
    main()

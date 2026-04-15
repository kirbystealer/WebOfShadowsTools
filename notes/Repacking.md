## Repacking Status

The repo can now do an experimental outer-pack rebuild for `PCPACK` and `XEPACK` archives via [`python/wos/repack.py`](../python/wos/repack.py).

What works now:

- Use an original pack as a template.
- Rebuild the decompressed pack image with edited extracted files.
- Rewrite per-file offsets and sizes in the file header table.
- Recompress back into `NCH` blocks with raw LZO (`header=False`).
- Round-trip `GLOBALTEXT_ENGLISH.XEPACK` through `unpack -> repack -> unpack`.
- Preserve edited top-level payload bytes across the round-trip.

What has been verified:

- The repo unpacker can read the repacked archive.
- Top-level extracted payload hashes match for an unchanged round-trip.
- Edited top-level files survive the repack.

What is still missing:

- Rebuilding non-empty `PCAPK/XEAPK` archives from extracted `WRAP` files.
- Repacking `PS3PACK`.
- Verifying which unknown `NCH` block header fields are actually checked by the game.
- Verifying whether the game requires byte-for-byte block layout quirks that the parser does not.

## Current Outer-Pack Strategy

The new repacker is deliberately template-preserving:

1. Decompress the original pack into its raw table/data image.
2. Keep the original static header area and unknown fields.
3. Replace only file payload bytes, offsets, and sizes.
4. Keep file order aligned to the original data-offset order.
5. Recompress into `NCH` blocks.

This is the least risky approach because the existing parser already proves those header/table bytes are good enough to read the archive.

## `NCH` Block Notes

Known fields from the current parser:

- `magic`: `NCH\\0`
- `compressedDataSize`
- `decompressedDataSize`
- `compressedDataEnd`

Observed behavior:

- The compressed payload is raw LZO, not the headered variant.
- The payload begins immediately after the 32-byte `NCH` header.
- Non-final blocks are padded out to `0x80000` bytes with `0xA1`.
- Final blocks can be shorter; the current repacker pads them to a `0x1000` boundary.

Unknown fields still not identified:

- `a2`
- `a4`
- `a5`
- `a6`

Current policy:

- For rebuilt blocks that correspond to original blocks, copy those unknown fields from the template.
- For newly created overflow blocks, emit dummy values.

This is enough for tool round-trips, but not yet proven for in-game loading.

## `WRAP -> XEAPK` Plan

The practical path is also template-preserving.

### 1. Require an original non-empty `XEAPK` template

Use the original raw `XEAPK` as the source of truth for:

- archive header fields
- component-header metadata
- file-type header order
- active-component counts
- per-component alignments
- filename table contents and offsets
- original patch semantics

### 2. Parse extracted `WRAP` files

Each extracted `WRAP` already contains:

- component count
- component byte blobs
- internal patch target list
- external patch metadata
- global patch metadata

The repo already writes these in [`python/wos/apk.py`](../python/wos/apk.py).

### 3. Normalize each `WRAP` against the template file

For each file being rebuilt:

- Match by filename hash and file type.
- Use the template file's patch list as the semantic reference.
- Recover internal patch destinations from the relative pointers stored in component 0.
- Recompute external patch target values using the rebuilt component layout.
- Preserve filename/global patch metadata from the template unless the mod explicitly changes it.

### 4. Rebuild the raw `XEAPK`

Serialize in the original archive order:

- header
- file-type table
- file headers
- filename table
- component headers
- component data streams
- encoded patch table
- global patch table

The existing parser already gives the decode rules for these structures in:

- [`python/wos/apk.py`](../python/wos/apk.py)
- [`imhex/APKF.hexpat`](../imhex/APKF.hexpat)

### 5. Drop the rebuilt `XEAPK` back into the outer pack

Once the raw `XEAPK` bytes exist, the outer repacker can already place them back into the template `XEPACK`.

## Likely Important Unknowns

Based on the current reverse path, the game probably only cares about a small number of fields:

- `NCH` block header validation fields, if any
- exact `XEAPK` patch encoding
- filename table offsets
- component-data alignment
- maybe final block padding/alignment rules

Everything else should be treated as template data first and only recomputed if the parser proves it must be.

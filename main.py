#!/usr/bin/env python3
"""ai-happy-01 entry: deliver art.png as /output/entry.png.

The artwork shows a golden retriever puppy in a daisy crown leaping
to pop a giant soap bubble with its nose, in a flower meadow at
golden hour. It is stored beside this file as art.png. This program
checks the image against the competition gate -- PNG or JPEG, at
most 1 MiB, at most 1024 x 1024 pixels, complete file -- and then
copies it byte-for-byte to the output location. Standard library
only, deterministic, no network, runs in well under a second.
"""

import hashlib
import os
import struct
import sys
from pathlib import Path

MAX_BYTES = 1_048_576  # 1 MiB gate limit
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"


def png_dimensions(data):
    """Return (width, height) read from the PNG IHDR chunk."""
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG file")
    if data[12:16] != b"IHDR":
        raise ValueError("PNG is missing its IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    if b"IEND" not in data[-64:]:
        raise ValueError("PNG is truncated: no IEND chunk near the end")
    return width, height


def jpeg_dimensions(data):
    """Return (width, height) by scanning JPEG segments for a SOF."""
    if not data.startswith(JPEG_SIGNATURE):
        raise ValueError("not a JPEG file")
    if not data.rstrip().endswith(b"\xff\xd9"):
        raise ValueError("JPEG is truncated: no EOI marker at the end")
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise ValueError("corrupt JPEG segment marker")
        marker = data[pos + 1]
        length = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack(">HH", data[pos + 5 : pos + 9])
            return width, height
        if length < 2:
            raise ValueError("corrupt JPEG segment length")
        pos += 2 + length
    raise ValueError("JPEG has no SOF marker: dimensions unknown")


def validate_image(data):
    """Check the gate rules and return (kind, width, height)."""
    if len(data) == 0:
        raise ValueError("image file is empty")
    if len(data) > MAX_BYTES:
        raise ValueError(f"image is {len(data)} bytes, over the 1 MiB limit")
    if data.startswith(PNG_SIGNATURE):
        kind = "PNG"
        width, height = png_dimensions(data)
    elif data.startswith(JPEG_SIGNATURE):
        kind = "JPEG"
        width, height = jpeg_dimensions(data)
    else:
        raise ValueError("image is neither PNG nor JPEG (bad magic bytes)")
    if width == 0 or height == 0:
        raise ValueError("image has a zero dimension")
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        raise ValueError(
            f"image is {width}x{height}, over the {MAX_WIDTH}x{MAX_HEIGHT} limit"
        )
    return kind, width, height


def main():
    here = Path(__file__).resolve().parent
    source = here / "art.png"
    if not source.is_file():
        raise ValueError("art.png is missing beside main.py")
    data = source.read_bytes()
    kind, width, height = validate_image(data)
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    tmp = out_dir / "entry.png.tmp"
    tmp.write_bytes(data)
    os.replace(tmp, target)
    written = target.read_bytes()
    if written != data:
        raise ValueError("output does not match art.png byte-for-byte")
    print(f"wrote {target} ({kind} {width}x{height}, {len(data)} bytes)")
    print(f"sha256 {hashlib.sha256(written).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

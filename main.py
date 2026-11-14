#!/usr/bin/env python3
"""Entry program for make.fun competition ai-happy-01 (v2 rebuild).

The picture: a golden retriever puppy wearing a crown of daisies,
caught mid-leap in a flower meadow at golden hour as its nose pops
a giant soap bubble. Pastel balloons drift on the left and a double
rainbow arcs over the hills on the right. The artwork lives next to
this file as art.png.

What this program does is deliberately small: it reads art.png,
checks it against the competition limits (PNG or JPEG, no more
than 1 MiB, no more than 1024 x 1024 pixels, and a complete file),
then writes the exact same bytes to the entry output. It uses only
the Python standard library, touches no network, and always
produces the same output for the same art.png.
"""

import hashlib
import os
import struct
import sys
from pathlib import Path

BYTE_LIMIT = 1048576
WIDTH_LIMIT = 1024
HEIGHT_LIMIT = 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


def size_of_png(blob):
    """Width and height of a PNG, from its IHDR chunk."""
    if len(blob) < 24:
        raise ValueError("PNG data is too short for a header")
    if blob[12:16] != b"IHDR":
        raise ValueError("PNG header chunk is not IHDR")
    if b"IEND" not in blob[-64:]:
        raise ValueError("PNG data ends before an IEND chunk")
    return struct.unpack(">II", blob[16:24])


def size_of_jpeg(blob):
    """Width and height of a JPEG, from its first SOF segment."""
    if not blob.rstrip().endswith(b"\xff\xd9"):
        raise ValueError("JPEG data has no end-of-image marker")
    cursor = 2
    while cursor + 4 <= len(blob):
        if blob[cursor] != 0xFF:
            raise ValueError("JPEG segment does not start with 0xFF")
        marker = blob[cursor + 1]
        seg_len = struct.unpack(">H", blob[cursor + 2 : cursor + 4])[0]
        if seg_len < 2:
            raise ValueError("JPEG segment length is invalid")
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack(
                ">HH", blob[cursor + 5 : cursor + 9]
            )
            return width, height
        cursor += 2 + seg_len
    raise ValueError("JPEG data has no start-of-frame segment")


def check_picture(blob):
    """Enforce the gate limits; return (format, width, height)."""
    if not blob:
        raise ValueError("art.png is empty")
    if len(blob) > BYTE_LIMIT:
        raise ValueError("art.png is larger than 1 MiB")
    if blob.startswith(PNG_MAGIC):
        fmt = "PNG"
        width, height = size_of_png(blob)
    elif blob.startswith(JPEG_MAGIC):
        fmt = "JPEG"
        width, height = size_of_jpeg(blob)
    else:
        raise ValueError("art.png is neither a PNG nor a JPEG")
    if width < 1 or height < 1:
        raise ValueError("art.png has a zero width or height")
    if width > WIDTH_LIMIT or height > HEIGHT_LIMIT:
        raise ValueError("art.png is larger than 1024 x 1024")
    return fmt, width, height


def deliver(blob):
    """Write blob to the output entry file, atomically.

    The bytes land on a staging file first and are then renamed over
    the target, so a reader never sees a half-written entry.png.
    """
    folder = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "entry.png"
    staging = folder / "entry.png.part"
    staging.write_bytes(blob)
    os.replace(staging, target)
    return target


def run():
    folder = Path(__file__).resolve().parent
    art_file = folder / "art.png"
    if not art_file.is_file():
        raise ValueError("art.png was not found beside main.py")
    blob = art_file.read_bytes()
    fmt, width, height = check_picture(blob)
    target = deliver(blob)
    echoed = target.read_bytes()
    if echoed != blob:
        raise ValueError("entry.png differs from art.png")
    digest = hashlib.sha256(echoed).hexdigest()
    print(f"entry written: {target}")
    print(f"format {fmt}, size {width}x{height}, bytes {len(blob)}")
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(run())

#!/usr/bin/env python3
"""Convert the lighthouse source PNG to an Inky:bit RLE renderer."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


WIDTH = 250
HEIGHT = 122
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

DEFAULT_INPUT = Path(
    "/Users/nakauchishouichi/Library/Mobile Documents/com~apple~CloudDocs/"
    "那須野崎プログラミング倶楽部/Logo/"
    "494267D0-2390-4BDB-903F-D782C6A5ABAC-E.png"
)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(data, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_dist = abs(estimate - left)
    above_dist = abs(estimate - above)
    upper_left_dist = abs(estimate - upper_left)
    if left_dist <= above_dist and left_dist <= upper_left_dist:
        return left
    if above_dist <= upper_left_dist:
        return above
    return upper_left


def unfilter_scanlines(data: bytes, width: int, height: int, channels: int) -> bytearray:
    stride = width * channels
    output = bytearray(height * stride)
    source = 0

    for y in range(height):
        filter_type = data[source]
        source += 1
        row = bytearray(data[source:source + stride])
        source += stride
        previous_start = (y - 1) * stride

        for x in range(stride):
            left = row[x - channels] if x >= channels else 0
            above = output[previous_start + x] if y > 0 else 0
            upper_left = output[previous_start + x - channels] if y > 0 and x >= channels else 0

            if filter_type == 1:
                row[x] = (row[x] + left) & 0xFF
            elif filter_type == 2:
                row[x] = (row[x] + above) & 0xFF
            elif filter_type == 3:
                row[x] = (row[x] + ((left + above) // 2)) & 0xFF
            elif filter_type == 4:
                row[x] = (row[x] + paeth(left, above, upper_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter: {filter_type}")

        output[y * stride:(y + 1) * stride] = row

    return output


def read_rgba_png(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG file")

    offset = 8
    width = height = bit_depth = color_type = None
    compressed = bytearray()

    while offset < len(data):
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        chunk = data[offset + 8:offset + 8 + size]
        offset += 12 + size

        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("unsupported PNG compression/filter/interlace")
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break

    if width is None or height is None or bit_depth != 8:
        raise ValueError("only 8-bit PNG input is supported")

    if color_type == 6:
        channels = 4
    elif color_type == 2:
        channels = 3
    else:
        raise ValueError(f"unsupported PNG colour type: {color_type}")

    raw = unfilter_scanlines(zlib.decompress(bytes(compressed)), width, height, channels)
    pixels: list[tuple[int, int, int, int]] = []
    for index in range(0, len(raw), channels):
        if channels == 4:
            pixels.append((raw[index], raw[index + 1], raw[index + 2], raw[index + 3]))
        else:
            pixels.append((raw[index], raw[index + 1], raw[index + 2], 255))
    return width, height, pixels


def alpha_bbox(width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            if pixels[y * width + x][3] >= 32:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise ValueError("source image is fully transparent")
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def make_lighthouse_pixels(
    source_width: int,
    source_height: int,
    source_pixels: list[tuple[int, int, int, int]],
    size: int,
    threshold: int,
) -> list[int]:
    left, top, right, bottom = alpha_bbox(source_width, source_height, source_pixels)
    crop_width = right - left
    crop_height = bottom - top
    scale = min(size / crop_width, size / crop_height)
    output_width = max(1, round(crop_width * scale))
    output_height = max(1, round(crop_height * scale))
    offset_x = (WIDTH - output_width) // 2
    offset_y = (HEIGHT - output_height) // 2

    canvas = [0] * (WIDTH * HEIGHT)
    for y in range(output_height):
        source_y = top + min(crop_height - 1, int(y / scale))
        for x in range(output_width):
            source_x = left + min(crop_width - 1, int(x / scale))
            r, g, b, a = source_pixels[source_y * source_width + source_x]
            gray = (r * 299 + g * 587 + b * 114) // 1000
            if a >= 32 and gray < threshold:
                canvas[(offset_y + y) * WIDTH + offset_x + x] = 1
    return canvas


def rgb_for_code(code: int) -> tuple[int, int, int]:
    if code == 0:
        return WHITE
    if code == 1:
        return BLACK
    if code == 2:
        return RED
    raise ValueError(f"unknown palette code: {code}")


def write_png(path: Path, pixels: list[int]) -> None:
    raw = bytearray()
    for y in range(HEIGHT):
        raw.append(0)
        start = y * WIDTH
        for code in pixels[start:start + WIDTH]:
            raw.extend(rgb_for_code(code))

    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", ihdr)
    data += png_chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
    data += png_chunk(b"IEND", b"")
    path.write_bytes(data)


def rle_encode(pixels: list[int]) -> list[int]:
    encoded: list[int] = []
    current = pixels[0]
    count = 0

    for value in pixels:
        if value == current and count < 255:
            count += 1
            continue
        encoded.extend((count, current))
        current = value
        count = 1

    encoded.extend((count, current))
    return encoded


def format_values(values: list[int], values_per_line: int = 24) -> str:
    lines = []
    for index in range(0, len(values), values_per_line):
        chunk = ", ".join(str(value) for value in values[index:index + values_per_line])
        lines.append("    " + chunk + ",")
    return "\n".join(lines)


def makecode_ts(encoded: list[int], source_png: Path) -> str:
    return f"""// Generated by make_lighthouse_png_rle.py from {source_png.name}.
// Palette: 0=white, 1=black, 2=red/accent.

const WIDTH = {WIDTH}
const HEIGHT = {HEIGHT}

const IMAGE_RLE = [
{format_values(encoded)}
]

function drawRleImage() {{
    let position = 0
    let index = 0

    while (index < IMAGE_RLE.length) {{
        const count = IMAGE_RLE[index]
        const colour = IMAGE_RLE[index + 1]

        if (colour != 0) {{
            let ink = inkybit.Color.Black
            if (colour == 2) {{
                ink = inkybit.Color.Accent
            }}

            for (let offset = 0; offset < count; offset++) {{
                const pixel = position + offset
                inkybit.setPixel(pixel % WIDTH, Math.idiv(pixel, WIDTH), ink)
            }}
        }}

        position += count
        index += 2
    }}
}}

inkybit.clear()
drawRleImage()
inkybit.show()
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--png", type=Path, default=Path("lighthouse_only.png"))
    parser.add_argument("--ts", type=Path, default=Path("makecode_project/main.ts"))
    parser.add_argument("--size", type=int, default=108)
    parser.add_argument("--threshold", type=int, default=170)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    width, height, pixels = read_rgba_png(args.input)
    output_pixels = make_lighthouse_pixels(width, height, pixels, args.size, args.threshold)
    encoded = rle_encode(output_pixels)

    write_png(args.png, output_pixels)
    args.ts.write_text(makecode_ts(encoded, args.png), encoding="utf-8")

    raw_pixels = WIDTH * HEIGHT
    print(f"source: {args.input}")
    print(f"PNG: {args.png}")
    print(f"MakeCode TS: {args.ts}")
    print(f"black pixels: {sum(1 for pixel in output_pixels if pixel == 1)}")
    print(f"RLE pairs: {len(encoded) // 2}")
    print(f"RLE values: {len(encoded)} ({len(encoded) / raw_pixels:.1%} of raw pixels)")


if __name__ == "__main__":
    main()

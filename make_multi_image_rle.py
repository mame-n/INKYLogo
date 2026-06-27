#!/usr/bin/env python3
"""Build a home image plus three button images for Inky:bit MakeCode."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

from make_png_rle import HEIGHT, WIDTH, format_hex, palette_codes, read_png_pixels, rle_encode


PROJECT_ROOT = Path(__file__).resolve().parent
HOME_IMAGE = PROJECT_ROOT / "lighthouse_kanji_prokura.png"
MAKECODE_PROJECT = PROJECT_ROOT / "makecode_project"
PXT_LAUNCHER = MAKECODE_PROJECT / "pxt_cli.js"
PXT_MODULES = MAKECODE_PROJECT / "pxt_modules"
BUILT_HEX = MAKECODE_PROJECT / "built" / "binary.hex"
OUTPUT_HEX = PROJECT_ROOT / "dist" / "inky_images_microbit_v2.hex"


def select_pngs_macos() -> list[Path]:
    """Use the native macOS picker without depending on Python's Tk build."""
    selected: list[Path] = []
    for button_name in ("A", "B", "A+B"):
        script = (
            f'set selectedFile to choose file with prompt "{button_name}ボタンで表示するPNGを選択" '
            'of type {"public.png"}\n'
            "POSIX path of selectedFile"
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            if "(-128)" in result.stderr:
                break
            message = result.stderr.strip() or "unknown osascript error"
            raise RuntimeError(f"could not open the macOS file picker: {message}")
        selected.append(Path(result.stdout.strip()))
    return selected


def select_pngs_tk() -> list[Path]:
    """Fallback picker for non-macOS platforms."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as error:
        raise RuntimeError("GUI file selection requires Python tkinter") from error

    root = tk.Tk()
    root.withdraw()
    root.update()
    selected: list[Path] = []
    for button_name in ("A", "B", "A+B"):
        item = filedialog.askopenfilename(
            parent=root,
            title=f"{button_name}ボタンで表示するPNGを選択",
            filetypes=(("PNG images", "*.png"),),
        )
        if not item:
            break
        selected.append(Path(item))
    root.destroy()
    return selected


def select_pngs() -> list[Path]:
    """Select the A, B, and A+B images in an unambiguous order."""
    if sys.platform == "darwin":
        return select_pngs_macos()
    return select_pngs_tk()


def fitted_palette_codes(
    width: int,
    height: int,
    channels: int,
    raw: bytearray,
    threshold: int,
) -> list[int]:
    """Fit an image on the display with white letterboxing and area sampling."""
    scale = min(WIDTH / width, HEIGHT / height)
    fitted_width = max(1, min(WIDTH, round(width * scale)))
    fitted_height = max(1, min(HEIGHT, round(height * scale)))
    left = (WIDTH - fitted_width) // 2
    top = (HEIGHT - fitted_height) // 2
    output = [0] * (WIDTH * HEIGHT)
    source_stride = width * channels

    for target_y in range(fitted_height):
        source_top = math.floor(target_y * height / fitted_height)
        source_bottom = max(source_top + 1, math.ceil((target_y + 1) * height / fitted_height))
        for target_x in range(fitted_width):
            source_left = math.floor(target_x * width / fitted_width)
            source_right = max(source_left + 1, math.ceil((target_x + 1) * width / fitted_width))
            red = green = blue = samples = 0

            for source_y in range(source_top, min(source_bottom, height)):
                row = source_y * source_stride
                for source_x in range(source_left, min(source_right, width)):
                    index = row + source_x * channels
                    alpha = raw[index + 3] if channels == 4 else 255
                    red += (raw[index] * alpha + 255 * (255 - alpha)) // 255
                    green += (raw[index + 1] * alpha + 255 * (255 - alpha)) // 255
                    blue += (raw[index + 2] * alpha + 255 * (255 - alpha)) // 255
                    samples += 1

            gray = ((red // samples) * 299 + (green // samples) * 587 + (blue // samples) * 114) // 1000
            if gray < threshold:
                output[(top + target_y) * WIDTH + left + target_x] = 1

    return output


def encode_png(path: Path, threshold: int, strict_size: bool = False) -> tuple[str, int, int, int, int]:
    width, height, channels, raw = read_png_pixels(path)
    if strict_size and (width != WIDTH or height != HEIGHT):
        raise ValueError(f"{path}: input must be {WIDTH}x{HEIGHT}; got {width}x{height}")

    if width == WIDTH and height == HEIGHT:
        pixels = palette_codes(width, height, channels, raw, threshold)
    else:
        pixels = fitted_palette_codes(width, height, channels, raw, threshold)
    encoded = rle_encode(pixels)
    return format_hex(encoded), sum(pixel == 1 for pixel in pixels), len(encoded) // 2, width, height


def run_pxt(command: str) -> None:
    if shutil.which("node") is None:
        raise RuntimeError("Node.js is required to compile the MakeCode project")
    if not PXT_LAUNCHER.exists():
        raise RuntimeError(f"MakeCode launcher not found: {PXT_LAUNCHER}")

    try:
        subprocess.run(["node", str(PXT_LAUNCHER), command], check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"MakeCode {command} failed (exit code {error.returncode})") from error


def build_hex(output: Path) -> Path:
    if not (PXT_MODULES / "inkybit" / "pxt.json").exists():
        print("Installing the Inky:bit MakeCode extension (first run only)...", flush=True)
        run_pxt("install")

    print("Compiling the micro:bit V2 HEX...", flush=True)
    run_pxt("build")
    if not BUILT_HEX.exists():
        raise RuntimeError(f"MakeCode did not create the expected HEX: {BUILT_HEX}")

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BUILT_HEX, output)
    return output


def reveal_hex_in_finder(hex_path: Path) -> None:
    if sys.platform != "darwin":
        print(f"HEX: {hex_path}")
        return

    subprocess.run(["open", "-R", str(hex_path)], check=False)
    microbit_drive = Path("/Volumes/MICROBIT")
    if microbit_drive.exists():
        subprocess.run(["open", str(microbit_drive)], check=False)
        print("Finder opened the HEX file and the MICROBIT drive.")
    else:
        print("Finder opened the HEX file. Connect the micro:bit to open its MICROBIT drive.")


def makecode_ts(home_image: str, images: list[str], sources: list[Path]) -> str:
    source_names = ", ".join(path.name for path in sources)
    image_constants = "\n".join(
        f'const IMAGE_{index + 1}_RLE_HEX = "{image}"' for index, image in enumerate(images)
    )
    return f"""// Generated by make_multi_image_rle.py.
// Home={HOME_IMAGE.name}; A/B/A+B images={source_names}.
// Reset or logo touch=home, A=image 1, B=image 2, A+B=image 3.
// Palette: 0=white, 1=black, 2=red/accent.

const WIDTH = {WIDTH}
const HEIGHT = {HEIGHT}

const HOME_IMAGE_RLE_HEX = "{home_image}"
{image_constants}

let busy = false
let currentImage = -1

function hexNibble(text: string, index: number): number {{
    const code = text.charCodeAt(index)
    if (code >= 48 && code <= 57) {{
        return code - 48
    }}
    return code - 87
}}

function hexByte(text: string, index: number): number {{
    return hexNibble(text, index) * 16 + hexNibble(text, index + 1)
}}

function imageData(imageNumber: number): string {{
    if (imageNumber == 0) {{
        return HOME_IMAGE_RLE_HEX
    }}
    if (imageNumber == 1) {{
        return IMAGE_1_RLE_HEX
    }}
    if (imageNumber == 2) {{
        return IMAGE_2_RLE_HEX
    }}
    return IMAGE_3_RLE_HEX
}}

function showImage(imageNumber: number) {{
    if (busy || currentImage == imageNumber) {{
        return
    }}

    busy = true
    const data = imageData(imageNumber)
    let position = 0
    let index = 0

    inkybit.clear()
    while (index < data.length) {{
        const count = hexByte(data, index)
        const colour = hexByte(data, index + 2)

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
        index += 4
    }}

    inkybit.show()
    currentImage = imageNumber
    busy = false
}}

input.onButtonPressed(Button.A, function () {{
    showImage(1)
}})

input.onButtonPressed(Button.B, function () {{
    showImage(2)
}})

input.onButtonPressed(Button.AB, function () {{
    showImage(3)
}})

input.onLogoEvent(TouchButtonEvent.Pressed, function () {{
    showImage(0)
}})

showImage(0)
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add three selectable button images to the fixed Inky:bit home image."
    )
    parser.add_argument("inputs", nargs="*", type=Path, help="three PNGs in image 1/2/3 order")
    parser.add_argument("--choose", action="store_true", help="select the three PNGs in a file picker")
    parser.add_argument("--ts", type=Path, default=MAKECODE_PROJECT / "main.ts")
    parser.add_argument("--output", type=Path, default=OUTPUT_HEX, help="final HEX output path")
    parser.add_argument("--no-build", action="store_true", help="only generate main.ts")
    parser.add_argument("--no-finder", action="store_true", help="do not reveal the HEX in Finder")
    parser.add_argument("--threshold", type=int, default=210)
    parser.add_argument(
        "--strict-size",
        action="store_true",
        help=f"reject images that are not exactly {WIDTH}x{HEIGHT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 <= args.threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")
    if args.choose and args.inputs:
        raise ValueError("use either --choose or three input paths, not both")

    sources = select_pngs() if args.choose else args.inputs
    if len(sources) != 3:
        raise ValueError(f"exactly three PNGs are required; got {len(sources)}")

    results = [encode_png(source, args.threshold, args.strict_size) for source in sources]
    home_result = encode_png(HOME_IMAGE, args.threshold, True)
    args.ts.parent.mkdir(parents=True, exist_ok=True)
    args.ts.write_text(
        makecode_ts(home_result[0], [result[0] for result in results], sources),
        encoding="utf-8",
    )

    print(f"MakeCode TS: {args.ts}")
    print(f"home (reset/logo): {HOME_IMAGE}")
    for index, (source, (_, black_pixels, pairs, width, height)) in enumerate(zip(sources, results), start=1):
        resize_note = "" if (width, height) == (WIDTH, HEIGHT) else f", fitted from {width}x{height}"
        print(
            f"image {index}: {source} "
            f"(black pixels: {black_pixels}, RLE pairs: {pairs}{resize_note})"
        )

    if not args.no_build:
        if args.ts.resolve() != (MAKECODE_PROJECT / "main.ts").resolve():
            raise ValueError("--ts can only be changed when --no-build is used")
        final_hex = build_hex(args.output)
        print(f"HEX: {final_hex}")
        if not args.no_finder:
            reveal_hex_in_finder(final_hex)


if __name__ == "__main__":
    main()

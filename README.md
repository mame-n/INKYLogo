# micro:bit + Inky:bit display test

## Recommended

Copy `nasunozaki_inky_lighthouse_kanji_prokura_microbit_v2.hex` to the
`MICROBIT` drive to display the lighthouse, `那須野崎`, and `プロクラ`.

The PNG is converted to packed RLE text in `makecode_project/main.ts`. The
micro:bit expands that RLE data and writes the pixels to the Inky:bit display.

`nasunozaki_inky_text_microbit_v2.hex` is also available as a text diagnostic.
`nasunozaki_inky_red_microbit_v2.hex` is a full-screen accent colour test.

This build is for micro:bit V2. The Pimoroni Inky:bit MakeCode extension used
here (`github:pimoroni/pxt-inkybit#v0.0.5`) disables the micro:bit V1 target, so
the V1/universal HEX files should not be used for this program.

The current program contains a fixed home image and three selectable images.
It shows the lighthouse + `那須野崎` + `プロクラ` image at startup and
switches images with the micro:bit controls:

- A: image 1
- B: image 2
- A+B: image 3
- Logo touch: home image

An e-ink refresh can take several seconds. Button input is ignored while a
refresh is running.

## Build a three-image version

Each source image must be an 8-bit RGB or RGBA PNG. Images of any size are
fitted inside the Inky:bit's 250x122 display without distortion; unused space
is filled white. On macOS, `--choose` uses the native file picker and asks for
the A, B, and A+B images in that order:

```sh
python3 make_multi_image_rle.py --choose
```

After the third image is selected, the script compiles a micro:bit V2 Universal
HEX at `dist/inky_images_microbit_v2.hex`. Finder then reveals the HEX and, if
the micro:bit is connected, opens the `MICROBIT` drive for drag-and-drop. The
first build needs internet access for the Inky:bit extension and MakeCode
native runtime; later builds use the local cache.

or provide the three files in button order:

```sh
python3 make_multi_image_rle.py image-a.png image-b.png image-ab.png
```

This writes `makecode_project/main.ts` and compiles the HEX automatically. Use
`--no-build` when only source generation is wanted. The fixed home image and
three selected PNGs are embedded in the firmware, so a PC is not required
after installation.

## MakeCode TypeScript

To edit the program in MakeCode:

1. Create a new project at https://makecode.microbit.org/.
2. Add the extension `github:pimoroni/pxt-inkybit#v0.0.5`.
3. Switch to JavaScript.
4. Replace the program with `makecode_project/main.ts`.

`makecode_project/main.ts` is the generated RLE image renderer in a PXT project.

## Files

- `nasunozaki_inky_text_microbit_v2.hex`: diagnostic text display for micro:bit V2
- `nasunozaki_inky_red_microbit_v2.hex`: full-screen accent colour test for micro:bit V2
- `nasunozaki_inky_black_circle_microbit_v2.hex`: 50-pixel black circle test for micro:bit V2
- `nasunozaki_inky_png_circle_microbit_v2.hex`: RLE-decoded PNG circle display for micro:bit V2
- `nasunozaki_inky_lighthouse_png_microbit_v2.hex`: RLE-decoded lighthouse PNG display for micro:bit V2
- `nasunozaki_inky_lighthouse_kanji_microbit_v2.hex`: RLE-decoded lighthouse + `那須野崎` display for micro:bit V2
- `nasunozaki_inky_lighthouse_kanji_packed_microbit_v2.hex`: lower-RAM packed RLE lighthouse + `那須野崎` display for micro:bit V2
- `nasunozaki_inky_lighthouse_kanji_prokura_microbit_v2.hex`: packed RLE lighthouse + `那須野崎` + `プロクラ` display for micro:bit V2
- `black_circle_50.png`: 250x122 PNG source image with a 50-pixel black circle
- `make_circle_png_rle.py`: PNG/RLE/MakeCode TypeScript generator
- `lighthouse_only.png`: 250x122 PNG source image with the lighthouse only
- `make_lighthouse_png_rle.py`: lighthouse PNG/RLE/MakeCode TypeScript generator
- `lighthouse_kanji.png`: 250x122 PNG source image with the lighthouse and `那須野崎`
- `lighthouse_kanji_prokura.png`: 250x122 PNG source image with the lighthouse, `那須野崎`, and `プロクラ`
- `render_lighthouse_kanji.swift`: macOS renderer that creates the Kanji PNG
- `make_png_rle.py`: generic 250x122 PNG-to-RLE MakeCode TypeScript generator
- `make_multi_image_rle.py`: fixed home image plus three-PNG A/B/A+B generator
- `nasunozaki_inky_logo_universal.hex`: generated universal HEX; do not use
- `nasunozaki_inky_logo_microbit_v1.hex`: generated placeholder; do not use
- `nasunozaki_inky_logo_microbit_v2.hex`: logo display for micro:bit V2
- `makecode_inky_logo.py`: generated MakeCode Python
- `convert_logo.py`: PNG-to-RLE conversion script
- `inky_logo_preview.png`: 250x122 three-colour preview

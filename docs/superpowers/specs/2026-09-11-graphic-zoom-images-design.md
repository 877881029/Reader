# Graphic Zoom and Raster Image Preview

Date: 2026-09-11  
Status: Implemented (hidden Ctrl+wheel zoom; PNG/JPEG/GIF/WebP/BMP tabs)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

SVG and raster image tabs stay **paper graphic viewers** with **no on-screen zoom chrome**. Zoom in/out is only **Ctrl + mouse wheel**. Reader also opens common image files as first-class tabs.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Zoom UI | None: no buttons, slider, percent label, or “适合窗口” control on graphic tabs |
| Zoom input | **Ctrl + wheel only**. Plain wheel does not zoom |
| Zoom range | Multiplier on fit-to-pane: `0.25`–`16`, step `1.15` per 120° wheel notch, toward cursor |
| Pan | Left-drag when zoomed (no scrollbars). Not a visible toolbar |
| SVG | Keep `kind="svg"` / `SvgView`; inherit shared canvas zoom |
| Raster | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` → `kind="image"` |
| Invalid image | Open tab; centered `无法打开此图片` |
| Animation | First frame only (GIF/WebP animation does not play) |
| Cache / Office | Skip cache; never call Office |
| Find | Images have no source text; SVG still searches source |
| Defaults | New suffixes join `associate.EXTENSIONS`; Settings claim stays `.pdf` |

## 3. Surfaces

- Shared `reader.preview.graphic_view.GraphicView` (paper fill, zoom, pan)
- `SvgView` / `ImageView` subclasses
- `reader.formats.image.to_preview` → `PreviewResult(kind="image", image_path=…)`
- sniff, associate, open dialog, welcome badges (`PNG` / `JPG` / `GIF` / `WEBP` / `BMP`)
- README + `docs/Reader功能全解.md`

## 4. Non-goals

- Zoom chrome on PDF / Markdown / PPTX (PPTX already has its own slide zoom)
- Ctrl+0 reset, pinch-zoom, or a visible zoom readout
- RAW / TIFF / ICO / HEIC
- Image editing

## 5. Testing

- Ctrl+wheel changes `zoom()`; wheel without Ctrl does not
- Graphic views have no slider / zoom button / percent label
- sniff / open / pipeline / associate / dialog accept the image suffixes
- `ImageView` loads a PNG; garbage file is invalid
- Caption hit tests stay green

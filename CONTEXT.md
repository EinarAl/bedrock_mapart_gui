# MapArt for Bedrock - GUI Version

## Goal
Desktop GUI that converts images into Minecraft Bedrock map art (128x128). Supports RGB and CIE Lab color matching with dithering, palettes, staircasing modes, and WebSocket-based in-game block placement.

## Stack
- Python 3.11+
- customtkinter (dark theme GUI framework)
- Pillow (image processing)
- numpy (color math)
- bedrockpy (Bedrock WebSocket protocol)
- adorable (CLI styling in server console)

## Architecture

### File Roles
| File | Role |
|---|---|
| `app.py` | Main GUI window, all UI components, event handlers, config save/load |
| `colour_data.py` | Minecraft block colour mapping (64 colour sets x 4 tones each), used by `presets.py` and `processor.py` |
| `presets.py` | Palette filtering by mode (wool, concrete, etc), builds block palettes from `colour_data.py` |
| `processor.py` | Image processing pipeline: resize, palette matching (RGB/Lab), dithering, staircasing expansion |
| `dither.py` | Dithering algorithms: Floyd-Steinberg, Bayer 2x2/4x4, Burkes, Sierra Lite, Stucki, Atkinson |
| `builder.py` | WebSocket server using bedrockpy, handles #build/#coords/#testblock commands in-game |
| `coordinates.py` | Coordinate save/load for multi-tile builds |
| `presets.py` | Palette filtering and block preference logic |
| `charcoal.json` | Charcoal block registry (bedrockpy server data) |

### Data Flow
1. User selects image -> cropped/resized to 128x128 -> saved to image directory
2. "Preview Map" -> `process_image()` -> palette matching (RGB or CIE Lab) -> dithering -> staircasing (3D expansion)
3. Block counts shown in materials list; pixelated preview rendered from matched colours
4. "Start Server" -> WebSocket server on bedrockpy -> in-game `/connect localhost:6464`
5. `#build image.png` reads saved 128x128 -> places blocks in-world via WebSocket commands

## How to Run
```powershell
cd D:\Cobalt\Projects\mapart-bedrock-gui
pip install -e .
mapart-gui
# or: python -m mapart_bedrock_gui.app
```

## Commands
- `python -m ruff check .` -- lint all source files
- `python -m ruff check --fix .` -- auto-fix lint issues
- `python -m pyright` -- type checking (when configured)

## Known Issues
- **Duplicate colour entries (FIXED)**: `orange_concrete_powder` and `orange_glazed_terracotta` had duplicate block entries in `colour_data.py` at Orange Wool colour set. Removed in migration.
- Type annotations missing across all modules (238 ANN warnings from ruff). Phase 2 to address.
- Bare `except` clauses in several places (should catch specific exceptions).
- Undefined `e` variable in two `except` blocks (line 981, 1145 in app.py -- `except Exception:` doesn't capture the exception var).
- `_reposition_dropdown` defined twice (lines 226 and 781) -- second definition shadows the first.
- Version-specific block filtering not yet implemented.
- Not bundled as .exe (PyInstaller).

## Current State
Migrated to D:\Cobalt\Projects\. Duplicate colour entries fixed. Ruff/pyright/pytest tooling config added. Ready for Phase 2 (UI Overhaul 1-on-1).

Project page: [[01_Projects/mapart-bedrock-gui]]

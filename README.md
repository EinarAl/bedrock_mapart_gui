# MapArt for Bedrock - GUI Version

Desktop app that converts images into Minecraft Bedrock map art (128x128). Supports RGB and CIE Lab color matching.

## Quick Start

### 1. Install

```powershell
cd path\to\mapart-bedrock-gui
pip install -e .
```

### 2. Launch

```powershell
mapart-gui
```

Or double-click `launch.bat`.

### 3. Select an image

Click **"Select Image"** and pick a `.png` or `.jpg`. Preview shows your image at 128x128.

### 4. Configure settings

- **Palette** - which blocks the tool can use
- **Dithering** - how colors blend together (try Floyd-Steinberg for photos)
- **Staircasing** - flat (2D) or with height variation (3D, more colors)
- **Color Mode** - RGB (default) or CIE Lab Delta-E
- **Dimension** - Overworld, End (transparent map bg), or Nether
- **Address/Port** - leave as `0.0.0.0` and `6464` unless you know what you're doing
- **Image Directory** - folder where images are stored for in-game access

### 5. Preview

Click **"Preview Map"** to see:
- Material counts (block types + quantities)
- Live preview of the block-colored version

After preview, click **"Copy Give Commands"** to copy `/give` commands.

### 6. Settings & Help

Click the **gear icon** (top-right) to change theme, accent color, enable **Give Materials** mode, or **Save/Load Presets**. Click **?** for the help guide.

### 7. Build in Minecraft

1. Click **"Start Server"**
2. Open Minecraft Bedrock, join your world
3. Press `/` and type: `/connect localhost:6464`
4. Stand where you want the top-left corner of the map art
5. In chat, type: `#build your_image_name.png`

Blocks place automatically. Keep still.

---

## Settings Explained

### Palette

| Palette | Blocks Used | Best For |
|---------|-------------|----------|
| All | Everything available | Best quality, any image |
| Wool | 16 wool colors | Survival-friendly, easy to get |
| Carpets | 16 carpet colors | Carpet duper farms |
| Concrete | 16 concrete colors | Clean solid colors |
| Terracotta | 16 terracotta colors | Muted/earthy tones |
| Greyscale | Grays + stone | Black & white images |

### Dithering

Dithering blends colors to fake more shades. Without it each pixel maps to the single closest block color.

| Method | Type | What it does |
|--------|------|-------------|
| None | - | No blending, flat colors, pixel-art look |
| Floyd-Steinberg | Error diffusion | Best for photos. Smooth, natural blends |
| Bayer 4x4 | Ordered | Patterned dots, retro game feel |
| Bayer 2x2 | Ordered | Coarser pattern than 4x4 |
| Burkes | Error diffusion | Smooth, slightly softer than Floyd |
| Sierra-Lite | Error diffusion | Fast, decent quality, subtle |
| Stucki | Error diffusion | Similar to Burkes, good all-rounder |
| Atkinson | Error diffusion | Keeps contrast, good for pixel art |

**Try this:** Photos > Floyd-Steinberg. Flat artwork > None. Pixel art > Atkinson or None.

### Staircasing

Normally all blocks sit flat at one height. Staircasing adds height variation for more color options:

| Mode | Effect |
|------|--------|
| Off (2D) | All blocks at same Y level. Simplest. |
| Classic (3D) | Blocks at +1, 0, or -1 height. More colors, up+down stairs. |
| Valley (3D) | Same colors as Classic, but only upward stairs. Easier survival build. |

With staircasing on, each color set contributes dark, normal, and light tones, tripling the palette.

### Address & Port

- **Address**: `0.0.0.0` means "listen on all network interfaces." Leave this.
- **Port**: `6464` is the standard Bedrock WebSocket port. Leave this unless something else uses it.

### Image Directory

Images you select are automatically copied here. When connected in-game, type `#build filename.png` and the server looks for it in this folder.

---

## In-Game Commands

Once the server is running and you're connected (`/connect localhost:6464`):

| Command | Description |
|---------|-------------|
| `#build image.png` | Build map art from image |
| `#build image.png --x=100 --z=200 --y=64` | Build at specific coordinates |
| `#coords saveat <x> <z> [name]` | Save a location so you don't reuse it |
| `#coords list` | Show saved locations |
| `#coords clear` | Clear all saved locations |
| `#help` | Show all commands |

If you don't specify `--x` and `--z`, the build starts at world origin `(0, 0)`.
Default `--y=-1`. Use `--y=64` to build at a higher elevation.
Example: `#build image.png --x=100 --z=200 --y=64`

---

## Tips

- **Build over an ocean or high in the sky** so you don't hit terrain
- **Open a map first** to initialize it, then check the top-left corner
- **Use a ticking area** if you leave the area (the tool creates one automatically)
- **128x128 blocks** (16,384 blocks total)
- **Creative mode** is easiest. In survival, make sure you have the materials

---

## Files

```
mapart-bedrock-gui/
+-- pyproject.toml
+-- README.md
+-- launch.bat              (double-click to launch)
+-- mapart_bedrock_gui/
    +-- __init__.py
    +-- app.py               (the GUI application)
    +-- colour_data.py       (64 color sets)
    +-- presets.py           (palette mode filtering)
    +-- processor.py         (image-to-block conversion)
    +-- dither.py            (dithering algorithms)
    +-- builder.py           (WebSocket server + block placer)
    +-- coordinates.py       (coordinate tracking)
```

---

## Requirements

- Python 3.11 or higher
- Minecraft Bedrock (any recent version)
- Windows (might work on macOS/Linux)

---

## Troubleshooting

**"Cannot connect to server"** - Make sure the server is started (green "Start Server" button), then in Minecraft type `/connect localhost:6464`. If on a different computer, use that computer's IP.

**"Image not found" in game** - The image must be in the Image Directory you set. The app copies selected images there automatically.

**Blocks not placing** - Make sure you're in the same world as the map you want to build. The tool places blocks using world coordinates.

**Port in use** - Change the port to something else (e.g. 6465) and use `/connect localhost:6465` in-game.

---

## License

MIT. Built with data from rebane2001's [MapartCraft](https://rebane2001.com/mapartcraft/) and [bedrock-ws/mapart](https://github.com/bedrock-ws/mapart).

# MapArt for Bedrock - GUI Version

## How to run
```powershell
cd path\to\mapart-bedrock-gui
pip install -e .
mapart-gui  # or: python -m mapart_bedrock_gui.app
```

## How it works
- Select an image → preview shows original and (after Preview) the block-colored version
- Palette, Dither, Staircasing, Color Mode dropdowns with descriptions
- Dimension selector (Overworld/End/Nether) with description
- CIE Lab Delta-E or RGB color matching (RGB is default)
- Single-map: any image is center-cropped to a square and resized to 128×128
- Settings gear → theme/accent, Give Materials toggle, Save/Load Presets
- Help button (?) → comprehensive usage guide
- File logging at ~/.mapart/mapart.log
- Live pixelated preview shows the actual block colors after clicking "Preview Map"
- "Preview Map" processes image → shows materials list
- "Copy Give Commands" copies /give @s <block> <count> to clipboard
- "Start Server" runs WebSocket server, connects via /connect localhost:6464
- In-game: #build image.png
- #coords saveat/list/clear commands

## Known improvements
- Version-specific block filtering
- Bundled as .exe (PyInstaller)

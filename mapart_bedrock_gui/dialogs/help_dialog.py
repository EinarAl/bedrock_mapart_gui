import customtkinter as ctk

_HELP_TEXT = (
    "HOW TO USE MAPART FOR BEDROCK\n"
    "================================\n\n"
    "1. SELECT AN IMAGE\n"
    '   Click "Select Image" and pick a .png or .jpg.\n\n'
    "2. CHOOSE YOUR SETTINGS\n"
    "   Palette - which blocks to use (All, Wool, Carpets, etc.)\n"
    "   Dithering - how colors blend (try Floyd-Steinberg for photos)\n"
    "   Staircasing - flat or 3D for more colors\n"
    "   Color Mode - Lab (CIE Delta-E) or RGB\n\n"
    "3. DIMENSION\n"
    "   Overworld (default), End (transparent background), Nether.\n"
    "   You must be in this dimension in-game.\n"
    "   End dimension void = transparent sections on the map.\n\n"
    "4. PREVIEW\n"
    '   Click "Preview Map" to see block counts.\n'
    "   The preview updates to show the block-colored result.\n"
    '   Use "Copy Give Commands" for /give commands.\n\n'
    "5. START THE SERVER\n"
    '   Click "Start Server". Status bar shows "Server live!".\n\n'
    "6. CONNECT IN MINECRAFT\n"
    "   Open your world. Press / to open chat.\n"
    "   Type:  /connect localhost:6464\n\n"
    "7. BUILD THE ART\n"
    "   In chat, type:  #build your_image_name.png\n"
    "   Default origin is (0, -1, 0). Add --x= --z= --y= for coords:\n"
    "   #build image.png --x=100 --z=200 --y=64\n\n"
    "8. STOP THE SERVER\n"
    '   Click "Stop Server" when done.\n\n'
    "---\n\n"
    "SINGLE-MAP (128x128)\n"
    "   Images are center-cropped to a square and resized\n"
    "   to 128x128. Each pixel becomes one block, and the\n"
    "   full image fits on a single map.\n\n"
    "---\n\n"
    "WHERE DOES THE WORLD NEED TO BE?\n"
    "   Anywhere. The tool connects to YOUR MINECRAFT CLIENT,\n"
    "   not the server. Singleplayer, Realm, Aternos, server:\n"
    "   it all works the same way. /connect localhost:6464\n\n"
    "---\n\n"
    "SURVIVAL MODE?\n"
    '   Enable Settings > Give Materials in the menu bar for auto-/give.\n'
    '   Or use "Copy Give Commands" to get the commands.\n'
    "   The //setblock commands work in any gamemode.\n\n"
    "---\n\n"
    "TIPS\n"
    "  - Build high up (y=64+) or over ocean to avoid terrain\n"
    "  - The End dimension gives transparent map backgrounds\n"
    "  - Open a blank map first to see where it aligns\n"
    "  - Use #build image.png --x=100 --z=200 --y=64 for coords\n"
    "  - File > Save/Load Preset to save/load your config"
)


def open_help(parent):
    win = ctk.CTkToplevel(parent)
    win.title("How to Use - MapArt for Bedrock")
    win.geometry("620x540")
    win.transient(parent)

    text = ctk.CTkTextbox(win, wrap="word", font=("Segoe UI", 12))
    text.pack(fill="both", expand=True, padx=15, pady=15)
    text.insert("1.0", _HELP_TEXT)
    text.configure(state="disabled")
    return win

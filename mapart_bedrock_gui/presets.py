from .colour_data import COLOUR_SETS

def _preferred_blocks(mode: str):
    match mode:
        case "wool":
            return {
                "white_wool", "orange_wool", "magenta_wool", "light_blue_wool",
                "yellow_wool", "lime_wool", "pink_wool", "gray_wool",
                "light_gray_wool", "cyan_wool", "purple_wool", "blue_wool",
                "brown_wool", "green_wool", "red_wool", "black_wool",
            }
        case "carpets":
            return {
                "white_carpet", "orange_carpet", "magenta_carpet", "light_blue_carpet",
                "yellow_carpet", "lime_carpet", "pink_carpet", "gray_carpet",
                "light_gray_carpet", "cyan_carpet", "purple_carpet", "blue_carpet",
                "brown_carpet", "green_carpet", "red_carpet", "black_carpet",
            }
        case "concrete":
            return {
                "white_concrete", "orange_concrete", "magenta_concrete", "light_blue_concrete",
                "yellow_concrete", "lime_concrete", "pink_concrete", "gray_concrete",
                "light_gray_concrete", "cyan_concrete", "purple_concrete", "blue_concrete",
                "brown_concrete", "green_concrete", "red_concrete", "black_concrete",
            }
        case "terracotta":
            return {
                "white_terracotta", "orange_terracotta", "magenta_terracotta",
                "light_blue_terracotta", "yellow_terracotta", "lime_terracotta",
                "pink_terracotta", "gray_terracotta", "light_gray_terracotta",
                "cyan_terracotta", "purple_terracotta", "blue_terracotta",
                "brown_terracotta", "green_terracotta", "red_terracotta", "black_terracotta",
            }
        case _:
            return set()


def get_palette_by_mode(mode: str):
    preferred = _preferred_blocks(mode)

    match mode:
        case "all" | "greyscale":
            if mode == "greyscale":
                extra = {"stone", "cobblestone", "andesite"}
                preferred = _preferred_blocks("wool") | _preferred_blocks("concrete") | extra
            return _build_palette_with_preference(preferred) if preferred else _build_palette_all()

        case _:
            return _build_palette_with_preference(preferred)


def _build_palette_all():
    palette = {}
    for cs_id, cs in COLOUR_SETS.items():
        rgb = cs["tonesRGB"]["normal"]
        if cs["blocks"]:
            palette[rgb] = cs["blocks"][0]["name"]
    return palette


def _build_palette_with_preference(preferred):
    palette = {}
    for cs_id, cs in COLOUR_SETS.items():
        rgb = cs["tonesRGB"]["normal"]
        matching_preferred = [b["name"] for b in cs["blocks"] if b["name"] in preferred]
        if matching_preferred:
            palette[rgb] = matching_preferred[0]
    return palette


ALL_BLOCKS_PALETTE = get_palette_by_mode("all")

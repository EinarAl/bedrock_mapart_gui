import json
from pathlib import Path

COORDS_FILE = "mapart_coords.json"

USED_COORDS: list[dict] = []


def load_coords(data_dir: Path):
    global USED_COORDS
    coords_path = data_dir / COORDS_FILE
    if coords_path.exists():
        with open(coords_path) as f:
            USED_COORDS = json.load(f)
    else:
        USED_COORDS = []


def save_coords(data_dir: Path):
    coords_path = data_dir / COORDS_FILE
    with open(coords_path, "w") as f:
        json.dump(USED_COORDS, f, indent=2)


def add_coord(data_dir: Path, x: int, y: int, z: int, name: str = ""):
    global USED_COORDS
    entry = {"x": x, "y": y, "z": z, "name": name or f"MapArt {len(USED_COORDS) + 1}"}
    USED_COORDS.append(entry)
    save_coords(data_dir)
    return entry


def is_coord_used(x: int, z: int, margin: int = 256) -> bool:
    for c in USED_COORDS:
        if abs(c["x"] - x) < margin and abs(c["z"] - z) < margin:
            return True
    return False


def map_bottom_left(player_x: int, player_z: int) -> tuple:
    map_x = player_x & ~127
    map_z = player_z & ~127
    return map_x, map_z

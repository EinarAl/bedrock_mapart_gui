import numpy as np
from PIL import Image
from typing import List, Tuple, Optional, Literal
from .colour_data import COLOUR_SETS
from .presets import get_palette_by_mode
from .dither import apply_dithering

MAP_TILE = 128


def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    rn, gn, bn = r / 255.0, g / 255.0, b / 255.0

    def linearize(c: float) -> float:
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92

    rl, gl, bl = linearize(rn), linearize(gn), linearize(bn)

    x = rl * 0.4124564 + gl * 0.3575761 + bl * 0.1804375
    y = rl * 0.2126729 + gl * 0.7151522 + bl * 0.0721750
    z = rl * 0.0193339 + gl * 0.1191920 + bl * 0.9503041

    xn, yn, zn = 0.95047, 1.0, 1.08883
    x, y, z = x / xn, y / yn, z / zn

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else (903.3 * t + 16) / 116

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))




def _crop_center_square(im):
    w, h = im.size
    size = min(w, h)
    left = (w - size) // 2
    top = (h - size) // 2
    return im.crop((left, top, left + size, top + size))

def process_image(
    image_path: str,
    palette_mode: str = "all",
    dither: str = "none",
    staircasing: str = "off",
    color_mode: Literal["rgb", "lab"] = "lab",
) -> Tuple[List[Tuple[int, int, int, str, str, Tuple[int, int, int]]], int, int]:
    im = Image.open(image_path).convert("RGB")
    im = _crop_center_square(im)
    im = im.resize((MAP_TILE, MAP_TILE), Image.Resampling.LANCZOS)

    palette = _build_colour_set_palette(palette_mode, staircasing)
    palette_rgbs = list(palette.keys())

    if color_mode == "lab":
        palette_labs = {prgb: rgb_to_lab(*prgb) for prgb in palette_rgbs}
        _closest_fn = _lab_closest_factory(palette_labs)
        _closest_n_fn = _lab_closest_n_factory(palette_rgbs, palette_labs)
    else:
        _closest_fn = _rgb_closest_factory(palette_rgbs)
        _closest_n_fn = _rgb_closest_n_factory(palette_rgbs)

    pixels = np.array(im, dtype=np.uint8)

    if dither != "none":
        if color_mode == "lab":
            palette_for_dither = list(palette_labs.keys())
            find_closest = _lab_find_closest_in_list_factory(
                palette_for_dither, palette_labs,
            )
        else:
            palette_for_dither = palette_rgbs
            find_closest = _find_closest_in_list_rgb
        pixels = apply_dithering(pixels, palette_for_dither, find_closest, dither)

    tone_height = {"normal": 0, "dark": 1, "light": -1}

    blocks = []
    for z in range(MAP_TILE):
        for x in range(MAP_TILE):
            r, g, b = int(pixels[z, x, 0]), int(pixels[z, x, 1]), int(pixels[z, x, 2])
            block_name, tone, matched_rgb = _find_best_block(
                (r, g, b), palette, staircasing,
                color_mode,
            )
            dy = tone_height.get(tone, 0) if staircasing != "off" else 0
            blocks.append((x, z, dy, block_name, tone, matched_rgb))

    return blocks, MAP_TILE, MAP_TILE


def _build_colour_set_palette(palette_mode: str, staircasing: str):
    base = get_palette_by_mode(palette_mode)
    tone_keys = ["normal"]
    if staircasing in ("classic", "valley"):
        tone_keys = ["dark", "normal", "light"]
    palette = {}
    for cs_id, cs in COLOUR_SETS.items():
        normal_rgb = cs["tonesRGB"]["normal"]
        if normal_rgb not in base:
            continue
        block_name = base[normal_rgb]
        for tone in tone_keys:
            rgb = cs["tonesRGB"][tone]
            palette[rgb] = {"block": block_name, "tone": tone, "colour_set": cs_id}
    return palette


def _find_best_block(rgb, palette, staircasing, color_mode):
    best_dist = float("inf")
    best = None
    best_rgb = None
    if color_mode == "lab":
        lab_target = rgb_to_lab(*rgb)
        for prgb, info in palette.items():
            lab_prgb = rgb_to_lab(*prgb)
            d = (lab_target[0] - lab_prgb[0]) ** 2
            d += (lab_target[1] - lab_prgb[1]) ** 2
            d += (lab_target[2] - lab_prgb[2]) ** 2
            if d < best_dist:
                best_dist = d
                best = info
                best_rgb = prgb
    else:
        for prgb, info in palette.items():
            d = (rgb[0] - prgb[0]) ** 2 + (rgb[1] - prgb[1]) ** 2 + (rgb[2] - prgb[2]) ** 2
            if d < best_dist:
                best_dist = d
                best = info
                best_rgb = prgb
    return best["block"], best["tone"], best_rgb


def _lab_closest_factory(palette_labs):
    def closest(rgb, *_):
        lab = rgb_to_lab(*rgb)
        best_dist = float("inf")
        best = None
        for prgb, plab in palette_labs.items():
            d = (lab[0] - plab[0]) ** 2 + (lab[1] - plab[1]) ** 2 + (lab[2] - plab[2]) ** 2
            if d < best_dist:
                best_dist = d
                best = prgb
        return best
    return closest


def _lab_closest_n_factory(palette_rgbs, palette_labs):
    def closest_n(rgb, n):
        lab = rgb_to_lab(*rgb)
        distances = []
        for prgb in palette_rgbs:
            plab = palette_labs[prgb]
            d = (lab[0] - plab[0]) ** 2 + (lab[1] - plab[1]) ** 2 + (lab[2] - plab[2]) ** 2
            distances.append((prgb, d))
        distances.sort(key=lambda x: x[1])
        return distances[:n]
    return closest_n


def _rgb_closest_factory(palette_rgbs):
    def closest(rgb, *_):
        best_dist = float("inf")
        best = None
        for prgb in palette_rgbs:
            d = (rgb[0] - prgb[0]) ** 2 + (rgb[1] - prgb[1]) ** 2 + (rgb[2] - prgb[2]) ** 2
            if d < best_dist:
                best_dist = d
                best = prgb
        return best
    return closest


def _rgb_closest_n_factory(palette_rgbs):
    def closest_n(rgb, n):
        distances = []
        for prgb in palette_rgbs:
            d = (rgb[0] - prgb[0]) ** 2 + (rgb[1] - prgb[1]) ** 2 + (rgb[2] - prgb[2]) ** 2
            distances.append((prgb, d))
        distances.sort(key=lambda x: x[1])
        return distances[:n]
    return closest_n


def _lab_find_closest_in_list_factory(palette_rgbs, palette_labs):
    def closest_in_list(rgb, _palette_rgbs, n=1):
        lab = rgb_to_lab(*rgb)
        if n == 1:
            best_dist = float("inf")
            best = None
            for prgb in _palette_rgbs:
                plab = palette_labs[prgb]
                d = (lab[0] - plab[0]) ** 2 + (lab[1] - plab[1]) ** 2 + (lab[2] - plab[2]) ** 2
                if d < best_dist:
                    best_dist = d
                    best = prgb
            return best
        distances = []
        for prgb in _palette_rgbs:
            plab = palette_labs[prgb]
            d = (lab[0] - plab[0]) ** 2 + (lab[1] - plab[1]) ** 2 + (lab[2] - plab[2]) ** 2
            distances.append((prgb, d))
        distances.sort(key=lambda x: x[1])
        return distances[:n]
    return closest_in_list


def _find_closest_in_list_rgb(rgb, palette_rgbs, n=1):
    if n == 1:
        best_dist = float("inf")
        best = None
        for prgb in palette_rgbs:
            d = (rgb[0] - prgb[0]) ** 2 + (rgb[1] - prgb[1]) ** 2 + (rgb[2] - prgb[2]) ** 2
            if d < best_dist:
                best_dist = d
                best = prgb
        return best
    distances = []
    for prgb in palette_rgbs:
        d = (rgb[0] - prgb[0]) ** 2 + (rgb[1] - prgb[1]) ** 2 + (rgb[2] - prgb[2]) ** 2
        distances.append((prgb, d))
    distances.sort(key=lambda x: x[1])
    return distances[:n]

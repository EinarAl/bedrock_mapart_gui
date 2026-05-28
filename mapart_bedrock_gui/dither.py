import numpy as np
from typing import Callable


def apply_dithering(
    pixels: np.ndarray,
    palette_rgbs: list,
    find_closest: Callable,
    method: str = "none",
):
    h, w = pixels.shape[:2]
    result = np.zeros((h, w, 3), dtype=np.float32)
    result[:] = pixels.astype(np.float32)

    match method:
        case "none":
            pass
        case "floyd-steinberg":
            _error_diffusion(result, palette_rgbs, find_closest, FLOYD_STEINBERG, 16)
        case "bayer-4x4":
            return _ordered_dithering(pixels, palette_rgbs, find_closest, BAYER_4x4, 17)
        case "bayer-2x2":
            return _ordered_dithering(pixels, palette_rgbs, find_closest, BAYER_2x2, 5)
        case "burkes":
            _error_diffusion(result, palette_rgbs, find_closest, BURKES, 32)
        case "sierra-lite":
            _error_diffusion(result, palette_rgbs, find_closest, SIERRA_LITE, 4)
        case "stucki":
            _error_diffusion(result, palette_rgbs, find_closest, STUCKI, 42)
        case "atkinson":
            _error_diffusion(result, palette_rgbs, find_closest, ATKINSON, 8)

    return result.astype(np.uint8)


FLOYD_STEINBERG = [
    (1, 0, 7),
    (-1, 1, 3),
    (0, 1, 5),
    (1, 1, 1),
]

BURKES = [
    (1, 0, 8),
    (2, 0, 4),
    (-2, 1, 2),
    (-1, 1, 4),
    (0, 1, 8),
    (1, 1, 4),
    (2, 1, 2),
]

SIERRA_LITE = [
    (1, 0, 2),
    (-1, 1, 1),
    (0, 1, 1),
]

STUCKI = [
    (1, 0, 8),
    (2, 0, 4),
    (-2, 1, 2),
    (-1, 1, 4),
    (0, 1, 8),
    (1, 1, 4),
    (2, 1, 2),
    (-2, 2, 1),
    (-1, 2, 2),
    (0, 2, 4),
    (1, 2, 2),
    (2, 2, 1),
]

ATKINSON = [
    (1, 0, 1),
    (2, 0, 1),
    (-1, 1, 1),
    (0, 1, 1),
    (1, 1, 1),
    (0, 2, 1),
]

BAYER_4x4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]

BAYER_2x2 = [
    [0, 2],
    [3, 1],
]


def _error_diffusion(
    pixels: np.ndarray,
    palette_rgbs: list,
    find_closest: Callable,
    pattern: list,
    divisor: int,
):
    h, w = pixels.shape[:2]

    for y in range(h):
        for x in range(w):
            old_pixel = pixels[y, x].copy()
            closest = find_closest(old_pixel, palette_rgbs)
            new_pixel = np.array(closest, dtype=np.float32)
            pixels[y, x] = new_pixel
            error = old_pixel - new_pixel

            for dx, dy, weight in pattern:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    pixels[ny, nx] += error * (weight / divisor)


def _ordered_dithering(
    pixels: np.ndarray,
    palette_rgbs: list,
    find_closest: Callable,
    matrix: list,
    levels: int,
):
    h, w = pixels.shape[:2]
    result = np.zeros_like(pixels)
    msize = len(matrix)

    for y in range(h):
        for x in range(w):
            threshold = (matrix[y % msize][x % msize] + 0.5) / levels
            pixel = pixels[y, x].astype(np.float32)

            two = find_closest(pixel, palette_rgbs, n=2)
            if len(two) == 2:
                c1 = np.array(two[0][0], dtype=np.float32)
                c2 = np.array(two[1][0], dtype=np.float32)
                result[y, x] = c1 if threshold > 0.5 else c2
            else:
                result[y, x] = two[0][0]

    return result.astype(np.uint8)

from pathlib import Path

__all__ = [
    "CONFIG_VERSION", "LOG_DIR", "PALETTE_OPTIONS", "DITHER_OPTIONS",
    "STAIRCASING_OPTIONS", "DIMENSION_OPTIONS", "DEFAULT_BG_HEX",
    "DEFAULT_ACCENT_HEX", "PRESETS_DIR", "CONFIG_PATH",
]

CONFIG_VERSION = 2
LOG_DIR = Path.home() / ".mapart"
LOG_DIR.mkdir(parents=True, exist_ok=True)

PALETTE_OPTIONS = [
    ("all", "All blocks - best quality, uses everything available"),
    ("wool", "16 wool colors only - survival-friendly, easy to obtain"),
    ("carpets", "16 carpet colors only - good for carpet duper setups"),
    ("concrete", "16 concrete colors - clean, solid, vibrant colors"),
    ("terracotta", "16 terracotta colors - muted, earthy tones"),
    ("greyscale", "Grays + stone - perfect for black & white images"),
]

DITHER_OPTIONS = [
    ("none", "No dithering - solid flat colors, pixel-art look"),
    ("floyd-steinberg", "Best quality smooth blending, good for photos"),
    ("bayer-4x4", "Ordered pattern dithering, retro game feel"),
    ("bayer-2x2", "Coarser ordered pattern than 4x4"),
    ("burkes", "Smooth error diffusion, slightly softer than Floyd"),
    ("sierra-lite", "Fast error diffusion, decent quality, lighter touch"),
    ("stucki", "Similar to Burkes, good general-purpose dither"),
    ("atkinson", "Preserves contrast well, good for pixel art style"),
]

STAIRCASING_OPTIONS = [
    ("off", "Flat (2D) - single Y level, simplest to build"),
    ("classic", "3D with up+down stairs - triples available colors"),
    ("valley", "3D with only upward stairs - easier survival build"),
]

DIMENSION_OPTIONS = [
    ("overworld", "Build in the Overworld (default)"),
    ("end", "Build in The End for transparent map background"),
    ("nether", "Build in the Nether"),
]

DEFAULT_BG_HEX = "#1a1a1a"
DEFAULT_ACCENT_HEX = "#4a4a4a"
PRESETS_DIR = LOG_DIR / "presets"
CONFIG_PATH = LOG_DIR / "config.json"

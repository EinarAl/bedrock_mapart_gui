import asyncio
import json
import logging
import os
import threading
import time
from pathlib import Path
import tkinter as tk
import tkinter.colorchooser as tkc
from tkinter import filedialog, messagebox

import customtkinter as ctk
import numpy as np
from PIL import Image

from .builder import MapartBuilder
from .processor import process_image, MAP_TILE

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")  # will be overridden by _apply_custom_theme()

CONFIG_VERSION = 2
LOG_DIR = Path.home() / ".mapart"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "mapart.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mapart")

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


class MapartGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MapArt for Bedrock")
        self.geometry("1000+100")
        self.minsize(820, 620)

        self.selected_image_path = None
        self.preview_image_ctk = None
        self.server_thread = None
        self.server_instance = None
        self.material_counts = {}
        self.blocks_data = []
        self.image_width = 0
        self.image_height = 0
        self.live_preview_image = None
        self._preview_pil = None
        self._preview_is_live = False
        self.bg_hex = DEFAULT_BG_HEX
        self.accent_hex = DEFAULT_ACCENT_HEX
        self._option_menus = []
        self._dropdown_anchor = None
        self._hover_timer = None
        self.give_materials_mode = False
        self.give_materials_var = tk.BooleanVar(value=False)
        self.color_mode = "rgb"

        logger.info("Application started")
        self._build_ui()
        self._load_config()
        self._apply_custom_theme()
        self._bind_events()

    def _load_config(self):
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    cfg = json.load(f)
                saved_version = cfg.get("config_version", 1)
                if "image_directory" in cfg:
                    self.dir_path_var.set(cfg["image_directory"])
                self.bg_hex = cfg.get("bg_hex", DEFAULT_BG_HEX)
                self.accent_hex = cfg.get("accent_hex", DEFAULT_ACCENT_HEX)
                if hasattr(self, "palette_var"):
                    self.palette_var.set(cfg.get("palette", "all"))
                    self.dither_var.set(cfg.get("dither", "none"))
                    if saved_version < 2:
                        self.color_mode_var.set("rgb")
                        self.staircasing_var.set("off")
                    else:
                        self.staircasing_var.set(cfg.get("staircasing", "off"))
                        self.color_mode_var.set(cfg.get("color_mode", "rgb"))
                    self.dimension_var.set(cfg.get("dimension", "overworld"))
                    give = cfg.get("give_materials", False)
                    self.give_materials_var.set(give)
                    self.give_materials_mode = give
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    def _save_config(self):
        try:
            cfg = {
                "config_version": CONFIG_VERSION,
                "image_directory": self.dir_path_var.get(),
                "bg_hex": self.bg_hex,
                "accent_hex": self.accent_hex,
                "palette": self.palette_var.get(),
                "dither": self.dither_var.get(),
                "staircasing": self.staircasing_var.get(),
                "color_mode": self.color_mode_var.get(),
                "dimension": self.dimension_var.get(),
                "give_materials": self.give_materials_var.get(),
            }
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save config: {e}")

    def _build_menu_bar(self):
        bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)

        menu_btn_kw = {
            "height": 26, "font": ("Segoe UI", 12),
            "fg_color": "transparent", "text_color": ("gray10", "#DCE4EE"),
            "hover_color": ("gray60", self._lighten(self.accent_hex, 0.3)),
            "corner_radius": 4,
        }

        def _hover_enter(name):
            if self._hover_timer:
                self.after_cancel(self._hover_timer)
            self._hover_timer = self.after(120, lambda: self._show_named_dropdown(name))

        def _hover_leave():
            if self._hover_timer:
                self.after_cancel(self._hover_timer)
            self._hover_timer = self.after(350, self._close_dropdown)

        self._menu_file = ctk.CTkButton(bar, text="File", width=44, **menu_btn_kw)
        self._menu_file.pack(side="left", padx=(6, 1), pady=2)
        self._menu_file.bind("<Enter>", lambda e: _hover_enter("file"))
        self._menu_file.bind("<Leave>", lambda e: _hover_leave())

        self._menu_settings = ctk.CTkButton(bar, text="Theme", width=66, **menu_btn_kw)
        self._menu_settings.pack(side="left", padx=1, pady=2)
        self._menu_settings.bind("<Enter>", lambda e: _hover_enter("settings"))
        self._menu_settings.bind("<Leave>", lambda e: _hover_leave())

        self._menu_help = ctk.CTkButton(bar, text="Help", width=44, **menu_btn_kw)
        self._menu_help.pack(side="left", padx=1, pady=2)
        self._menu_help.bind("<Enter>", lambda e: _hover_enter("help"))
        self._menu_help.bind("<Leave>", lambda e: _hover_leave())

        ctk.CTkLabel(bar, text="v0.2", text_color=("gray50", "gray60"),
                     font=("Segoe UI", 10)).pack(side="right", padx=10)
        self._active_dropdown = None

    def _show_named_dropdown(self, name):
        if name == "file":
            self._show_file_dropdown()
        elif name == "settings":
            self._show_settings_dropdown()
        elif name == "help":
            self._show_help_dropdown()

    @staticmethod
    def _lighten(hex_color, factor=0.2):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(hex_color, factor=0.2):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _close_dropdown(self, event=None):
        if self._active_dropdown is not None and self._active_dropdown.winfo_exists():
            try:
                self._active_dropdown.destroy()
            except:
                pass
            self._active_dropdown = None
            self._dropdown_anchor = None

    def _reposition_dropdown(self, event=None):
        if self._active_dropdown is not None and self._active_dropdown.winfo_exists() and self._dropdown_anchor is not None:
            try:
                x = self._dropdown_anchor.winfo_rootx()
                y = self._dropdown_anchor.winfo_rooty() + self._dropdown_anchor.winfo_height()
                self._active_dropdown.geometry(f"+{x}+{y}")
            except:
                pass

    def _build_dropdown(self, anchor_btn, populate_fn):
        self._close_dropdown()
        self._dropdown_anchor = anchor_btn
        x = anchor_btn.winfo_rootx()
        y = anchor_btn.winfo_rooty() + anchor_btn.winfo_height()
        win = ctk.CTkToplevel(self)
        win.overrideredirect(True)
        win.transient(self)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.bind("<Escape>", lambda e: self._close_dropdown())
        frame = ctk.CTkFrame(win, corner_radius=8, border_width=1, border_color=("gray70", self._lighten(self.bg_hex, 0.25)))
        frame.pack(fill="both", expand=True)
        populate_fn(frame, win)
        win.update_idletasks()
        w = max(180, frame.winfo_reqwidth())
        h = frame.winfo_reqheight()
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.focus_set()
        win.grab_set()
        win.bind("<Enter>", lambda e: self._hover_cancel_close())
        win.bind("<Leave>", lambda e: self._hover_schedule_close())
        self._active_dropdown = win

    def _show_file_dropdown(self):
        btn_style = {"fg_color": "transparent", "text_color": ("gray10", "#DCE4EE"),
                     "hover_color": self._lighten(self.accent_hex, 0.3)}

        def _save(win):
            win.destroy()
            self.after(50, self._save_preset_action)

        def _load(win):
            win.destroy()
            self.after(50, self._load_preset_action)

        def _exit(win):
            win.destroy()
            self.after(50, self._on_close)

        def populate(frame, win):
            ctk.CTkButton(frame, text="Save Preset...", height=28, anchor="w",
                          command=lambda: _save(win),
                          font=("Segoe UI", 12), **btn_style).pack(fill="x", padx=6, pady=3)
            ctk.CTkButton(frame, text="Load Preset...", height=28, anchor="w",
                          command=lambda: _load(win),
                          font=("Segoe UI", 12), **btn_style).pack(fill="x", padx=6, pady=3)
            ctk.CTkFrame(frame, height=1, fg_color=("gray70", self._lighten(self.bg_hex, 0.25))).pack(fill="x", padx=6, pady=3)
            ctk.CTkButton(frame, text="Exit", height=28, anchor="w",
                          command=lambda: _exit(win),
                          font=("Segoe UI", 12), **btn_style).pack(fill="x", padx=6, pady=3)
        self._build_dropdown(self._menu_file, populate)

    def _show_settings_dropdown(self):
        def _open_bg_picker(win):
            win.destroy()
            self.after(50, self._pick_background_color)

        def _open_accent_picker(win):
            win.destroy()
            self.after(50, self._pick_accent_color)

        def _toggle_give(win):
            win.destroy()
            self._toggle_give_materials()

        def populate(frame, win):
            ctk.CTkLabel(frame, text="Background", font=("Segoe UI", 11, "bold")).pack(pady=(6, 2), padx=8, anchor="w")
            bg_f = ctk.CTkFrame(frame, fg_color="transparent")
            bg_f.pack(fill="x", padx=8, pady=(0, 4))
            ctk.CTkLabel(bg_f, text="     ", fg_color=self.bg_hex, corner_radius=4, width=28).pack(side="left", padx=(0, 4))
            ctk.CTkButton(bg_f, text=self.bg_hex, height=24, anchor="w",
                          command=lambda: _open_bg_picker(win),
                          font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True)
            ctk.CTkFrame(frame, height=1, fg_color=("gray70", self._lighten(self.bg_hex, 0.25))).pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(frame, text="Accent", font=("Segoe UI", 11, "bold")).pack(pady=(2, 2), padx=8, anchor="w")
            ac_f = ctk.CTkFrame(frame, fg_color="transparent")
            ac_f.pack(fill="x", padx=8, pady=(0, 4))
            ctk.CTkLabel(ac_f, text="     ", fg_color=self.accent_hex, corner_radius=4, width=28).pack(side="left", padx=(0, 4))
            ctk.CTkButton(ac_f, text=self.accent_hex, height=24, anchor="w",
                          command=lambda: _open_accent_picker(win),
                          font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True)
            ctk.CTkFrame(frame, height=1, fg_color=("gray70", self._lighten(self.bg_hex, 0.25))).pack(fill="x", padx=8, pady=4)
            give_text = f"Give Materials: {'ON' if self.give_materials_mode else 'OFF'}"
            ctk.CTkButton(frame, text=give_text, height=28,
                          command=lambda: _toggle_give(win),
                          font=("Segoe UI", 12)).pack(fill="x", padx=8, pady=4)
        self._build_dropdown(self._menu_settings, populate)

    def _show_help_dropdown(self):
        def _show_help(win):
            win.destroy()
            self.after(50, self._open_help)

        def populate(frame, win):
            ctk.CTkButton(frame, text="How to Use", height=28, anchor="w",
                          fg_color="transparent", text_color=("gray10", "#DCE4EE"),
                          hover_color=self._lighten(self.accent_hex, 0.3),
                          command=lambda: _show_help(win),
                          font=("Segoe UI", 12)).pack(fill="x", padx=6, pady=3)
        self._build_dropdown(self._menu_help, populate)

    def _generate_theme_file(self, bg_hex, accent_hex):
        theme = {
            "CTk": {"fg_color": ["gray95", bg_hex]},
            "CTkToplevel": {"fg_color": ["gray95", bg_hex]},
            "CTkFrame": {"corner_radius": 6, "border_width": 0, "fg_color": ["gray90", bg_hex], "top_fg_color": ["gray85", self._lighten(bg_hex, 0.05)], "border_color": ["gray65", self._lighten(bg_hex, 0.15)]},
            "CTkButton": {"corner_radius": 6, "border_width": 0, "fg_color": ["#4a4a4a", accent_hex], "hover_color": ["#3a3a3a", self._lighten(accent_hex, 0.2)], "border_color": ["#3E454A", self._lighten(accent_hex, 0.1)], "text_color": ["#DCE4EE", "#DCE4EE"], "text_color_disabled": ["gray74", "gray60"]},
            "CTkLabel": {"corner_radius": 0, "fg_color": "transparent", "text_color": ["gray14", "gray84"]},
            "CTkEntry": {"corner_radius": 6, "border_width": 2, "fg_color": ["#F9F9FA", self._lighten(bg_hex, 0.08)], "border_color": ["#979DA2", self._lighten(accent_hex, 0.3)], "text_color": ["gray14", "gray84"], "placeholder_text_color": ["gray52", "gray62"]},
            "CTkCheckBox": {"corner_radius": 6, "border_width": 3, "fg_color": ["#4a4a4a", accent_hex], "border_color": ["#3E454A", self._lighten(accent_hex, 0.1)], "hover_color": ["#3a3a3a", self._lighten(accent_hex, 0.2)], "checkmark_color": ["#DCE4EE", "gray90"], "text_color": ["gray14", "gray84"], "text_color_disabled": ["gray60", "gray45"]},
            "CTkSwitch": {"corner_radius": 1000, "border_width": 3, "button_length": 0, "fg_color": ["#939BA2", self._lighten(bg_hex, 0.2)], "progress_color": ["#4a4a4a", accent_hex], "button_color": ["gray36", "#D5D9DE"], "button_hover_color": ["gray20", "gray100"], "text_color": ["gray14", "gray84"], "text_color_disabled": ["gray60", "gray45"]},
            "CTkRadioButton": {"corner_radius": 1000, "border_width_checked": 6, "border_width_unchecked": 3, "fg_color": ["#4a4a4a", accent_hex], "border_color": ["#3E454A", self._lighten(accent_hex, 0.1)], "hover_color": ["#3a3a3a", self._lighten(accent_hex, 0.2)], "text_color": ["gray14", "gray84"], "text_color_disabled": ["gray60", "gray45"]},
            "CTkProgressBar": {"corner_radius": 1000, "border_width": 0, "fg_color": ["#939BA2", self._lighten(bg_hex, 0.2)], "progress_color": ["#4a4a4a", accent_hex], "border_color": ["gray", "gray"]},
            "CTkSlider": {"corner_radius": 1000, "button_corner_radius": 1000, "border_width": 6, "button_length": 0, "fg_color": ["#939BA2", self._lighten(bg_hex, 0.2)], "progress_color": ["gray40", accent_hex], "button_color": ["#4a4a4a", accent_hex], "button_hover_color": ["#3a3a3a", self._lighten(accent_hex, 0.2)]},
            "CTkOptionMenu": {"corner_radius": 6, "fg_color": ["#4a4a4a", accent_hex], "button_color": ["#3a3a3a", self._darken(accent_hex, 0.15)], "button_hover_color": ["#234567", self._lighten(accent_hex, 0.3)], "text_color": ["#DCE4EE", "#DCE4EE"], "text_color_disabled": ["gray74", "gray60"]},
            "CTkComboBox": {"corner_radius": 6, "border_width": 2, "fg_color": ["#F9F9FA", self._lighten(bg_hex, 0.08)], "border_color": ["#979DA2", self._lighten(accent_hex, 0.3)], "button_color": ["#979DA2", accent_hex], "button_hover_color": ["#6E7174", self._lighten(accent_hex, 0.2)], "text_color": ["gray14", "gray84"], "text_color_disabled": ["gray50", "gray45"]},
            "CTkScrollbar": {"corner_radius": 1000, "border_spacing": 4, "fg_color": "transparent", "button_color": ["gray55", self._lighten(bg_hex, 0.15)], "button_hover_color": ["gray40", self._lighten(bg_hex, 0.25)]},
            "CTkSegmentedButton": {"corner_radius": 6, "border_width": 2, "fg_color": ["#979DA2", self._lighten(bg_hex, 0.15)], "selected_color": ["#4a4a4a", accent_hex], "selected_hover_color": ["#3a3a3a", self._lighten(accent_hex, 0.2)], "unselected_color": ["#979DA2", self._lighten(bg_hex, 0.15)], "unselected_hover_color": ["gray70", self._lighten(bg_hex, 0.25)], "text_color": ["#DCE4EE", "#DCE4EE"], "text_color_disabled": ["gray74", "gray60"]},
            "CTkTextbox": {"corner_radius": 6, "border_width": 0, "fg_color": ["gray100", self._lighten(bg_hex, 0.08)], "border_color": ["#979DA2", self._lighten(accent_hex, 0.3)], "text_color": ["gray14", "gray84"], "scrollbar_button_color": ["gray55", self._lighten(bg_hex, 0.15)], "scrollbar_button_hover_color": ["gray40", self._lighten(bg_hex, 0.25)]},
            "CTkScrollableFrame": {"label_fg_color": ["gray80", self._lighten(bg_hex, 0.05)]},
            "DropdownMenu": {"fg_color": ["gray90", self._lighten(bg_hex, 0.15)], "hover_color": ["gray75", self._lighten(accent_hex, 0.3)], "text_color": ["gray14", "gray84"]},
            "CTkFont": {"macOS": {"family": "SF Display", "size": 13, "weight": "normal"}, "Windows": {"family": "Roboto", "size": 13, "weight": "normal"}, "Linux": {"family": "Roboto", "size": 13, "weight": "normal"}}
        }
        path = LOG_DIR / f"custom_theme_{int(time.time())}.json"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(theme, f, indent=2)
        return str(path)

    def _update_widget_colors(self):
        accent = self.accent_hex
        hover = self._lighten(accent, 0.2)
        for btn in (self._menu_file, self._menu_settings, self._menu_help):
            btn.configure(hover_color=hover)
        for widget in (self.preview_btn, self.start_btn, self.give_btn, self.select_btn):
            try:
                widget.configure(fg_color=accent, hover_color=hover)
            except:
                pass
        for om in self._option_menus:
            try:
                om.configure(fg_color=accent, button_color=self._darken(accent, 0.15),
                             button_hover_color=hover)
            except:
                pass

    def _apply_custom_theme(self):
        try:
            theme_path = self._generate_theme_file(self.bg_hex, self.accent_hex)
            ctk.set_default_color_theme(theme_path)
            self._update_widget_colors()
            self._log(f"Colors applied (restart for full effect)")
            logger.info(f"Custom theme applied: bg={self.bg_hex}, accent={self.accent_hex}")
        except Exception as e:
            self._log(f"Theme error: {e}")

    def _custom_color_picker(self, title, current_color):
        _PRESETS = [
            "#1a1a1a", "#2a2a2a", "#3a3a3a", "#4a4a4a", "#5a5a5a", "#6a6a6a",
            "#8b0000", "#cc0000", "#ff4444", "#ff8888",
            "#cc6600", "#ff8800", "#ffaa44", "#ffcc88",
            "#ccaa00", "#ffcc00", "#ffee44", "#ffee88",
            "#448800", "#66cc00", "#88ff44", "#aaff88",
            "#004488", "#0066cc", "#4488ff", "#88aaff",
            "#440088", "#6600cc", "#8844ff", "#aa88ff",
            "#880044", "#cc0066", "#ff4488", "#ff88aa",
        ]
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        result = [None]

        entry_var = ctk.StringVar(value=current_color)

        def is_valid_hex(h):
            return h.startswith("#") and len(h) == 7 and all(c in "0123456789abcdefABCDEF" for c in h[1:])

        def update_swatch(*_):
            v = entry_var.get().strip()
            if is_valid_hex(v):
                swatch.configure(fg_color=v, text=v)
            else:
                swatch.configure(fg_color="gray30", text="invalid")

        def pick_from_system():
            native = tkc.askcolor(title=title, initialcolor=entry_var.get())
            if native and native[1]:
                entry_var.set(native[1])

        def on_ok():
            v = entry_var.get().strip()
            if is_valid_hex(v):
                result[0] = v
                dialog.destroy()

        ctk.CTkLabel(dialog, text="Hex Color:", font=("Segoe UI", 12, "bold")).pack(pady=(12, 4))
        entry = ctk.CTkEntry(dialog, textvariable=entry_var, width=200,
                             placeholder_text="#RRGGBB", font=("Consolas", 13))
        entry.pack()
        entry_var.trace_add("write", update_swatch)

        swatch = ctk.CTkLabel(dialog, text=current_color, fg_color=current_color,
                              corner_radius=6, width=200, height=36,
                              font=("Consolas", 12, "bold"), text_color=("gray10", "#DCE4EE"))
        swatch.pack(pady=(8, 6))

        ctk.CTkLabel(dialog, text="Quick Colors:", font=("Segoe UI", 11)).pack()
        swatch_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        swatch_frame.pack(padx=10, pady=(2, 8))
        row = None
        for i, sc in enumerate(_PRESETS):
            if i % 8 == 0:
                row = ctk.CTkFrame(swatch_frame, fg_color="transparent")
                row.pack(pady=1)
            ctk.CTkButton(row, text="", width=24, height=18, fg_color=sc, hover_color=sc,
                          corner_radius=3, command=lambda v=sc: entry_var.set(v)).pack(side="left", padx=1)

        btn_f = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_f.pack(pady=(0, 12))
        ctk.CTkButton(btn_f, text="System Picker...", command=pick_from_system,
                      font=("Segoe UI", 11)).pack(side="left", padx=4)
        ctk.CTkButton(btn_f, text="OK", command=on_ok,
                      fg_color=self.accent_hex, hover_color=self._lighten(self.accent_hex, 0.2),
                      font=("Segoe UI", 11, "bold")).pack(side="left", padx=4)
        ctk.CTkButton(btn_f, text="Cancel", command=dialog.destroy,
                      font=("Segoe UI", 11)).pack(side="left", padx=4)

        update_swatch()
        dialog.grab_set()
        entry.focus_set()
        self.wait_window(dialog)
        return result[0]

    def _pick_background_color(self):
        color = self._custom_color_picker("Choose Background Color", self.bg_hex)
        if color:
            self.bg_hex = color
            self._apply_custom_theme()

    def _pick_accent_color(self):
        color = self._custom_color_picker("Choose Accent Color", self.accent_hex)
        if color:
            self.accent_hex = color
            self._apply_custom_theme()

    def _toggle_give_materials(self):
        self.give_materials_mode = self.give_materials_var.get()
        self._log(f"Give Materials: {'ON' if self.give_materials_mode else 'OFF'}")
        logger.info(f"Give Materials toggled to {self.give_materials_mode}")

    def _save_preset_action(self):
        name = filedialog.asksaveasfilename(
            title="Save Preset",
            initialdir=str(PRESETS_DIR),
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not name:
            return
        data = {
            "palette": self.palette_var.get(),
            "dither": self.dither_var.get(),
            "staircasing": self.staircasing_var.get(),
            "color_mode": self.color_mode_var.get(),
            "dimension": self.dimension_var.get(),
            "give_materials": self.give_materials_var.get(),
        }
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        with open(name, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved preset: {name}")
        self._log(f"Preset saved: {Path(name).name}")

    def _load_preset_action(self):
        name = filedialog.askopenfilename(
            title="Load Preset",
            initialdir=str(PRESETS_DIR),
            filetypes=[("JSON", "*.json")],
        )
        if not name:
            return
        with open(name) as f:
            data = json.load(f)
        self.palette_var.set(data.get("palette", "all"))
        self.dither_var.set(data.get("dither", "none"))
        self.staircasing_var.set(data.get("staircasing", "off"))
        self.color_mode_var.set(data.get("color_mode", "rgb"))
        self.dimension_var.set(data.get("dimension", "overworld"))
        give = data.get("give_materials", False)
        self.give_materials_var.set(give)
        self.give_materials_mode = give
        logger.info(f"Loaded preset: {name}")
        self._log(f"Preset loaded: {Path(name).name}")

    def _build_ui(self):
        self._build_menu_bar()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        main = ctk.CTkFrame(self)
        main.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        main.grid_columnconfigure(0, weight=0, minsize=300)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self._build_left_panel(main)
        self._build_right_panel(main)
        self._build_status_bar()

    def _build_left_panel(self, parent):
        left = ctk.CTkFrame(parent, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="Preview", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, pady=(10, 0),
        )

        self.preview_label = ctk.CTkLabel(
            left,
            text="No image selected\n\nSelect an image to see\nthe map art preview",
            fg_color=("gray85", "gray20"),
            corner_radius=8,
        )
        self.preview_label.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        self.preview_label.bind("<Configure>", self._update_preview_size)
        self.preview_label.bind("<Button-1>", self._open_fullsize_view)

        self.progress_bar = ctk.CTkProgressBar(left, mode="indeterminate", height=6, corner_radius=3)
        self.progress_bar.grid(row=2, column=0, padx=20, pady=0, sticky="ew")
        self.progress_bar.grid_remove()

        self.select_btn = ctk.CTkButton(
            left, text="Select Image",
            command=self._select_image,
            height=36, font=("Segoe UI", 13),
        )
        self.select_btn.grid(row=3, column=0, pady=(5, 5), padx=10, sticky="ew")

        self.image_info_label = ctk.CTkLabel(
            left, text="", font=("Segoe UI", 11),
        )
        self.image_info_label.grid(row=4, column=0, pady=(0, 10), padx=10)

    def _build_right_panel(self, parent):
        right = ctk.CTkScrollableFrame(parent, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="Settings", font=("Segoe UI", 16, "bold")).pack(
            pady=(10, 10),
        )

        self._add_dropdown(right, "Palette", PALETTE_OPTIONS, "palette_var", "all")
        self._add_dropdown(right, "Dithering", DITHER_OPTIONS, "dither_var", "none")
        self._add_dropdown(right, "Staircasing", STAIRCASING_OPTIONS, "staircasing_var", "off")

        sep1 = ctk.CTkFrame(right, height=2, fg_color=("gray70", "gray30"))
        sep1.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(right, text="Color Matching", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 5),
        )
        cm_frame = ctk.CTkFrame(right, fg_color="transparent")
        cm_frame.pack(fill="x", padx=10, pady=2)
        self.color_mode_var = ctk.StringVar(value="rgb")
        cm_dropdown = ctk.CTkOptionMenu(
            cm_frame, values=["rgb", "lab"],
            variable=self.color_mode_var, width=120,
        )
        cm_dropdown.pack(side="left")
        self._option_menus.append(cm_dropdown)
        ctk.CTkLabel(
            cm_frame,
            text="Color Mode - CIE Lab Delta-E vs RGB distance",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            wraplength=320, justify="left",
        ).pack(side="left", padx=(10, 0))

        sep_dim = ctk.CTkFrame(right, height=2, fg_color=("gray70", "gray30"))
        sep_dim.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(right, text="Dimension", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 5),
        )
        dim_frame = ctk.CTkFrame(right, fg_color="transparent")
        dim_frame.pack(fill="x", padx=10, pady=2)
        dim_values = [d[0] for d in DIMENSION_OPTIONS]
        dim_descs = {d[0]: d[1] for d in DIMENSION_OPTIONS}
        self.dimension_var = ctk.StringVar(value="overworld")
        dim_dropdown = ctk.CTkOptionMenu(
            dim_frame, values=dim_values,
            variable=self.dimension_var, width=120,
        )
        dim_dropdown.pack(side="left")
        self._option_menus.append(dim_dropdown)
        self.dim_desc_label = ctk.CTkLabel(
            dim_frame, text=dim_descs["overworld"],
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            wraplength=320, justify="left",
        )
        self.dim_desc_label.pack(side="left", padx=(10, 0))
        dim_dropdown.configure(
            command=lambda c: self.dim_desc_label.configure(text=dim_descs[c]),
        )
        ctk.CTkLabel(
            right,
            text="You must be in this dimension in-game.\nFor End: void background = transparent map sections.",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            justify="left", wraplength=380,
        ).pack(pady=(2, 5), anchor="w", padx=10)

        sep2 = ctk.CTkFrame(right, height=2, fg_color=("gray70", "gray30"))
        sep2.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(right, text="Server", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 5),
        )

        addr_frame = ctk.CTkFrame(right, fg_color="transparent")
        addr_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(addr_frame, text="Address:", width=70, anchor="w").pack(side="left")
        self.address_entry = ctk.CTkEntry(addr_frame, placeholder_text="0.0.0.0")
        self.address_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.address_entry.insert(0, "0.0.0.0")

        port_frame = ctk.CTkFrame(right, fg_color="transparent")
        port_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(port_frame, text="Port:", width=70, anchor="w").pack(side="left")
        self.port_entry = ctk.CTkEntry(port_frame, placeholder_text="6464")
        self.port_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.port_entry.insert(0, "6464")
        ctk.CTkLabel(
            port_frame,
            text="Leave as 0.0.0.0:6464 unless you changed Bedrock's WebSocket port.",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            justify="left", wraplength=380,
        ).pack(pady=(2, 0), anchor="w", padx=(75, 0))

        sep3 = ctk.CTkFrame(right, height=2, fg_color=("gray70", "gray30"))
        sep3.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(right, text="Image Directory", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 5),
        )
        dir_frame = ctk.CTkFrame(right, fg_color="transparent")
        dir_frame.pack(fill="x", padx=10, pady=2)
        self.dir_path_var = ctk.StringVar(value=str(Path.home() / "Desktop"))
        ctk.CTkEntry(dir_frame, textvariable=self.dir_path_var).pack(
            side="left", fill="x", expand=True,
        )
        ctk.CTkButton(dir_frame, text="Browse", width=80, command=self._browse_directory).pack(
            side="left", padx=(5, 0),
        )
        ctk.CTkLabel(
            right,
            text="Images you select are copied here. In-game, type #build filename.png.",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            justify="left", wraplength=380,
        ).pack(pady=(2, 5), anchor="w", padx=10)

        sep4 = ctk.CTkFrame(right, height=2, fg_color=("gray70", "gray30"))
        sep4.pack(fill="x", pady=10, padx=10)

        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)

        self.preview_btn = ctk.CTkButton(
            btn_frame, text="Preview Map",
            command=self._run_preview,
            height=38, font=("Segoe UI", 14, "bold"),
            state="disabled",
        )
        self.preview_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.start_btn = ctk.CTkButton(
            btn_frame, text="Start Server",
            command=self._toggle_server,
            height=38, font=("Segoe UI", 14, "bold"),
            fg_color=("green", "darkgreen"),
            hover_color=("darkgreen", "green"),
            state="disabled",
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

        sep5 = ctk.CTkFrame(right, height=2, fg_color=("gray70", "gray30"))
        sep5.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(right, text="Materials Needed", font=("Segoe UI", 14, "bold")).pack(
            pady=(0, 5),
        )

        mat_stats = ctk.CTkFrame(right, fg_color="transparent")
        mat_stats.pack(fill="x", padx=10, pady=(0, 2))
        self.total_blocks_label = ctk.CTkLabel(
            mat_stats, text="Total: 0 blocks",
            font=("Segoe UI", 13, "bold"),
        )
        self.total_blocks_label.pack(side="left")
        self.give_btn = ctk.CTkButton(
            mat_stats, text="Copy Give Commands",
            width=160, height=24, font=("Segoe UI", 11),
            command=self._copy_give_commands,
            state="disabled",
        )
        self.give_btn.pack(side="right")

        self.materials_text = ctk.CTkTextbox(
            right, height=140, font=("Consolas", 11),
        )
        self.materials_text.pack(fill="x", padx=10, pady=(0, 10))
        self.materials_text.insert("1.0", "Run Preview to see materials...")
        self.materials_text.configure(state="disabled")

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self, height=56, corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        self.status_text = ctk.CTkTextbox(
            bar, height=56, font=("Consolas", 11),
            wrap="word", fg_color="transparent",
        )
        self.status_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        self.status_text.insert("1.0", "Ready. Select an image to begin.")
        self.status_text.configure(state="disabled")

    def _hover_cancel_close(self):
        if self._hover_timer:
            self.after_cancel(self._hover_timer)
            self._hover_timer = None

    def _hover_schedule_close(self):
        if self._hover_timer:
            self.after_cancel(self._hover_timer)
        self._hover_timer = self.after(350, self._close_dropdown)

    def _reposition_dropdown(self, event=None):
        if self._active_dropdown is not None and self._active_dropdown.winfo_exists() and self._dropdown_anchor is not None:
            try:
                x = self._dropdown_anchor.winfo_rootx()
                y = self._dropdown_anchor.winfo_rooty() + self._dropdown_anchor.winfo_height()
                self._active_dropdown.geometry(f"+{x}+{y}")
            except:
                pass

    def _bind_events(self):
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Configure>", self._reposition_dropdown, "+")

    def _add_dropdown(self, parent, label, options, attr, default):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(frame, text=f"{label}:", width=100, anchor="w").pack(
            side="top", anchor="w",
        )

        values = [o[0] for o in options]
        descriptions = {o[0]: o[1] for o in options}
        var = ctk.StringVar(value=default)
        setattr(self, attr, var)

        dropdown = ctk.CTkOptionMenu(
            frame, values=values, variable=var,
            width=280, dynamic_resizing=False,
        )
        dropdown.pack(side="left")
        self._option_menus.append(dropdown)

        desc_label = ctk.CTkLabel(
            frame, text=descriptions[default],
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            justify="left", wraplength=300,
        )
        desc_label.pack(side="left", padx=(10, 0))

        dropdown.configure(command=lambda c: desc_label.configure(text=descriptions[c]))

    def _select_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            original = Image.open(path)
            if original.mode != "RGB":
                original = original.convert("RGB")
        except Exception as e:
            self._log(f"Error loading image: {e}")
            logger.error(f"Image load error: {e}")
            return

        processed = self._show_crop_dialog(original, path)
        if processed is None:
            return

        filename = os.path.basename(path)
        name_root = Path(filename).stem
        processed_path = str(Path(self.dir_path_var.get()) / f"{name_root}_mapart.png")
        processed.save(processed_path)
        self._log(f"Saved 128x128 version to image directory")

        self.selected_image_path = processed_path
        self._preview_pil = original
        self._preview_is_live = False
        self.live_preview_image = None
        w, h = original.size
        self.image_info_label.configure(text=f"{Path(filename).name} ({w}x{h}) \u2192 128x128")
        self.after(100, self._update_preview_size)

        self.blocks_data = []
        self.material_counts = {}
        self.materials_text.configure(state="normal")
        self.materials_text.delete("1.0", "end")
        self.materials_text.insert("1.0", "Run Preview to see materials...")
        self.materials_text.configure(state="disabled")
        self.total_blocks_label.configure(text="Total: 0 blocks")
        self.give_btn.configure(state="disabled")
        self.preview_btn.configure(state="normal")
        self.start_btn.configure(state="normal")
        logger.info(f"Selected image: {filename} (\u2192128x128)")
        self._log(f"Selected: {Path(filename).name}")

    def _show_crop_dialog(self, original, orig_path):
        w, h = original.size
        result_container = [None]

        def _crop_to_square(im):
            sz = min(im.width, im.height)
            l = (im.width - sz) // 2
            t = (im.height - sz) // 2
            return im.crop((l, t, l + sz, t + sz))

        def _update_dialog_preview(mode):
            nonlocal preview_label
            if mode == "crop":
                out = _crop_to_square(original).resize((128, 128), Image.Resampling.LANCZOS)
            else:
                out = original.resize((128, 128), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=out, dark_image=out, size=(128, 128))
            preview_label.configure(image=ctk_img)

        def _confirm(mode):
            if mode == "crop":
                out = _crop_to_square(original).resize((128, 128), Image.Resampling.LANCZOS)
            else:
                out = original.resize((128, 128), Image.Resampling.LANCZOS)
            result_container[0] = out
            dialog.destroy()

        dialog = ctk.CTkToplevel(self)
        dialog.title("Prepare Image for Map Art")
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.grab_set()

        top = ctk.CTkFrame(dialog, fg_color="transparent")
        top.pack(padx=15, pady=(12, 4), fill="x")
        ctk.CTkLabel(top, text="Original:", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        orig_display = original.copy()
        orig_display.thumbnail((280, 280), Image.Resampling.LANCZOS)
        orig_ctk = ctk.CTkImage(light_image=orig_display, dark_image=orig_display, size=orig_display.size)
        img_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        img_frame.pack(padx=15, pady=4)
        ctk.CTkLabel(img_frame, image=orig_ctk, text="").pack(side="left", padx=(0, 15))
        preview_label = ctk.CTkLabel(img_frame, text="", width=128, height=128,
                                      fg_color=("gray85", "gray20"), corner_radius=4)
        preview_label.pack(side="left")

        ctk.CTkLabel(top, text=f"{w}\u00d7{h}  \u2192  128\u00d7128",
                     font=("Segoe UI", 11)).pack(anchor="w")

        opt_f = ctk.CTkFrame(dialog, fg_color="transparent")
        opt_f.pack(pady=6)
        crop_mode = ctk.StringVar(value="crop")
        ctk.CTkRadioButton(opt_f, text="Crop to square (center crop)", variable=crop_mode,
                           value="crop", font=("Segoe UI", 11),
                           command=lambda: _update_dialog_preview(crop_mode.get())).pack(anchor="w", pady=1)
        ctk.CTkRadioButton(opt_f, text="Stretch to fit", variable=crop_mode,
                           value="stretch", font=("Segoe UI", 11),
                           command=lambda: _update_dialog_preview(crop_mode.get())).pack(anchor="w", pady=1)

        _update_dialog_preview("crop")

        btn_f = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_f.pack(pady=(4, 12))
        ctk.CTkButton(btn_f, text="Cancel", command=dialog.destroy,
                      font=("Segoe UI", 11)).pack(side="left", padx=4)
        ctk.CTkButton(btn_f, text="Use Image", font=("Segoe UI", 11, "bold"),
                      fg_color=self.accent_hex,
                      command=lambda: _confirm(crop_mode.get())).pack(side="left", padx=4)

        dialog.update_idletasks()
        dialog.focus_set()
        self.wait_window(dialog)
        return result_container[0]

    def _browse_directory(self):
        path = filedialog.askdirectory(title="Select Image Directory", initialdir=self.dir_path_var.get())
        if path:
            self.dir_path_var.set(path)

    def _run_preview(self):
        if not self.selected_image_path:
            return

        palette = self.palette_var.get()
        dither = self.dither_var.get()
        staircasing = self.staircasing_var.get()
        cmode = self.color_mode_var.get()

        self._log(f"Processing (color mode: {cmode})...")
        self.preview_btn.configure(state="disabled", text="Processing...")
        self.progress_bar.grid()
        self.progress_bar.start()
        self.update()

        def process():
            try:
                blocks, img_w, img_h = process_image(
                    self.selected_image_path, palette, dither, staircasing, cmode,
                )
                counts = {}
                for _, _, _, name, _, _ in blocks:
                    counts[name] = counts.get(name, 0) + 1
                sorted_counts = dict(sorted(counts.items(), key=lambda x: -x[1]))
                total = len(blocks)
                self.after(0, lambda: self._show_preview_result(
                    total, sorted_counts, blocks, img_w, img_h,
                ))
            except Exception as e:
                logger.exception("Preview failed")
                self.after(0, lambda: self._log(f"Preview failed: {e}"))
                self.after(0, lambda: self.preview_btn.configure(state="normal", text="Preview Map"))
                self.after(0, lambda: (self.progress_bar.stop(), self.progress_bar.grid_remove()))

        threading.Thread(target=process, daemon=True).start()

    def _show_preview_result(self, total, counts, blocks, img_w, img_h):
        self.blocks_data = blocks
        self.material_counts = counts
        self.image_width = img_w
        self.image_height = img_h

        self.materials_text.configure(state="normal")
        self.materials_text.delete("1.0", "end")
        self.materials_text.insert("1.0", f"Total blocks: {total} | Unique types: {len(counts)}\n")
        self.materials_text.insert("end", f"1 map (128\u00d7128)\n\n")
        for name, count in counts.items():
            self.materials_text.insert("end", f"  {name}: {count}\n")
        self.materials_text.configure(state="disabled")

        self.total_blocks_label.configure(text=f"Total: {total} blocks")
        self.give_btn.configure(state="normal" if counts else "disabled")

        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self._generate_live_preview(blocks, img_w, img_h)
        self._log(f"Preview: {total} blocks, {len(counts)} types, 1 map")
        logger.info(f"Preview done: {total} blocks, 1 tile")
        self.preview_btn.configure(state="normal", text="Preview Map")

    def _generate_live_preview(self, blocks, img_w, img_h):
        preview_img = Image.new("RGB", (img_w, img_h), (0, 0, 0))
        px = preview_img.load()
        for x, z, dy, block_name, tone, (r, g, b) in blocks:
            if 0 <= x < img_w and 0 <= z < img_h:
                px[x, z] = (r, g, b)
        self._preview_pil = preview_img
        self._preview_is_live = True
        self.after(100, self._update_preview_size)

    def _open_fullsize_view(self, event=None):
        if self._preview_pil is None:
            return
        from PIL import ImageTk
        import tkinter as tk

        win = ctk.CTkToplevel(self)
        win.title(f"Full Preview - {self.image_width}x{self.image_height}")
        win.transient(self)

        mw = self.winfo_width()
        mh = self.winfo_height()
        init_w = max(400, int(mw * 0.85))
        init_h = max(300, int(mh * 0.85))
        win.geometry(f"{init_w}x{init_h}")
        win.minsize(250, 200)

        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0, bg="gray20")
        canvas.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkButton(win, text="Close", command=win.destroy,
                      font=("Segoe UI", 11)).pack(pady=(0, 8))

        def _resize_img(event=None):
            cw = event.width if event and event.width > 1 else canvas.winfo_width()
            ch = event.height if event and event.height > 1 else canvas.winfo_height()
            if cw < 50 or ch < 50:
                return
            pil_copy = self._preview_pil.copy()
            if pil_copy.width > cw or pil_copy.height > ch:
                pil_copy.thumbnail((cw, ch), Image.Resampling.LANCZOS)
            else:
                ratio = min(cw / pil_copy.width, ch / pil_copy.height)
                new_size = (int(pil_copy.width * ratio), int(pil_copy.height * ratio))
                pil_copy = pil_copy.resize(new_size, Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(pil_copy)
            canvas.delete("all")
            canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center")
            canvas.photo = photo

        canvas.bind("<Configure>", _resize_img)
        win.after(50, _resize_img)

    def _update_preview_size(self, event=None):
        w = self.preview_label.winfo_width()
        h = self.preview_label.winfo_height()
        if w < 50 or h < 50:
            return
        pad = 16
        size = min(w, h) - pad
        if size < 50:
            return
        pil = self._preview_pil
        if pil is None:
            return
        img = pil.copy()
        if img.width > size or img.height > size:
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
        else:
            ratio = min(size / img.width, size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.NEAREST)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.preview_label.configure(image=ctk_img, text="", fg_color="transparent")
        self.preview_image_ctk = ctk_img

    def _copy_give_commands(self):
        if not self.material_counts:
            return
        lines = []
        for name, count in self.material_counts.items():
            lines.append(f"/give @s {name} {count}")
        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        logger.info(f"Copied {len(lines)} /give commands to clipboard")
        self._log(f"Copied {len(lines)} /give commands to clipboard")

    def _toggle_server(self):
        if self.server_instance and self.server_thread and self.server_thread.is_alive():
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        palette = self.palette_var.get()
        dither = self.dither_var.get()
        staircasing = self.staircasing_var.get()
        cmode = self.color_mode_var.get()
        address = self.address_entry.get() or "0.0.0.0"
        port_str = self.port_entry.get() or "6464"

        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be a number.")
            return

        dir_path = self.dir_path_var.get()
        if not os.path.isdir(dir_path):
            messagebox.showerror("Invalid Directory", "The image directory does not exist.")
            return

        self._log(f"Starting server on {address}:{port}...")
        logger.info(f"Starting server on {address}:{port}")
        self.start_btn.configure(text="Stop Server", fg_color=("red", "darkred"), hover_color=("darkred", "red"))

        def run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                builder = MapartBuilder(
                    Path(dir_path), palette, dither, staircasing,
                    give_mode=self.give_materials_mode,
                    color_mode=cmode,
                )
                self.server_instance = builder
                builder.launch(address, port)
            except Exception as e:
                logger.exception("Server error")
                self.after(0, lambda: self._log(f"Server error: {e}"))
                self.after(0, lambda: self._server_stopped())

        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        self.after(2000, lambda: self._log(f"Server live! In Bedrock: /connect {address}:{port}"))

    def _stop_server(self):
        self._log("Stopping server...")
        logger.info("Server stopping")
        if self.server_instance:
            try:
                self.server_instance.server.shutdown()
            except Exception:
                pass
        self.server_instance = None
        self._server_stopped()

    def _server_stopped(self):
        self.start_btn.configure(text="Start Server", fg_color=("green", "darkgreen"), hover_color=("darkgreen", "green"))

    def _log(self, message):
        self.status_text.configure(state="normal")
        self.status_text.insert("end", f"{message}\n")
        self.status_text.see("end")
        self.status_text.configure(state="disabled")

    def _open_help(self):
        win = ctk.CTkToplevel(self)
        win.title("How to Use - MapArt for Bedrock")
        win.geometry("620x540")
        win.transient(self)

        text = ctk.CTkTextbox(win, wrap="word", font=("Segoe UI", 12))
        text.pack(fill="both", expand=True, padx=15, pady=15)
        text.insert("1.0", (
            "HOW TO USE MAPARTCRAFT FOR BEDROCK\n"
            "====================================\n\n"
             "1. SELECT AN IMAGE\n"
             "   Click \"Select Image\" and pick a .png or .jpg.\n\n"
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
             "   Click \"Preview Map\" to see block counts.\n"
             "   The preview updates to show the block-colored result.\n"
             "   Use \"Copy Give Commands\" for /give commands.\n\n"
            "5. START THE SERVER\n"
            "   Click \"Start Server\". Status bar shows \"Server live!\".\n\n"
            "6. CONNECT IN MINECRAFT\n"
            "   Open your world. Press / to open chat.\n"
            "   Type:  /connect localhost:6464\n\n"
              "7. BUILD THE ART\n"
             "   In chat, type:  #build your_image_name.png\n"
             "   Default origin is (0, -1, 0). Add --x= --z= --y= for coords:\n"
             "   #build image.png --x=100 --z=200 --y=64\n\n"
            "8. STOP THE SERVER\n"
            "   Click \"Stop Server\" when done.\n\n"
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
            "   Enable Settings > Give Materials in the menu bar for auto-/give.\n"
            "   Or use \"Copy Give Commands\" to get the commands.\n"
            "   The //setblock commands work in any gamemode.\n\n"
            "---\n\n"
             "TIPS\n"
             "  - Build high up (y=64+) or over ocean to avoid terrain\n"
             "  - The End dimension gives transparent map backgrounds\n"
             "  - Open a blank map first to see where it aligns\n"
             "  - Use #build image.png --x=100 --z=200 --y=64 for coords\n"
             "  - File > Save/Load Preset to save/load your config"
        ))
        text.configure(state="disabled")

    def _on_close(self):
        if self.server_instance:
            try:
                self.server_instance.server.shutdown()
            except Exception:
                pass
        self._save_config()
        logger.info("Application closed")
        self.destroy()


def main():
    app = MapartGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

import asyncio
import json
import logging
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from . import constants
from .builder import MapartBuilder
from .dialogs.color_picker import open_color_picker
from .dialogs.crop_dialog import open_crop_dialog
from .dialogs.full_preview import open_full_preview
from .dialogs.help_dialog import open_help
from .panels.menu_bar import MenuBar
from .panels.preview_panel import PreviewPanel
from .panels.settings_panel import SettingsPanel
from .panels.status_bar import StatusBar
from .processor import process_image
from .theme import DEFAULT_THEME

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme(DEFAULT_THEME)

logging.basicConfig(
    filename=str(constants.LOG_DIR / "mapart.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mapart")


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
        self.bg_hex = constants.DEFAULT_BG_HEX
        self.accent_hex = constants.DEFAULT_ACCENT_HEX
        self.give_materials_mode = False
        self.give_materials_var = tk.BooleanVar(value=False)
        self.color_mode = "rgb"
        self.palette_var = ctk.StringVar(value="all")
        self.dither_var = ctk.StringVar(value="none")
        self.staircasing_var = ctk.StringVar(value="off")
        self.color_mode_var = ctk.StringVar(value="rgb")
        self.dimension_var = ctk.StringVar(value="overworld")

        # Panels
        self.menu_bar = MenuBar(self)
        self.preview_panel = PreviewPanel(self)
        self.settings_panel = SettingsPanel(self)
        self.status_bar = StatusBar(self)

        logger.info("Application started")
        self._build_ui()
        self._load_config()

    def _build_ui(self):
        self.menu_bar.build(self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        main = ctk.CTkFrame(self)
        main.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        main.grid_columnconfigure(0, weight=0, minsize=300)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self.preview_panel.build(main)
        self.settings_panel.build(main)
        self.status_bar.build(self)
        self._bind_events()

    def _log(self, message):
        self.status_bar.log(message)

    def _load_config(self):
        try:
            if constants.CONFIG_PATH.exists():
                with open(constants.CONFIG_PATH) as f:
                    cfg = json.load(f)
                saved_version = cfg.get("config_version", 1)
                if "image_directory" in cfg:
                    self.settings_panel.dir_path_var.set(cfg["image_directory"])
                self.bg_hex = cfg.get("bg_hex", constants.DEFAULT_BG_HEX)
                self.accent_hex = cfg.get("accent_hex", constants.DEFAULT_ACCENT_HEX)
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
                "config_version": constants.CONFIG_VERSION,
                "image_directory": self.settings_panel.dir_path_var.get(),
                "bg_hex": self.bg_hex,
                "accent_hex": self.accent_hex,
                "palette": self.palette_var.get(),
                "dither": self.dither_var.get(),
                "staircasing": self.staircasing_var.get(),
                "color_mode": self.color_mode_var.get(),
                "dimension": self.dimension_var.get(),
                "give_materials": self.give_materials_var.get(),
            }
            constants.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(constants.CONFIG_PATH, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save config: {e}")

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

        processed = open_crop_dialog(self, original)
        if processed is None:
            return

        filename = os.path.basename(path)
        name_root = Path(filename).stem
        processed_path = str(Path(self.settings_panel.dir_path_var.get()) / f"{name_root}_mapart.png")
        processed.save(processed_path)
        self._log("Saved 128x128 version to image directory")

        self.selected_image_path = processed_path
        self._preview_pil = original
        self._preview_is_live = False
        self.live_preview_image = None
        w, h = original.size
        self.preview_panel.update_image_info(f"{Path(filename).name} ({w}x{h}) \u2192 128x128")
        self.after(100, self.preview_panel._update_preview_size)

        self.blocks_data = []
        self.material_counts = {}
        self.settings_panel.materials_text.configure(state="normal")
        self.settings_panel.materials_text.delete("1.0", "end")
        self.settings_panel.materials_text.insert("1.0", "Run Preview to see materials...")
        self.settings_panel.materials_text.configure(state="disabled")
        self.settings_panel.total_blocks_label.configure(text="Total: 0 blocks")
        self.settings_panel.give_btn.configure(state="disabled")
        self.settings_panel.preview_btn.configure(state="normal")
        self.settings_panel.start_btn.configure(state="normal")
        logger.info(f"Selected image: {filename} (\u2192128x128)")
        self._log(f"Selected: {Path(filename).name}")

    def _browse_directory(self):
        path = filedialog.askdirectory(
            title="Select Image Directory",
            initialdir=self.settings_panel.dir_path_var.get())
        if path:
            self.settings_panel.dir_path_var.set(path)

    def _run_preview(self):
        if not self.selected_image_path:
            return

        palette = self.palette_var.get()
        dither = self.dither_var.get()
        staircasing = self.staircasing_var.get()
        cmode = self.color_mode_var.get()

        self._log(f"Processing (color mode: {cmode})...")
        self.settings_panel.preview_btn.configure(state="disabled", text="Processing...")
        self.preview_panel.show_progress()
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
            except Exception:
                logger.exception("Preview failed")
                self.after(0, lambda: self._log("Preview failed"))
                self.after(0, lambda: self.settings_panel.preview_btn.configure(
                    state="normal", text="Preview Map"))
                self.after(0, lambda: self.preview_panel.hide_progress())

        threading.Thread(target=process, daemon=True).start()

    def _show_preview_result(self, total, counts, blocks, img_w, img_h):
        self.blocks_data = blocks
        self.material_counts = counts
        self.image_width = img_w
        self.image_height = img_h

        mt = self.settings_panel.materials_text
        mt.configure(state="normal")
        mt.delete("1.0", "end")
        mt.insert("1.0", f"Total blocks: {total} | Unique types: {len(counts)}\n")
        mt.insert("end", "1 map (128\u00d7128)\n\n")
        for name, count in counts.items():
            mt.insert("end", f"  {name}: {count}\n")
        mt.configure(state="disabled")

        self.settings_panel.total_blocks_label.configure(text=f"Total: {total} blocks")
        self.settings_panel.give_btn.configure(state="normal" if counts else "disabled")

        self.preview_panel.hide_progress()
        self._generate_live_preview(blocks, img_w, img_h)
        self._log(f"Preview: {total} blocks, {len(counts)} types, 1 map")
        logger.info(f"Preview done: {total} blocks, 1 tile")
        self.settings_panel.preview_btn.configure(state="normal", text="Preview Map")

    def _generate_live_preview(self, blocks, img_w, img_h):
        preview_img = Image.new("RGB", (img_w, img_h), (0, 0, 0))
        px = preview_img.load()
        for x, z, dy, block_name, tone, (r, g, b) in blocks:
            if 0 <= x < img_w and 0 <= z < img_h:
                px[x, z] = (r, g, b)
        self._preview_pil = preview_img
        self._preview_is_live = True
        self.after(100, self.preview_panel._update_preview_size)

    def _open_fullsize_view(self):
        if self._preview_pil is None:
            return
        open_full_preview(self, self._preview_pil, self.image_width, self.image_height)

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
        address = self.settings_panel.address_entry.get() or "0.0.0.0"
        port_str = self.settings_panel.port_entry.get() or "6464"

        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be a number.")
            return

        dir_path = self.settings_panel.dir_path_var.get()
        if not os.path.isdir(dir_path):
            messagebox.showerror("Invalid Directory", "The image directory does not exist.")
            return

        self._log(f"Starting server on {address}:{port}...")
        logger.info(f"Starting server on {address}:{port}")
        self.settings_panel.start_btn.configure(text="Stop Server")
        self.settings_panel.server_status_dot.configure(fg_color="#EF4444")

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
            except Exception:
                logger.exception("Server error")
                self.after(0, lambda: self._log("Server error"))
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
        self.settings_panel.start_btn.configure(text="Start Server")
        self.settings_panel.server_status_dot.configure(fg_color="#22C55E")

    def _toggle_give_materials(self):
        self.give_materials_mode = self.give_materials_var.get()
        self._log(f"Give Materials: {'ON' if self.give_materials_mode else 'OFF'}")
        logger.info(f"Give Materials toggled to {self.give_materials_mode}")

    def _save_preset_action(self):
        name = filedialog.asksaveasfilename(
            title="Save Preset",
            initialdir=str(constants.PRESETS_DIR),
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
        constants.PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        with open(name, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved preset: {name}")
        self._log(f"Preset saved: {Path(name).name}")

    def _load_preset_action(self):
        name = filedialog.askopenfilename(
            title="Load Preset",
            initialdir=str(constants.PRESETS_DIR),
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

    def _pick_background_color(self):
        color = open_color_picker(self, "Choose Background Color", self.bg_hex)
        if color:
            self.bg_hex = color

    def _pick_accent_color(self):
        color = open_color_picker(self, "Choose Accent Color", self.accent_hex)
        if color:
            self.accent_hex = color

    def _open_help(self):
        open_help(self)

    def _bind_events(self):
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Configure>", self.menu_bar._reposition_dropdown, "+")

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

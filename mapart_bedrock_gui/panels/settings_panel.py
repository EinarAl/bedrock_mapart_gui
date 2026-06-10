from pathlib import Path

import customtkinter as ctk

from .. import constants


class SettingsPanel:
    def __init__(self, app):
        self.app = app
        self._option_menus = []
        self.preview_btn = None
        self.start_btn = None
        self.give_btn = None
        self.materials_text = None
        self.total_blocks_label = None
        self.address_entry = None
        self.port_entry = None
        self.dir_path_var = None
        self.dim_desc_label = None
        self.frame = None

    def build(self, parent):
        self.frame = ctk.CTkScrollableFrame(parent, corner_radius=10)
        self.frame.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(self.frame, text="Settings", font=("Segoe UI", 16, "bold")).pack(
            pady=(10, 10),
        )

        self._add_dropdown("Palette", constants.PALETTE_OPTIONS, "palette_var", "all")
        self._add_dropdown("Dithering", constants.DITHER_OPTIONS, "dither_var", "none")
        self._add_dropdown("Staircasing", constants.STAIRCASING_OPTIONS, "staircasing_var", "off")

        self._add_separator()

        ctk.CTkLabel(self.frame, text="Color Matching", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 5),
        )
        cm_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        cm_frame.pack(fill="x", padx=10, pady=2)
        self.app.color_mode_var = ctk.StringVar(value="rgb")
        cm_dropdown = ctk.CTkOptionMenu(
            cm_frame, values=["rgb", "lab"],
            variable=self.app.color_mode_var, width=120,
        )
        cm_dropdown.pack(side="left")
        self._option_menus.append(cm_dropdown)
        ctk.CTkLabel(
            cm_frame,
            text="CIE Lab Delta-E vs RGB distance",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            wraplength=320, justify="left",
        ).pack(side="left", padx=(10, 0))

        self._add_separator()

        ctk.CTkLabel(self.frame, text="Dimension", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 5),
        )
        dim_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        dim_frame.pack(fill="x", padx=10, pady=2)
        dim_values = [d[0] for d in constants.DIMENSION_OPTIONS]
        dim_descs = {d[0]: d[1] for d in constants.DIMENSION_OPTIONS}
        self.app.dimension_var = ctk.StringVar(value="overworld")
        dim_dropdown = ctk.CTkOptionMenu(
            dim_frame, values=dim_values,
            variable=self.app.dimension_var, width=120,
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
            self.frame,
            text="You must be in this dimension in-game.\nEnd void = transparent map sections.",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            justify="left", wraplength=380,
        ).pack(pady=(2, 5), anchor="w", padx=10)

        self._add_separator()

        ctk.CTkLabel(self.frame, text="Server", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 5),
        )

        addr_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        addr_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(addr_frame, text="Address:", width=70, anchor="w").pack(side="left")
        self.address_entry = ctk.CTkEntry(addr_frame, placeholder_text="0.0.0.0")
        self.address_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.address_entry.insert(0, "0.0.0.0")

        port_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        port_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(port_frame, text="Port:", width=70, anchor="w").pack(side="left")
        self.port_entry = ctk.CTkEntry(port_frame, placeholder_text="6464")
        self.port_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.port_entry.insert(0, "6464")
        ctk.CTkLabel(
            port_frame,
            text="Leave as 0.0.0.0:6464 unless changed.",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            justify="left", wraplength=380,
        ).pack(pady=(2, 0), anchor="w", padx=(75, 0))

        self._add_separator()

        ctk.CTkLabel(self.frame, text="Image Directory", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 5),
        )
        dir_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        dir_frame.pack(fill="x", padx=10, pady=2)
        self.dir_path_var = ctk.StringVar(value=str(Path.home() / "Desktop"))
        ctk.CTkEntry(dir_frame, textvariable=self.dir_path_var).pack(
            side="left", fill="x", expand=True,
        )
        ctk.CTkButton(dir_frame, text="Browse", width=80, command=self.app._browse_directory).pack(
            side="left", padx=(5, 0),
        )
        ctk.CTkLabel(
            self.frame,
            text="Images are copied here. In-game: #build filename.png",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            justify="left", wraplength=380,
        ).pack(pady=(2, 5), anchor="w", padx=10)

        self._add_separator()

        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)

        self.preview_btn = ctk.CTkButton(
            btn_frame, text="Preview Map",
            command=self.app._run_preview,
            height=38, font=("Segoe UI", 14, "bold"),
            state="disabled",
        )
        self.preview_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        server_btn_wrap = ctk.CTkFrame(btn_frame, fg_color="transparent")
        server_btn_wrap.pack(side="left", fill="x", expand=True, padx=(5, 0))

        self.server_status_dot = ctk.CTkLabel(
            server_btn_wrap, text="", width=8, height=8,
            fg_color="#22C55E", corner_radius=4,
        )
        self.server_status_dot.pack(side="left", padx=(0, 6))

        self.start_btn = ctk.CTkButton(
            server_btn_wrap, text="Start Server",
            command=self.app._toggle_server,
            height=38, font=("Segoe UI", 14, "bold"),
            state="disabled",
        )
        self.start_btn.pack(side="left", fill="x", expand=True)

        self._add_separator()

        ctk.CTkLabel(self.frame, text="Materials Needed", font=("Segoe UI", 14, "bold")).pack(
            pady=(0, 5),
        )

        mat_stats = ctk.CTkFrame(self.frame, fg_color="transparent")
        mat_stats.pack(fill="x", padx=10, pady=(0, 2))
        self.total_blocks_label = ctk.CTkLabel(
            mat_stats, text="Total: 0 blocks",
            font=("Segoe UI", 13, "bold"),
        )
        self.total_blocks_label.pack(side="left")
        self.give_btn = ctk.CTkButton(
            mat_stats, text="Copy Give Commands",
            width=160, height=24, font=("Segoe UI", 11),
            command=self.app._copy_give_commands,
            state="disabled",
        )
        self.give_btn.pack(side="right")

        self.materials_text = ctk.CTkTextbox(
            self.frame, height=140, font=("Consolas", 11),
        )
        self.materials_text.pack(fill="x", padx=10, pady=(0, 10))
        self.materials_text.insert("1.0", "Run Preview to see materials...")
        self.materials_text.configure(state="disabled")

    def update_widget_colors(self):
        accent = self.app.accent_hex
        hover = self._lighten(accent, 0.2)
        dark = self._darken(accent, 0.15)
        for widget in (self.preview_btn, self.give_btn):
            try:
                widget.configure(fg_color=accent, hover_color=hover)
            except Exception:
                pass
        for om in self._option_menus:
            try:
                om.configure(fg_color=accent, button_color=dark, button_hover_color=hover)
            except Exception:
                pass

    def _add_separator(self):
        sep = ctk.CTkFrame(self.frame, height=1, fg_color=("gray60", "#2A2A30"))
        sep.pack(fill="x", pady=10, padx=10)

    def _add_dropdown(self, label, options, attr, default):
        frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(frame, text=f"{label}:", width=100, anchor="w").pack(
            side="top", anchor="w",
        )

        values = [o[0] for o in options]
        descriptions = {o[0]: o[1] for o in options}
        var = ctk.StringVar(value=default)
        setattr(self.app, attr, var)

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

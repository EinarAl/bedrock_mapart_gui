import customtkinter as ctk


class MenuBar:
    def __init__(self, app):
        self.app = app
        self._menu_file = None
        self._menu_settings = None
        self._menu_help = None
        self._active_dropdown = None
        self._dropdown_anchor = None
        self._hover_timer = None

    def build(self, parent):
        bar = ctk.CTkFrame(parent, height=30, corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)

        menu_btn_kw = {
            "height": 26, "font": ("Segoe UI", 12),
            "fg_color": "transparent", "text_color": ("gray10", "#DCE4EE"),
            "hover_color": ("gray60", self._lighten(self.app.accent_hex, 0.3)),
            "corner_radius": 4,
        }

        self._menu_file = ctk.CTkButton(bar, text="File", width=44, **menu_btn_kw)
        self._menu_file.pack(side="left", padx=(6, 1), pady=2)
        self._menu_file.bind("<Enter>", lambda e: self._hover_enter("file"))
        self._menu_file.bind("<Leave>", lambda e: self._hover_leave())

        self._menu_settings = ctk.CTkButton(bar, text="Theme", width=66, **menu_btn_kw)
        self._menu_settings.pack(side="left", padx=1, pady=2)
        self._menu_settings.bind("<Enter>", lambda e: self._hover_enter("settings"))
        self._menu_settings.bind("<Leave>", lambda e: self._hover_leave())

        self._menu_help = ctk.CTkButton(bar, text="Help", width=44, **menu_btn_kw)
        self._menu_help.pack(side="left", padx=1, pady=2)
        self._menu_help.bind("<Enter>", lambda e: self._hover_enter("help"))
        self._menu_help.bind("<Leave>", lambda e: self._hover_leave())

        ctk.CTkLabel(bar, text="v0.3", text_color=("gray50", "gray60"),
                     font=("Segoe UI", 10)).pack(side="right", padx=10)
        return bar

    def update_hover_colors(self):
        hover = self._lighten(self.app.accent_hex, 0.3)
        for btn in (self._menu_file, self._menu_settings, self._menu_help):
            btn.configure(hover_color=hover)

    def _hover_enter(self, name):
        if self._hover_timer:
            self.app.after_cancel(self._hover_timer)
        self._hover_timer = self.app.after(120, lambda: self._show_named_dropdown(name))

    def _hover_leave(self):
        if self._hover_timer:
            self.app.after_cancel(self._hover_timer)
        self._hover_timer = self.app.after(350, self._close_dropdown)

    def _hover_cancel_close(self):
        if self._hover_timer:
            self.app.after_cancel(self._hover_timer)
            self._hover_timer = None

    def _hover_schedule_close(self):
        if self._hover_timer:
            self.app.after_cancel(self._hover_timer)
        self._hover_timer = self.app.after(350, self._close_dropdown)

    def _close_dropdown(self, event=None):
        if self._active_dropdown is not None and self._active_dropdown.winfo_exists():
            try:
                self._active_dropdown.destroy()
            except Exception:
                pass
            self._active_dropdown = None
            self._dropdown_anchor = None

    def _reposition_dropdown(self, event=None):
        dd = self._active_dropdown
        if dd is not None and dd.winfo_exists() and self._dropdown_anchor is not None:
            try:
                x = self._dropdown_anchor.winfo_rootx()
                y = self._dropdown_anchor.winfo_rooty() + self._dropdown_anchor.winfo_height()
                dd.geometry(f"+{x}+{y}")
            except Exception:
                pass

    def _build_dropdown(self, anchor_btn, populate_fn):
        self._close_dropdown()
        self._dropdown_anchor = anchor_btn
        x = anchor_btn.winfo_rootx()
        y = anchor_btn.winfo_rooty() + anchor_btn.winfo_height()
        win = ctk.CTkToplevel(self.app)
        win.overrideredirect(True)
        win.transient(self.app)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.bind("<Escape>", lambda e: self._close_dropdown())
        frame = ctk.CTkFrame(win, corner_radius=8, border_width=1,
                             border_color=("gray70", self._lighten(self.app.bg_hex, 0.25)))
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

    def _show_named_dropdown(self, name):
        if name == "file":
            self._show_file_dropdown()
        elif name == "settings":
            self._show_settings_dropdown()
        elif name == "help":
            self._show_help_dropdown()

    def _show_file_dropdown(self):
        btn_style = {"fg_color": "transparent", "text_color": ("gray10", "#DCE4EE"),
                     "hover_color": self._lighten(self.app.accent_hex, 0.3)}

        def _save(win):
            win.destroy()
            self.app.after(50, self.app._save_preset_action)

        def _load(win):
            win.destroy()
            self.app.after(50, self.app._load_preset_action)

        def _exit(win):
            win.destroy()
            self.app.after(50, self.app._on_close)

        def populate(frame, win):
            ctk.CTkButton(frame, text="Save Preset...", height=28, anchor="w",
                          command=lambda: _save(win),
                          font=("Segoe UI", 12), **btn_style).pack(fill="x", padx=6, pady=3)
            ctk.CTkButton(frame, text="Load Preset...", height=28, anchor="w",
                          command=lambda: _load(win),
                          font=("Segoe UI", 12), **btn_style).pack(fill="x", padx=6, pady=3)
            sep = ctk.CTkFrame(frame, height=1, fg_color=("gray70", self._lighten(self.app.bg_hex, 0.25)))
            sep.pack(fill="x", padx=6, pady=3)
            ctk.CTkButton(frame, text="Exit", height=28, anchor="w",
                          command=lambda: _exit(win),
                          font=("Segoe UI", 12), **btn_style).pack(fill="x", padx=6, pady=3)
        self._build_dropdown(self._menu_file, populate)

    def _show_settings_dropdown(self):
        def _open_bg_picker(win):
            win.destroy()
            self.app.after(50, self.app._pick_background_color)

        def _open_accent_picker(win):
            win.destroy()
            self.app.after(50, self.app._pick_accent_color)

        def _toggle_give(win):
            win.destroy()
            self.app._toggle_give_materials()

        def populate(frame, win):
            ctk.CTkLabel(frame, text="Background", font=("Segoe UI", 11, "bold")).pack(pady=(6, 2), padx=8, anchor="w")
            bg_f = ctk.CTkFrame(frame, fg_color="transparent")
            bg_f.pack(fill="x", padx=8, pady=(0, 4))
            ctk.CTkLabel(bg_f, text="     ", fg_color=self.app.bg_hex,
                         corner_radius=4, width=28).pack(side="left", padx=(0, 4))
            ctk.CTkButton(bg_f, text=self.app.bg_hex, height=24, anchor="w",
                          command=lambda: _open_bg_picker(win),
                          font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True)
            sep = ctk.CTkFrame(frame, height=1, fg_color=("gray70", self._lighten(self.app.bg_hex, 0.25)))
            sep.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(frame, text="Accent", font=("Segoe UI", 11, "bold")).pack(pady=(2, 2), padx=8, anchor="w")
            ac_f = ctk.CTkFrame(frame, fg_color="transparent")
            ac_f.pack(fill="x", padx=8, pady=(0, 4))
            ctk.CTkLabel(ac_f, text="     ", fg_color=self.app.accent_hex,
                         corner_radius=4, width=28).pack(side="left", padx=(0, 4))
            ctk.CTkButton(ac_f, text=self.app.accent_hex, height=24, anchor="w",
                          command=lambda: _open_accent_picker(win),
                          font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True)
            sep2 = ctk.CTkFrame(frame, height=1, fg_color=("gray70", self._lighten(self.app.bg_hex, 0.25)))
            sep2.pack(fill="x", padx=8, pady=4)
            give_text = f"Give Materials: {'ON' if self.app.give_materials_mode else 'OFF'}"
            ctk.CTkButton(frame, text=give_text, height=28,
                          command=lambda: _toggle_give(win),
                          font=("Segoe UI", 12)).pack(fill="x", padx=8, pady=4)
        self._build_dropdown(self._menu_settings, populate)

    def _show_help_dropdown(self):
        def _show_help(win):
            win.destroy()
            self.app.after(50, self.app._open_help)

        def populate(frame, win):
            ctk.CTkButton(frame, text="How to Use", height=28, anchor="w",
                          fg_color="transparent", text_color=("gray10", "#DCE4EE"),
                          hover_color=self._lighten(self.app.accent_hex, 0.3),
                          command=lambda: _show_help(win),
                          font=("Segoe UI", 12)).pack(fill="x", padx=6, pady=3)
        self._build_dropdown(self._menu_help, populate)

    @staticmethod
    def _lighten(hex_color, factor=0.2):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

import tkinter.colorchooser as tkc

import customtkinter as ctk

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


def open_color_picker(parent, title, current_color):
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
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
                  fg_color="#152642", hover_color="#1A3858",
                  font=("Segoe UI", 11, "bold")).pack(side="left", padx=4)
    ctk.CTkButton(btn_f, text="Cancel", command=dialog.destroy,
                  font=("Segoe UI", 11)).pack(side="left", padx=4)

    update_swatch()
    dialog.grab_set()
    entry.focus_set()
    parent.wait_window(dialog)
    return result[0]

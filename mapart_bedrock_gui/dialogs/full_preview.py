import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk


def open_full_preview(parent, preview_pil, image_width, image_height):
    win = ctk.CTkToplevel(parent)
    win.title(f"Full Preview - {image_width}x{image_height}")
    win.transient(parent)

    mw = parent.winfo_width()
    mh = parent.winfo_height()
    init_w = max(400, int(mw * 0.85))
    init_h = max(300, int(mh * 0.85))
    win.geometry(f"{init_w}x{init_h}")
    win.minsize(250, 200)

    container = ctk.CTkFrame(win, fg_color="transparent")
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container, highlightthickness=0, bg="#1A1A1E")
    canvas.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkButton(win, text="Close", command=win.destroy,
                  font=("Segoe UI", 11)).pack(pady=(0, 8))

    def _resize_img(event=None):
        cw = event.width if event and event.width > 1 else canvas.winfo_width()
        ch = event.height if event and event.height > 1 else canvas.winfo_height()
        if cw < 50 or ch < 50:
            return
        pil_copy = preview_pil.copy()
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
    return win

import customtkinter as ctk
from PIL import Image


def open_crop_dialog(parent, original):
    w, h = original.size
    result_container = [None]

    def _crop_to_square(im):
        sz = min(im.width, im.height)
        left = (im.width - sz) // 2
        t = (im.height - sz) // 2
        return im.crop((left, t, left + sz, t + sz))

    def _update_dialog_preview(mode):
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

    dialog = ctk.CTkToplevel(parent)
    dialog.title("Prepare Image for Map Art")
    dialog.transient(parent)
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
                  fg_color="#152642",
                  command=lambda: _confirm(crop_mode.get())).pack(side="left", padx=4)

    dialog.update_idletasks()
    dialog.focus_set()
    parent.wait_window(dialog)
    return result_container[0]

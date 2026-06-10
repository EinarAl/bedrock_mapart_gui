import customtkinter as ctk
from PIL import Image


class PreviewPanel:
    def __init__(self, app):
        self.app = app
        self.preview_label = None
        self.progress_bar = None
        self.select_btn = None
        self.image_info_label = None
        self.frame = None

    def build(self, parent):
        self.frame = ctk.CTkFrame(parent, corner_radius=10)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.frame, text="Preview", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, pady=(10, 0),
        )

        self.preview_label = ctk.CTkLabel(
            self.frame,
            text="No image selected\n\nSelect an image to see\nthe map art preview",
            fg_color=("#E4E4E7", "#24242A"),
            text_color=("#52525B", "#71717A"),
            corner_radius=8,
        )
        self.preview_label.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        self.preview_label.bind("<Configure>", self._update_preview_size)
        self.preview_label.bind("<Button-1>", lambda e: self.app._open_fullsize_view())

        self.progress_bar = ctk.CTkProgressBar(self.frame, mode="indeterminate", height=6, corner_radius=3)
        self.progress_bar.grid(row=2, column=0, padx=20, pady=0, sticky="ew")
        self.progress_bar.grid_remove()

        self.select_btn = ctk.CTkButton(
            self.frame, text="Select Image",
            command=self.app._select_image,
            height=36, font=("Segoe UI", 13),
        )
        self.select_btn.grid(row=3, column=0, pady=(5, 5), padx=10, sticky="ew")

        self.image_info_label = ctk.CTkLabel(
            self.frame, text="", font=("Segoe UI", 11),
        )
        self.image_info_label.grid(row=4, column=0, pady=(0, 10), padx=10)

    def _update_preview_size(self, event=None):
        if self.app._preview_pil is None:
            return
        w = self.preview_label.winfo_width()
        h = self.preview_label.winfo_height()
        if w < 50 or h < 50:
            return
        pad = 16
        size = min(w, h) - pad
        if size < 50:
            return
        img = self.app._preview_pil.copy()
        if img.width > size or img.height > size:
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
        else:
            ratio = min(size / img.width, size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.NEAREST)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.preview_label.configure(image=ctk_img, text="", fg_color="transparent")
        self.app.preview_image_ctk = ctk_img

    def show_progress(self):
        self.progress_bar.grid()
        self.progress_bar.start()

    def hide_progress(self):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

    def update_image_info(self, text):
        self.image_info_label.configure(text=text)

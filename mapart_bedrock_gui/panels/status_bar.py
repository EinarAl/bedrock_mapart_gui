import customtkinter as ctk


class StatusBar:
    def __init__(self, app):
        self.app = app

    def build(self, parent):
        bar = ctk.CTkFrame(parent, height=56, corner_radius=0)
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
        return bar

    def log(self, message):
        self.status_text.configure(state="normal")
        self.status_text.insert("end", f"{message}\n")
        self.status_text.see("end")
        self.status_text.configure(state="disabled")

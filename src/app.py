"""Modern Tk desktop interface for P@ssw0rd."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from preferences import PreferencesService, UiPreferences
from vault import ValidationError, VaultEntry, VaultError, VaultService

PALETTES = {
    "dark": {
        "bg": "#0b1020", "surface": "#141b2f", "surface_alt": "#1b2540", "input": "#0e1528",
        "text": "#f3f7ff", "muted": "#9cabc5", "accent": "#38bdf8", "accent_active": "#0ea5e9",
        "border": "#2a3858", "danger": "#fb7185", "danger_bg": "#3a1b32", "selected": "#173e5b",
    },
    "light": {
        "bg": "#edf3fb", "surface": "#ffffff", "surface_alt": "#f6f9fd", "input": "#ffffff",
        "text": "#162033", "muted": "#63708a", "accent": "#0969da", "accent_active": "#0758b9",
        "border": "#d7e0ed", "danger": "#c12645", "danger_bg": "#fff0f3", "selected": "#dcedff",
    },
}


class PasswordApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.vault = VaultService()
        self.preferences_service = PreferencesService()
        self.preferences = self.preferences_service.load()
        self.colors = PALETTES[self.preferences.theme]
        self.current_entry_id: str | None = None
        self.entries: dict[str, VaultEntry] = {}
        self._background_photo: ImageTk.PhotoImage | None = None
        self._background_source: Image.Image | None = None
        self.title("P@ssw0rd")
        self.geometry("1180x740")
        self.minsize(960, 620)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._configure_style()
        self.show_gate()

    def _configure_style(self) -> None:
        c = self.colors
        self.configure(bg=c["bg"])
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=c["bg"])
        style.configure("Surface.TFrame", background=c["surface"])
        style.configure("Alt.TFrame", background=c["surface_alt"])
        style.configure("Title.TLabel", background=c["bg"], foreground=c["text"], font=("Segoe UI", 25, "bold"))
        style.configure("Eyebrow.TLabel", background=c["surface"], foreground=c["accent"], font=("Segoe UI", 9, "bold"))
        style.configure("Heading.TLabel", background=c["surface"], foreground=c["text"], font=("Segoe UI", 17, "bold"))
        style.configure("Body.TLabel", background=c["surface"], foreground=c["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=c["surface"], foreground=c["muted"], font=("Segoe UI", 10))
        style.configure("OnBg.TLabel", background=c["bg"], foreground=c["muted"], font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground=c["input"], foreground=c["text"], bordercolor=c["border"], insertcolor=c["text"], padding=(10, 8))
        style.map("TEntry", bordercolor=[("focus", c["accent"])])
        style.configure("TCombobox", fieldbackground=c["input"], background=c["input"], foreground=c["text"], arrowcolor=c["muted"], padding=(8, 7))
        style.map("TCombobox", fieldbackground=[("readonly", c["input"])], foreground=[("readonly", c["text"])])
        style.configure("TButton", background=c["surface_alt"], foreground=c["text"], bordercolor=c["border"], font=("Segoe UI", 10, "bold"), padding=(13, 8), relief="flat")
        style.map("TButton", background=[("active", c["border"])])
        style.configure("Primary.TButton", background=c["accent"], foreground="#ffffff", bordercolor=c["accent"], padding=(14, 9))
        style.map("Primary.TButton", background=[("active", c["accent_active"])])
        style.configure("Danger.TButton", background=c["danger_bg"], foreground=c["danger"], bordercolor=c["danger_bg"])
        style.configure("Treeview", background=c["surface"], fieldbackground=c["surface"], foreground=c["text"], bordercolor=c["border"], rowheight=42, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=c["surface_alt"], foreground=c["muted"], font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", c["selected"])], foreground=[("selected", c["text"])])

    def clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._background_photo = None
        self._background_source = None

    def _page(self) -> tk.Canvas:
        canvas = tk.Canvas(self, bg=self.colors["bg"], highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", self._draw_background)
        return canvas

    def _draw_background(self, event: object = None) -> None:
        canvas = getattr(self, "page_canvas", None)
        if not canvas:
            return
        width, height = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
        canvas.delete("background")
        path = Path(self.preferences.background_image) if self.preferences.background_image else None
        if path and path.exists():
            try:
                if self._background_source is None:
                    self._background_source = Image.open(path).convert("RGB")
                image = self._background_source.copy()
                scale = max(width / image.width, height / image.height)
                image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
                left, top = (image.width - width) // 2, (image.height - height) // 2
                image = image.crop((left, top, left + width, top + height))
                overlay = Image.new("RGBA", image.size, self._hex_rgba(self.colors["bg"], 190))
                self._background_photo = ImageTk.PhotoImage(Image.alpha_composite(image.convert("RGBA"), overlay))
                canvas.create_image(0, 0, image=self._background_photo, anchor="nw", tags="background")
                canvas.tag_lower("background")
                return
            except Exception:
                self._background_source = None
        canvas.create_rectangle(0, 0, width, height, fill=self.colors["bg"], outline="", tags="background")
        # Subtle structured light, deliberately not a gradient or decorative orb.
        for y in range(0, height, 52):
            canvas.create_line(0, y, width, y, fill=self.colors["surface_alt"], width=1, tags="background")
        canvas.tag_lower("background")

    @staticmethod
    def _hex_rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4)) + (alpha,)

    def _place_panel(self, parent: tk.Canvas, panel: ttk.Frame, **kwargs: object) -> None:
        # Canvas coordinates are positional arguments; passing them as kwargs raises IndexError in Tk.
        x = int(kwargs.pop("x"))
        y = int(kwargs.pop("y"))
        self._content_item = parent.create_window(x, y, **kwargs, window=panel, anchor="center", tags="content")
        self._content_width = int(kwargs.get("width", 0))
        self._content_height = int(kwargs.get("height", 0))
        parent.bind("<Configure>", self._position_content, add="+")

    def _position_content(self, event: tk.Event) -> None:
        if not hasattr(self, "_content_item"):
            return
        width = max(event.width - 56, 900) if self._content_width > 500 else min(self._content_width, event.width - 32)
        height = max(event.height - 48, 560) if self._content_height else 0
        options: dict[str, int] = {"width": width}
        if self._content_height:
            options["height"] = height
        event.widget.coords(self._content_item, event.width // 2, event.height // 2)
        event.widget.itemconfigure(self._content_item, **options)

    def show_gate(self) -> None:
        self.clear()
        self.current_entry_id = None
        self.page_canvas = self._page()
        initial = not self.vault.is_initialized
        panel = ttk.Frame(self.page_canvas, style="Surface.TFrame", padding=36)
        self._place_panel(self.page_canvas, panel, x=max(self.winfo_width() // 2, 480), y=max(self.winfo_height() // 2 - 25, 300), width=450)
        ttk.Label(panel, text="P@ssw0rd", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(panel, text="Create your vault" if initial else "Welcome back", style="Heading.TLabel", font=("Segoe UI", 25, "bold")).pack(anchor="w", pady=(10, 5))
        copy = "Set the password that encrypts this vault on this device." if initial else "Unlock your local encrypted vault to continue."
        ttk.Label(panel, text=copy, style="Muted.TLabel", wraplength=355).pack(anchor="w", pady=(0, 26))
        password = tk.StringVar()
        confirm = tk.StringVar()
        self._label_entry(panel, "MASTER PASSWORD", password, secret=True)
        if initial:
            self._label_entry(panel, "CONFIRM PASSWORD", confirm, secret=True)
        status = ttk.Label(panel, text="", style="Body.TLabel", foreground=self.colors["danger"], wraplength=355)
        status.pack(anchor="w", pady=(6, 10))

        def submit() -> None:
            try:
                if initial:
                    if password.get() != confirm.get():
                        raise ValidationError("The two passwords do not match.")
                    self.vault.initialize(password.get())
                else:
                    self.vault.unlock(password.get())
                self.show_vault()
            except VaultError as exc:
                status.configure(text=str(exc))

        ttk.Button(panel, text=("Create encrypted vault" if initial else "Unlock vault") + "  →", style="Primary.TButton", command=submit).pack(fill="x", pady=(5, 0))
        ttk.Label(panel, text="Local only · AES-256-GCM encrypted", style="Muted.TLabel", font=("Segoe UI", 9)).pack(anchor="w", pady=(17, 0))
        self.bind("<Return>", lambda _: submit())

    def _label_entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar, secret: bool = False) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Eyebrow.TLabel").pack(anchor="w", pady=(10, 4))
        entry = ttk.Entry(parent, textvariable=variable, show="●" if secret else "")
        entry.pack(fill="x")
        entry.focus_set()
        return entry

    def show_vault(self) -> None:
        self.clear()
        self.page_canvas = self._page()
        shell = ttk.Frame(self.page_canvas, style="TFrame", padding=(28, 24))
        self._place_panel(self.page_canvas, shell, x=max(self.winfo_width() // 2, 480), y=max(self.winfo_height() // 2, 310), width=max(self.winfo_width() - 56, 900), height=max(self.winfo_height() - 48, 560))
        header = ttk.Frame(shell, style="TFrame")
        header.pack(fill="x", pady=(0, 20))
        brand = ttk.Frame(header, style="TFrame")
        brand.pack(side="left")
        ttk.Label(brand, text="P@ssw0rd", style="Title.TLabel").pack(side="left")
        ttk.Label(brand, text="LOCAL VAULT", style="OnBg.TLabel", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(12, 0), pady=(10, 0))
        ttk.Button(header, text=("☼" if self.preferences.theme == "dark" else "◐") + " Theme", command=self.toggle_theme).pack(side="right")
        ttk.Button(header, text="⚙ Settings", command=self.show_settings).pack(side="right", padx=(0, 8))
        ttk.Button(header, text="⌑ Lock", command=self.lock).pack(side="right", padx=(0, 8))
        body = ttk.Frame(shell, style="TFrame")
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Surface.TFrame", padding=16)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(body, style="Surface.TFrame", padding=20, width=350)
        right.pack(side="right", fill="both", padx=(16, 0))
        right.pack_propagate(False)
        controls = ttk.Frame(left, style="Surface.TFrame")
        controls.pack(fill="x", pady=(0, 14))
        ttk.Label(controls, text="YOUR ACCOUNTS", style="Eyebrow.TLabel").pack(side="left", padx=(0, 13))
        self.search_var = tk.StringVar()
        search = ttk.Entry(controls, textvariable=self.search_var, width=30)
        search.pack(side="left", fill="x", expand=True)
        self.category_var = tk.StringVar(value="All categories")
        self.category_box = ttk.Combobox(controls, state="readonly", textvariable=self.category_var, width=16)
        self.category_box.pack(side="left", padx=8)
        ttk.Button(controls, text="＋ New", style="Primary.TButton", command=lambda: self.open_editor()).pack(side="right")
        self.tree = ttk.Treeview(left, columns=("title", "identity", "category"), show="headings", selectmode="browse")
        for key, title, width in (("title", "ACCOUNT", 220), ("identity", "IDENTITY", 300), ("category", "CATEGORY", 130)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=100)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.select_entry)
        self.search_var.trace_add("write", lambda *_: self.refresh_entries())
        self.category_box.bind("<<ComboboxSelected>>", lambda _: self.refresh_entries())
        self.detail = ttk.Frame(right, style="Surface.TFrame")
        self.detail.pack(fill="both", expand=True)
        self.refresh_entries()
        self.show_empty_detail()

    def refresh_entries(self) -> None:
        if not self.vault.is_unlocked:
            return
        selected = self.current_entry_id
        self.entries = {item.id: item for item in self.vault.list_entries(self.search_var.get())}
        values = ["All categories", *self.vault.categories()]
        self.category_box["values"] = values
        if self.category_var.get() not in values:
            self.category_var.set("All categories")
        rows = [item for item in self.entries.values() if self.category_var.get() == "All categories" or item.category == self.category_var.get()]
        self.tree.delete(*self.tree.get_children())
        for item in rows:
            identity = item.username or item.email or item.phone or "No identity set"
            self.tree.insert("", "end", iid=item.id, values=(item.title, identity, item.category or "Uncategorized"))
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)

    def select_entry(self, _: object = None) -> None:
        selected = self.tree.selection()
        if selected:
            self.current_entry_id = selected[0]
            self.show_entry_detail(self.entries[self.current_entry_id])

    def show_empty_detail(self) -> None:
        self._clear_detail()
        ttk.Label(self.detail, text="DETAILS", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(self.detail, text="Select an account", style="Heading.TLabel").pack(anchor="w", pady=(13, 5))
        ttk.Label(self.detail, text="Its identity and secret fields will appear here.", style="Muted.TLabel", wraplength=270).pack(anchor="w")

    def _clear_detail(self) -> None:
        for child in self.detail.winfo_children():
            child.destroy()

    def show_entry_detail(self, entry: VaultEntry) -> None:
        self._clear_detail()
        ttk.Label(self.detail, text="DETAILS", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(self.detail, text=entry.title, style="Heading.TLabel", wraplength=290).pack(anchor="w", pady=(12, 3))
        metadata = " · ".join(filter(None, [entry.category, entry.tags])) or "Uncategorized"
        ttk.Label(self.detail, text=metadata, style="Muted.TLabel", wraplength=285).pack(anchor="w", pady=(0, 14))
        for label, value in (("Username", entry.username), ("Phone", entry.phone), ("Email", entry.email), ("Website", entry.url), ("Password", entry.password)):
            if value:
                row = ttk.Frame(self.detail, style="Alt.TFrame", padding=(10, 7))
                row.pack(fill="x", pady=3)
                ttk.Label(row, text=label.upper(), style="Eyebrow.TLabel", background=self.colors["surface_alt"]).pack(anchor="w")
                inner = ttk.Frame(row, style="Alt.TFrame")
                inner.pack(fill="x", pady=(3, 0))
                shown = "●" * min(max(len(value), 9), 20) if label == "Password" else value
                ttk.Label(inner, text=shown, style="Body.TLabel", background=self.colors["surface_alt"], wraplength=195).pack(side="left", fill="x", expand=True)
                ttk.Button(inner, text="⧉", command=lambda v=value: self.copy(v)).pack(side="right")
        if entry.notes:
            ttk.Label(self.detail, text="NOTES", style="Eyebrow.TLabel").pack(anchor="w", pady=(13, 4))
            ttk.Label(self.detail, text=entry.notes, style="Body.TLabel", wraplength=285).pack(anchor="w")
        actions = ttk.Frame(self.detail, style="Surface.TFrame")
        actions.pack(side="bottom", fill="x", pady=(14, 0))
        ttk.Button(actions, text="Edit", command=lambda: self.open_editor(entry)).pack(side="left")
        ttk.Button(actions, text="Delete", style="Danger.TButton", command=lambda: self.delete_selected(entry)).pack(side="right")

    def copy(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()
        self.title("P@ssw0rd  ·  Copied to clipboard")
        self.after(1400, lambda: self.title("P@ssw0rd"))

    def open_editor(self, entry: VaultEntry | None = None) -> None:
        editor = tk.Toplevel(self)
        editor.title("New account" if entry is None else "Edit account")
        editor.configure(bg=self.colors["bg"])
        editor.transient(self)
        editor.grab_set()
        editor.resizable(False, False)
        panel = ttk.Frame(editor, style="Surface.TFrame", padding=26)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="NEW ACCOUNT" if entry is None else "EDIT ACCOUNT", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(panel, text="Account details", style="Heading.TLabel").pack(anchor="w", pady=(8, 8))
        values = entry or VaultEntry(id="", title="")
        fields = [("NAME *", "title"), ("USERNAME", "username"), ("PHONE", "phone"), ("EMAIL", "email"), ("WEBSITE", "url"), ("PASSWORD", "password"), ("CATEGORY", "category"), ("TAGS", "tags")]
        variables: dict[str, tk.StringVar] = {}
        for label, key in fields:
            variable = tk.StringVar(value=getattr(values, key))
            variables[key] = variable
            self._label_entry(panel, label, variable, key == "password")
        ttk.Label(panel, text="NOTES", style="Eyebrow.TLabel").pack(anchor="w", pady=(10, 4))
        notes = tk.Text(panel, height=4, width=48, bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["text"], relief="flat", padx=10, pady=8, font=("Segoe UI", 10))
        notes.insert("1.0", values.notes)
        notes.pack(fill="x")
        feedback = ttk.Label(panel, text="", style="Body.TLabel", foreground=self.colors["danger"])
        feedback.pack(anchor="w", pady=(8, 0))
        def save() -> None:
            try:
                draft = VaultEntry(id=values.id, created_at=values.created_at, updated_at=values.updated_at, notes=notes.get("1.0", "end-1c"), **{key: value.get() for key, value in variables.items()})
                saved = self.vault.save_entry(draft)
                self.current_entry_id = saved.id
                editor.destroy()
                self.refresh_entries()
                self.show_entry_detail(saved)
            except ValidationError as exc:
                feedback.configure(text=str(exc))
        actions = ttk.Frame(panel, style="Surface.TFrame")
        actions.pack(fill="x", pady=(18, 0))
        ttk.Button(actions, text="Cancel", command=editor.destroy).pack(side="right")
        ttk.Button(actions, text="Save account", style="Primary.TButton", command=save).pack(side="right", padx=(0, 8))

    def delete_selected(self, entry: VaultEntry) -> None:
        if messagebox.askyesno("Delete account", f"Delete '{entry.title}'? This cannot be undone.", parent=self):
            self.vault.delete_entry(entry.id)
            self.current_entry_id = None
            self.refresh_entries()
            self.show_empty_detail()

    def show_settings(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Settings")
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        panel = ttk.Frame(dialog, style="Surface.TFrame", padding=27)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="SETTINGS", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(panel, text="Appearance & security", style="Heading.TLabel").pack(anchor="w", pady=(8, 14))
        appearance = ttk.Frame(panel, style="Alt.TFrame", padding=14)
        appearance.pack(fill="x")
        ttk.Label(appearance, text="APPEARANCE", style="Eyebrow.TLabel", background=self.colors["surface_alt"]).pack(anchor="w")
        ttk.Label(appearance, text="Theme", style="Body.TLabel", background=self.colors["surface_alt"]).pack(anchor="w", pady=(10, 4))
        theme_value = tk.StringVar(value=self.preferences.theme)
        theme_box = ttk.Combobox(appearance, state="readonly", values=("dark", "light"), textvariable=theme_value)
        theme_box.pack(fill="x")
        ttk.Label(appearance, text="Background image", style="Body.TLabel", background=self.colors["surface_alt"]).pack(anchor="w", pady=(12, 4))
        background_label = ttk.Label(appearance, text=Path(self.preferences.background_image).name if self.preferences.background_image else "No custom image", style="Muted.TLabel", background=self.colors["surface_alt"], wraplength=320)
        background_label.pack(anchor="w")
        def choose_background() -> None:
            filename = filedialog.askopenfilename(parent=dialog, title="Choose background image", filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")])
            if filename:
                self.preferences.background_image = filename
                self.preferences_service.save(self.preferences)
                background_label.configure(text=Path(filename).name)
                self._background_source = None
                self._draw_background()
        buttons = ttk.Frame(appearance, style="Alt.TFrame")
        buttons.pack(fill="x", pady=(9, 0))
        ttk.Button(buttons, text="Choose image", command=choose_background).pack(side="left")
        ttk.Button(buttons, text="Remove", command=self.clear_background).pack(side="left", padx=(7, 0))
        def apply_theme() -> None:
            self.preferences.theme = theme_value.get()
            self.preferences_service.save(self.preferences)
            dialog.destroy()
            self._configure_style()
            self.show_vault()
        ttk.Button(panel, text="Apply appearance", style="Primary.TButton", command=apply_theme).pack(fill="x", pady=(12, 17))
        ttk.Label(panel, text="CHANGE MASTER PASSWORD", style="Eyebrow.TLabel").pack(anchor="w")
        variables = {name: tk.StringVar() for name in ("current", "new", "confirm")}
        for label, key in (("CURRENT PASSWORD", "current"), ("NEW PASSWORD", "new"), ("CONFIRM NEW PASSWORD", "confirm")):
            self._label_entry(panel, label, variables[key], True)
        feedback = ttk.Label(panel, text="", style="Body.TLabel", foreground=self.colors["danger"], wraplength=330)
        feedback.pack(anchor="w", pady=(8, 0))
        def change_password() -> None:
            try:
                if variables["new"].get() != variables["confirm"].get():
                    raise ValidationError("The new passwords do not match.")
                self.vault.change_master_password(variables["current"].get(), variables["new"].get())
                dialog.destroy()
                messagebox.showinfo("P@ssw0rd", "Master password updated.", parent=self)
            except VaultError as exc:
                feedback.configure(text=str(exc))
        ttk.Button(panel, text="Update master password", command=change_password).pack(fill="x", pady=(8, 0))

    def toggle_theme(self) -> None:
        self.preferences.theme = "light" if self.preferences.theme == "dark" else "dark"
        self.preferences_service.save(self.preferences)
        self.colors = PALETTES[self.preferences.theme]
        self._configure_style()
        self.show_vault()

    def clear_background(self) -> None:
        self.preferences.background_image = ""
        self.preferences_service.save(self.preferences)
        self._background_source = None
        self._draw_background()

    def lock(self) -> None:
        self.vault.lock()
        self.show_gate()

    def _close(self) -> None:
        self.vault.lock()
        self.destroy()


if __name__ == "__main__":
    PasswordApp().mainloop()

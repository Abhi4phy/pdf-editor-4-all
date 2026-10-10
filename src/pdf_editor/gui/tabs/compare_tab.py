"""PDF Side-by-Side Comparison Tab."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from PIL import ImageTk

from pdf_editor.operations import extras

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class CompareTab(ttk.Frame):
    """Side-by-side visual and text diff comparison of two PDFs."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state
        self.paths = {"a": None, "b": None}

        self.file_a_var = tk.StringVar(value="(none)")
        self.file_b_var = tk.StringVar(value="(none)")
        self.page_var = tk.IntVar(value=1)

        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(self, text="Compare two PDFs side by side.", font=("Segoe UI", 10)).pack(pady=(0, 6))

        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, pady=4)

        ttk.Button(ctrl, text="PDF A", command=lambda: self.pick_file("a"), bootstyle="outline").pack(side=tk.LEFT, padx=2)
        ttk.Label(ctrl, textvariable=self.file_a_var, font=("Segoe UI", 8), width=30).pack(side=tk.LEFT, padx=4)

        ttk.Button(ctrl, text="PDF B", command=lambda: self.pick_file("b"), bootstyle="outline").pack(side=tk.LEFT, padx=2)
        ttk.Label(ctrl, textvariable=self.file_b_var, font=("Segoe UI", 8), width=30).pack(side=tk.LEFT, padx=4)

        ttk.Button(ctrl, text="Compare", command=self.run_compare, bootstyle="success").pack(side=tk.RIGHT, padx=2)

        nav = ttk.Frame(self)
        nav.pack(fill=tk.X, pady=2)
        ttk.Label(nav, text="Page:").pack(side=tk.LEFT, padx=2)
        self.page_spin = ttk.Spinbox(nav, from_=1, to=1, width=5, textvariable=self.page_var)
        self.page_spin.pack(side=tk.LEFT, padx=2)
        ttk.Button(nav, text="Show Page", command=self.show_page, bootstyle="outline", width=10).pack(side=tk.LEFT, padx=4)

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, pady=4)

        self.canvas_a = tk.Canvas(container, bg="#e8e8e8")
        self.canvas_b = tk.Canvas(container, bg="#e8e8e8")
        self.canvas_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        self.canvas_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))

        self.result_text = tk.Text(self, height=3, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9))
        self.result_text.pack(fill=tk.X, pady=4)

    def pick_file(self, which: str) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self.paths[which] = path
        name = os.path.basename(path)
        if which == "a":
            self.file_a_var.set(name)
        else:
            self.file_b_var.set(name)

    def run_compare(self) -> None:
        a, b = self.paths["a"], self.paths["b"]
        if not a or not b:
            messagebox.showinfo("Info", "Select both PDFs first.")
            return

        result = extras.compare_pdfs(a, b)
        self.page_spin.config(to=max(result["pages_a"], result["pages_b"]))
        diffs = result["text_diffs"]

        text = (
            f"PDF A: {result['pages_a']} pages, {result['size_a'] / 1024:.0f} KB  |  "
            f"PDF B: {result['pages_b']} pages, {result['size_b'] / 1024:.0f} KB\n"
            f"Pages with text differences: {len(diffs)}"
        )
        if diffs:
            pages = [str(d["page"]) for d in diffs[:10]]
            text += f"  (pages: {', '.join(pages)}{'...' if len(diffs) > 10 else ''})"

        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", text)
        self.result_text.config(state=tk.DISABLED)

        self.page_var.set(1)
        self.show_page()

    def show_page(self) -> None:
        a, b = self.paths["a"], self.paths["b"]
        if not a or not b:
            return

        page = self.page_var.get()
        img_a, img_b = extras.get_comparison_images(a, b, page, zoom=0.8)

        for cv, img in [(self.canvas_a, img_a), (self.canvas_b, img_b)]:
            cv.delete("all")
            if img:
                photo = ImageTk.PhotoImage(img)
                cv.create_image(0, 0, anchor=tk.NW, image=photo)
                cv._photo = photo
                cv.config(scrollregion=(0, 0, img.width, img.height))
            else:
                cv.create_text(100, 100, text="(no page)", font=("Segoe UI", 14))


"""Basic Operations Tab (Extract, Rotate, Watermark, Images-to-PDF)."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from pdf_editor.operations import basic, extras

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class BasicTab(ttk.Frame):
    """Tab for common basic PDF operations."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.LabelFrame(self, text="Common Tasks")
        frame.pack(fill=tk.X, pady=5)

        inner = ttk.Frame(frame, padding=10)
        inner.pack(fill=tk.X)

        ttk.Label(
            inner,
            text="Click a button below → follow prompts to execute operations.",
            font=("Segoe UI", 9), foreground="gray"
        ).pack(anchor=tk.W, pady=(0, 6))

        ttk.Button(inner, text="Extract Pages", command=self.on_extract, style="primary.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(inner, text="Rotate PDF", command=self.on_rotate, style="primary.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(inner, text="Add Watermark", command=self.on_watermark, style="primary.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(inner, text="Image(s) to PDF", command=self.on_images_to_pdf, style="primary.TButton").pack(fill=tk.X, pady=2)

        hints = ttk.LabelFrame(self, text="What each operation needs")
        hints.pack(fill=tk.X, pady=5)

        hints_inner = ttk.Frame(hints, padding=10)
        hints_inner.pack(fill=tk.X)

        for txt in [
            "Extract — Select a PDF → enter page numbers (e.g. 1,3-5,7) → save",
            "Rotate — Select a PDF → pick angle (90°/180°/270°) → save",
            "Watermark — Select a PDF → select watermark PDF → save",
            "Image(s) to PDF — Select image files → save as PDF",
        ]:
            ttk.Label(hints_inner, text=f"  \u2022 {txt}", font=("Segoe UI", 9)).pack(anchor=tk.W)

    def on_extract(self) -> None:
        inp = self.app_state.get_input_file("Select PDF to Extract Pages")
        if not inp:
            return
        pages_str = simpledialog.askstring(
            "Extract Pages", "Enter page numbers (e.g. 1,3-5,7):", parent=self.app_state.window
        )
        if not pages_str:
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        basic.extract_pages(inp, out, pages_str)
        self.app_state.history.record("extract_pages", inp, out, f"Pages: {pages_str}")
        self.app_state.set_active_file(out)
        self.app_state.notify_success("Pages extracted successfully!")

    def on_rotate(self) -> None:
        inp = self.app_state.get_input_file("Select PDF to Rotate")
        if not inp:
            return
        angle = simpledialog.askinteger(
            "Rotate PDF", "Enter rotation angle (90, 180, or 270):",
            parent=self.app_state.window, minvalue=90, maxvalue=270
        )
        if angle not in (90, 180, 270):
            messagebox.showwarning("Warning", "Angle must be 90, 180, or 270.")
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        basic.rotate_pdf(inp, out, angle)
        self.app_state.history.record("rotate", inp, out, f"{angle}°")
        self.app_state.set_active_file(out)
        self.app_state.notify_success("PDF rotated successfully!")

    def on_watermark(self) -> None:
        inp = self.app_state.get_input_file("Select Source PDF")
        if not inp:
            return
        wm = filedialog.askopenfilename(title="Select watermark PDF", filetypes=[("PDF files", "*.pdf")])
        if not wm:
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        basic.add_watermark(inp, out, wm)
        self.app_state.history.record("watermark", inp, out)
        self.app_state.set_active_file(out)
        self.app_state.notify_success("Watermark added successfully!")

    def on_images_to_pdf(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
        )
        if not files:
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        extras.images_to_pdf(list(files), out)
        self.app_state.history.record("images_to_pdf", str(files[0]), out, f"{len(files)} images")
        self.app_state.set_active_file(out)
        self.app_state.notify_success(f"Created PDF from {len(files)} images!")


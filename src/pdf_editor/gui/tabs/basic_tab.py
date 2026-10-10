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
        from pdf_editor.gui.components.cards import build_card_grid

        ttk.Label(
            self,
            text="Perform essential operations on your PDF documents with one-click tools.",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=(0, 6))

        cards_data = [
            {
                "title": "Extract Pages",
                "description": "Extract specific page numbers or ranges (e.g., 1, 3-5, 7) into a new PDF document.",
                "button_text": "Extract Pages",
                "command": self.on_extract,
                "icon": "✂️",
                "bootstyle": "primary",
            },
            {
                "title": "Rotate PDF",
                "description": "Rotate all pages in document by 90°, 180°, or 270° clockwise.",
                "button_text": "Rotate PDF",
                "command": self.on_rotate,
                "icon": "🔄",
                "bootstyle": "primary",
            },
            {
                "title": "Add Watermark",
                "description": "Overlay a transparent watermark PDF across all pages of your source document.",
                "button_text": "Watermark PDF",
                "command": self.on_watermark,
                "icon": "💧",
                "bootstyle": "primary",
            },
            {
                "title": "Image(s) to PDF",
                "description": "Combine multiple image files (PNG, JPG, WEBP) into a clean single PDF file.",
                "button_text": "Convert Images",
                "command": self.on_images_to_pdf,
                "icon": "🖼️",
                "bootstyle": "success",
            },
        ]

        build_card_grid(self, cards_data, columns=2)


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


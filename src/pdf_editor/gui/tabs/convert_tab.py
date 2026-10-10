"""Convert Tab (To Word, Images, Text)."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from pdf_editor.operations import converter

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class ConvertTab(ttk.Frame):
    """Tab for PDF conversions."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.LabelFrame(self, text="Convert PDF")
        frame.pack(fill=tk.X, pady=5)

        inner = ttk.Frame(frame, padding=10)
        inner.pack(fill=tk.X)

        ttk.Button(inner, text="To Word Document", command=self.on_pdf_to_word, style="success.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(inner, text="To Images", command=self.on_pdf_to_images, style="success.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(inner, text="To Text File", command=self.on_pdf_to_text, style="success.TButton").pack(fill=tk.X, pady=2)

    def on_pdf_to_word(self) -> None:
        inp = self.app_state.get_input_file("Select PDF to Convert to Word")
        if not inp:
            return
        out = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word files", "*.docx")])
        if not out:
            return
        converter.pdf_to_word(inp, out)
        self.app_state.history.record("to_word", inp, out)
        self.app_state.notify_success("PDF converted to Word!")

    def on_pdf_to_images(self) -> None:
        inp = self.app_state.get_input_file("Select PDF to Convert to Images")
        if not inp:
            return
        out_dir = filedialog.askdirectory(title="Output directory for images")
        if not out_dir:
            return
        paths = converter.pdf_to_images(inp, out_dir)
        self.app_state.history.record("to_images", inp, out_dir, f"{len(paths)} pages")
        self.app_state.notify_success(f"Converted {len(paths)} pages to images!")

    def on_pdf_to_text(self) -> None:
        inp = self.app_state.get_input_file("Select PDF to Convert to Text")
        if not inp:
            return
        out = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not out:
            return
        converter.pdf_to_text(inp, out)
        self.app_state.history.record("to_text", inp, out)
        self.app_state.notify_success("PDF converted to text!")


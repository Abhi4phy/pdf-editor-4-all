"""Application shared state management for PDF Editor 4 All."""

from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Optional

from pdf_editor.history import OperationHistory, add_recent_file
from pdf_editor.utils import get_pdf_info


class AppState:
    """Encapsulates shared state and helper workflows for all GUI components."""

    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        self.status_var = tk.StringVar(value="Ready")
        self.active_file_var = tk.StringVar(value="Active PDF: (None loaded)")
        self.active_file: str | None = None
        self.signature_path: str | None = None
        self.history = OperationHistory()

        # Progress bar state
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value="")

    def set_active_file(self, path: str, info_widget: Optional[tk.Text] = None) -> None:
        """Set the active PDF path across all tabs."""
        if path and os.path.isfile(path):
            self.active_file = path
            name = os.path.basename(path)
            self.active_file_var.set(f"Active PDF: {name}")
            add_recent_file(path)
            if info_widget:
                self.show_file_info(path, info_widget)

    def update_status(self, msg: str) -> None:
        """Update the status bar text."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"{ts}  —  {msg}")

    def show_file_info(self, path: str, text_widget: tk.Text) -> None:
        """Display metadata and specs for a PDF file in the info panel."""
        try:
            info = get_pdf_info(path)
            text = (
                f"Title: {info['title']}  |  Author: {info['author']}  |  "
                f"Pages: {info['pages']}  |  Created: {info['created']}  |  "
                f"Size: {info['file_size'] / 1024:.1f} KB"
            )
        except Exception:
            text = "Could not read file information."

        text_widget.config(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", text)
        text_widget.config(state=tk.DISABLED)

    def get_input_file(self, title: str = "Select PDF", multiple: bool = False) -> str | list[str] | None:
        """Helper that prompts for a file or offers to use the currently active file."""
        if not multiple and self.active_file and os.path.isfile(self.active_file):
            use_active = messagebox.askyesnocancel(
                "Use Active File?",
                f"Use currently active file?\n\n{os.path.basename(self.active_file)}\n\n(Click 'No' to pick a different file)",
                parent=self.window,
            )
            if use_active is True:
                return self.active_file
            elif use_active is None:
                return None

        ft = [("PDF files", "*.pdf")]
        if multiple:
            paths = filedialog.askopenfilenames(title=title, filetypes=ft)
            for p in paths:
                add_recent_file(p)
            return list(paths)

        path = filedialog.askopenfilename(title=title, filetypes=ft)
        if path:
            self.set_active_file(path)
        return path

    def ask_output_file(self, ext: str = ".pdf") -> str:
        """Prompt user for destination file path."""
        return filedialog.asksaveasfilename(defaultextension=ext)

    def notify_success(self, msg: str) -> None:
        """Show success message box and update status."""
        self.update_status(msg)
        messagebox.showinfo("Success", msg)


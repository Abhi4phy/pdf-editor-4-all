"""Metadata Editor Tab."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Dict

import ttkbootstrap as ttk

from pdf_editor.operations import extras

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class MetadataTab(ttk.Frame):
    """Tab for viewing and editing PDF document metadata."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state
        self.meta_file: str | None = None
        self.entries: Dict[str, ttk.Entry] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(self, text="View and edit PDF metadata fields.", font=("Segoe UI", 10)).pack(pady=(0, 8))

        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, pady=4)
        ttk.Button(ctrl, text="Load PDF", command=self.load_metadata, bootstyle="primary").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Save As", command=self.save_metadata, bootstyle="success").pack(side=tk.RIGHT, padx=2)

        fields_frame = ttk.LabelFrame(self, text="Metadata Fields")
        fields_frame.pack(fill=tk.X, pady=6)

        inner = ttk.Frame(fields_frame, padding=10)
        inner.pack(fill=tk.X)

        for field in ["title", "author", "subject", "keywords"]:
            row = ttk.Frame(inner)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=f"{field.title()}:", width=10, font=("Segoe UI", 10)).pack(side=tk.LEFT)
            entry = ttk.Entry(row, font=("Segoe UI", 10))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            self.entries[field] = entry

    def load_metadata(self) -> None:
        path = self.app_state.get_input_file("Select PDF for Metadata")
        if not path:
            return

        self.meta_file = path
        self.app_state.set_active_file(path)
        meta = extras.get_metadata(path)

        for field, entry in self.entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, meta.get(field, ""))

        self.app_state.update_status(f"Loaded metadata: {os.path.basename(path)}")

    def save_metadata(self) -> None:
        if not self.meta_file:
            messagebox.showinfo("Info", "Load a PDF first.")
            return

        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if not out:
            return

        extras.edit_metadata(
            self.meta_file, out,
            title=self.entries["title"].get() or None,
            author=self.entries["author"].get() or None,
            subject=self.entries["subject"].get() or None,
            keywords=self.entries["keywords"].get() or None,
        )

        self.app_state.history.record("edit_metadata", self.meta_file, out)
        self.app_state.set_active_file(out)
        self.app_state.notify_success("Metadata saved!")


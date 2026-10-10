"""Security Tab (Encrypt, Decrypt)."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog
from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from pdf_editor.operations import security

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class SecurityTab(ttk.Frame):
    """Tab for PDF security and password protection."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.LabelFrame(self, text="Security Options")
        frame.pack(fill=tk.X, pady=5)

        inner = ttk.Frame(frame, padding=10)
        inner.pack(fill=tk.X)

        ttk.Button(inner, text="Encrypt PDF", command=self.on_encrypt, style="warning.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(inner, text="Remove Password", command=self.on_remove_password, style="warning.TButton").pack(fill=tk.X, pady=2)

    def on_encrypt(self) -> None:
        inp = self.app_state.get_input_file("Select PDF to Encrypt")
        if not inp:
            return
        pw = simpledialog.askstring("Encrypt", "Enter password:", show="*", parent=self.app_state.window)
        if not pw:
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        security.encrypt_pdf(inp, out, pw)
        self.app_state.history.record("encrypt", inp, out)
        self.app_state.set_active_file(out)
        self.app_state.notify_success("PDF encrypted!")

    def on_remove_password(self) -> None:
        inp = self.app_state.get_input_file("Select PDF to Decrypt")
        if not inp:
            return
        pw = simpledialog.askstring("Decrypt", "Enter current password:", show="*", parent=self.app_state.window)
        if not pw:
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        security.remove_password(inp, out, pw)
        self.app_state.history.record("remove_password", inp, out)
        self.app_state.set_active_file(out)
        self.app_state.notify_success("Password removed!")


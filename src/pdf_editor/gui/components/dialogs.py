"""Reusable Dialog Windows for Recent Files and History."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable

import ttkbootstrap as ttk

from pdf_editor.history import clear_recent_files, get_recent_files

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


def show_recent_files_dialog(app_state: AppState, open_callback: Callable[[str], None]) -> None:
    """Show the Recent Files selection modal dialog."""
    recents = get_recent_files()
    if not recents:
        messagebox.showinfo("Recent Files", "No recent files.")
        return

    win = ttk.Toplevel(app_state.window)
    win.title("Recent Files")
    win.geometry("500x350")
    win.grab_set()

    lb = tk.Listbox(win, font=("Consolas", 9))
    sb = ttk.Scrollbar(win, command=lb.yview)
    lb.config(yscrollcommand=sb.set)
    lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
    sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

    for r in recents:
        lb.insert(tk.END, f"{r['timestamp'][:10]}  {r['path']}")

    def open_selected():
        sel = lb.curselection()
        if sel:
            path = recents[sel[0]]["path"]
            if os.path.isfile(path):
                open_callback(path)
                win.destroy()
            else:
                messagebox.showwarning("Not Found", f"File no longer exists:\n{path}")

    btn_frame = ttk.Frame(win)
    btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
    ttk.Button(btn_frame, text="Open", command=open_selected, bootstyle="primary").pack(side=tk.LEFT, padx=2)
    ttk.Button(
        btn_frame, text="Clear History",
        command=lambda: (clear_recent_files(), win.destroy()),
        bootstyle="outline-danger"
    ).pack(side=tk.RIGHT, padx=2)


def show_history_dialog(app_state: AppState) -> None:
    """Show operation history window."""
    entries = app_state.history.entries
    if not entries:
        messagebox.showinfo("History", "No operations recorded yet.")
        return

    win = ttk.Toplevel(app_state.window)
    win.title("Operation History")
    win.geometry("620x360")
    win.grab_set()

    cols = ("time", "operation", "input", "output", "details")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    tree.heading("time", text="Time")
    tree.heading("operation", text="Operation")
    tree.heading("input", text="Input")
    tree.heading("output", text="Output")
    tree.heading("details", text="Details")

    tree.column("time", width=65, stretch=False)
    tree.column("operation", width=110, stretch=False)
    tree.column("input", width=150)
    tree.column("output", width=150)
    tree.column("details", width=130)

    for e in reversed(entries):
        tree.insert("", tk.END, values=(
            e["timestamp"],
            e["operation"],
            os.path.basename(e["input_file"]),
            os.path.basename(e["output_file"]),
            e["details"][:40],
        ))

    sb = ttk.Scrollbar(win, command=tree.yview)
    tree.config(yscrollcommand=sb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
    sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)


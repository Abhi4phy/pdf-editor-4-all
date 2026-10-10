"""Batch Operations Tab."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, List

import ttkbootstrap as ttk

from pdf_editor.operations import advanced, basic, converter

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class BatchTab(ttk.Frame):
    """Tab for multi-file batch PDF processing."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state
        self.batch_files: List[str] = []
        self.op_var = tk.StringVar(value="compress")
        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(self, text="Apply an operation to multiple PDF files at once.", font=("Segoe UI", 10)).pack(pady=(0, 8))

        list_frame = ttk.LabelFrame(self, text="Files")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        list_inner = ttk.Frame(list_frame, padding=8)
        list_inner.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(list_inner)
        btn_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(btn_row, text="Add Files", command=self.add_files, bootstyle="outline").pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Clear", command=self.clear_files, bootstyle="outline-danger").pack(side=tk.LEFT, padx=2)

        self.listbox = tk.Listbox(list_inner, height=8, selectmode=tk.EXTENDED)
        sb = ttk.Scrollbar(list_inner, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        op_frame = ttk.LabelFrame(self, text="Operation")
        op_frame.pack(fill=tk.X, pady=4)

        op_inner = ttk.Frame(op_frame, padding=8)
        op_inner.pack(fill=tk.X)

        ops = [
            ("Compress", "compress"),
            ("Add Page Numbers", "page_numbers"),
            ("Rotate 90°", "rotate_90"),
            ("Rotate 180°", "rotate_180"),
            ("Rotate 270°", "rotate_270"),
            ("Convert to Images", "to_images"),
            ("Convert to Text", "to_text"),
        ]
        for label, val in ops:
            ttk.Radiobutton(op_inner, text=label, variable=self.op_var, value=val).pack(anchor=tk.W, pady=1)

        ttk.Button(self, text="Run Batch Operation", command=self.run_batch, bootstyle="success", width=25).pack(pady=8)

    def add_files(self, file_list: list[str] | None = None) -> None:
        files = file_list or filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for f in files:
            if f not in self.batch_files:
                self.batch_files.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))

    def clear_files(self) -> None:
        self.batch_files.clear()
        self.listbox.delete(0, tk.END)

    def run_batch(self) -> None:
        if not self.batch_files:
            messagebox.showinfo("Info", "Add files first.")
            return
        out_dir = filedialog.askdirectory(title="Select output directory")
        if not out_dir:
            return

        op = self.op_var.get()
        total = len(self.batch_files)
        errors = []

        for i, f in enumerate(self.batch_files):
            base = os.path.splitext(os.path.basename(f))[0]
            try:
                if op == "compress":
                    advanced.compress_pdf(f, os.path.join(out_dir, f"{base}_compressed.pdf"), quality="medium")
                elif op == "page_numbers":
                    advanced.add_page_numbers(f, os.path.join(out_dir, f"{base}_numbered.pdf"))
                elif op.startswith("rotate_"):
                    angle = int(op.split("_")[1])
                    basic.rotate_pdf(f, os.path.join(out_dir, f"{base}_rotated{angle}.pdf"), angle)
                elif op == "to_images":
                    converter.pdf_to_images(f, os.path.join(out_dir, base))
                elif op == "to_text":
                    converter.pdf_to_text(f, os.path.join(out_dir, f"{base}.txt"))
            except Exception as e:
                errors.append(f"{os.path.basename(f)}: {e}")

        if errors:
            messagebox.showwarning("Batch Complete", f"Done with {len(errors)} error(s):\n" + "\n".join(errors[:5]))
        else:
            self.app_state.notify_success(f"Batch operation complete! {total} files processed.")


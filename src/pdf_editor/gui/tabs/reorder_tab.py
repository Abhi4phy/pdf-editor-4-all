"""Visual Page Reordering Gallery Tab."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, List

import fitz
import ttkbootstrap as ttk
from PIL import Image, ImageTk

from pdf_editor.operations import extras

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class ReorderTab(ttk.Frame):
    """Visual page reordering gallery with page thumbnail cards."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state

        self.doc_path: str | None = None
        self.items: List[dict] = []

        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(
            self, text="Load a PDF, view visual page thumbnails, reorder/rotate/delete pages, then save.",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 6))

        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, pady=4)

        ttk.Button(ctrl, text="Load PDF", command=self.load_pdf, bootstyle="primary").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Save As", command=self.save_reordered, bootstyle="success").pack(side=tk.RIGHT, padx=2)

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, pady=4)

        vsb = ttk.Scrollbar(container, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas = tk.Canvas(container, bg="#f8f9fa", yscrollcommand=vsb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=self.canvas.yview)

        self.grid_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor=tk.NW)
        self.grid_frame.bind(
            "<Configure>",
            lambda e: self.canvas.config(scrollregion=self.canvas.bbox("all"))
        )

    def load_pdf(self) -> None:
        path = self.app_state.get_input_file("Select PDF to Reorder")
        if not path:
            return

        doc = fitz.open(path)
        total = doc.page_count
        doc.close()

        self.doc_path = path
        self.items = [{"file": path, "page": p, "rotation": 0} for p in range(1, total + 1)]
        self.refresh()
        self.app_state.set_active_file(path)

    def refresh(self) -> None:
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        if not self.items:
            empty_frame = ttk.Frame(self.grid_frame, padding=30)
            empty_frame.pack(fill=tk.BOTH, expand=True)
            ttk.Label(
                empty_frame, text="📑 Visual Page Reorder Gallery",
                font=("Segoe UI", 14, "bold"), bootstyle="primary"
            ).pack(pady=(10, 4))
            ttk.Label(
                empty_frame, text="No document loaded yet.\nClick 'Load PDF' above to preview, reorder, rotate, or remove pages visually.",
                font=("Segoe UI", 10), justify=tk.CENTER, bootstyle="info"
            ).pack(pady=4)
            return

        cols = 4
        for idx, item in enumerate(self.items):
            r = idx // cols
            c = idx % cols

            card = ttk.LabelFrame(self.grid_frame, text=f" #{idx + 1} ")
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            card_inner = ttk.Frame(card, padding=4)
            card_inner.pack(fill=tk.BOTH, expand=True)

            try:
                pil_img = extras.get_page_thumbnail(item["file"], item["page"], width=140)
                if item["rotation"]:
                    pil_img = pil_img.rotate(-item["rotation"], expand=True)
                photo = ImageTk.PhotoImage(pil_img)
                lbl_img = ttk.Label(card_inner, image=photo)
                lbl_img._photo = photo
                lbl_img.pack(pady=2)
            except Exception:
                ttk.Label(card_inner, text="[Thumbnail Error]", font=("Segoe UI", 8)).pack(pady=10)

            rot_str = f" • {item['rotation']}°" if item['rotation'] else ""
            ttk.Label(
                card_inner, text=f"Page {idx + 1} (Orig p.{item['page']}){rot_str}",
                font=("Segoe UI", 8, "bold")
            ).pack(pady=(2, 4))

            btn_row = ttk.Frame(card_inner)
            btn_row.pack(pady=2)

            ttk.Button(btn_row, text="◄", width=2, command=lambda i=idx: self.move_item(i, -1),
                       bootstyle="outline").pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_row, text="►", width=2, command=lambda i=idx: self.move_item(i, 1),
                       bootstyle="outline").pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_row, text="↺", width=2, command=lambda i=idx: self.rotate_item(i, 90),
                       bootstyle="outline").pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_row, text="✖", width=2, command=lambda i=idx: self.remove_item(i),
                       bootstyle="outline-danger").pack(side=tk.LEFT, padx=1)

    def move_item(self, idx: int, direction: int) -> None:
        target = idx + direction
        if 0 <= target < len(self.items):
            self.items[idx], self.items[target] = self.items[target], self.items[idx]
            self.refresh()

    def rotate_item(self, idx: int, angle: int) -> None:
        self.items[idx]["rotation"] = (self.items[idx]["rotation"] + angle) % 360
        self.refresh()

    def remove_item(self, idx: int) -> None:
        if len(self.items) <= 1:
            messagebox.showwarning("Warning", "Cannot delete the last page.")
            return
        self.items.pop(idx)
        self.refresh()

    def save_reordered(self) -> None:
        if not self.doc_path or not self.items:
            messagebox.showinfo("Info", "Load a PDF first.")
            return

        out = self.app_state.ask_output_file()
        if not out:
            return

        extras.merge_pdf_pages(self.items, out)
        self.app_state.history.record("reorder_pages", self.doc_path, out, f"{len(self.items)} pages")
        self.app_state.set_active_file(out)
        self.app_state.notify_success("Pages reordered and saved successfully!")


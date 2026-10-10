"""Visual PDF Merge Workspace Tab."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, List

import fitz
import ttkbootstrap as ttk
from PIL import Image, ImageTk

from pdf_editor.operations import extras

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class VisualMergeTab(ttk.Frame):
    """Interactive Visual PDF & Page Merge Workspace."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state

        self.items: List[dict] = []  # List of {"file": path, "page": page_num, "rotation": angle}

        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(
            self, text="Add PDF files or pages, preview thumbnails, reorder/rotate/delete, then merge.",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 6))

        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, pady=4)

        ttk.Button(ctrl, text="+ Add PDF Files", command=self.add_files, bootstyle="primary").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Clear All", command=self.clear_all, bootstyle="outline-danger").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Merge All Pages", command=self.run_merge, bootstyle="success").pack(side=tk.RIGHT, padx=2)

        # Scrollable Thumbnail Grid
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

    def add_files(self, file_list: list[str] | None = None) -> None:
        files = file_list or filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if not files:
            return

        for f in files:
            try:
                doc = fitz.open(f)
                total = doc.page_count
                doc.close()
                for p in range(1, total + 1):
                    self.items.append({"file": f, "page": p, "rotation": 0})
            except Exception:
                pass
        self.refresh()

    def clear_all(self) -> None:
        self.items.clear()
        self.refresh()

    def refresh(self) -> None:
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        if not self.items:
            empty_frame = ttk.Frame(self.grid_frame, padding=30)
            empty_frame.pack(fill=tk.BOTH, expand=True)
            ttk.Label(
                empty_frame, text="🔀 Visual PDF Merge Workspace",
                font=("Segoe UI", 14, "bold"), bootstyle="primary"
            ).pack(pady=(10, 4))
            ttk.Label(
                empty_frame, text="No PDF pages loaded yet.\nClick '+ Add PDF Files' above or drag & drop PDF files onto the window to begin.",
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

            fname = os.path.basename(item["file"])
            if len(fname) > 18:
                fname = fname[:15] + "..."
            rot_str = f" • {item['rotation']}°" if item['rotation'] else ""
            ttk.Label(
                card_inner, text=f"{fname}\nPage {item['page']}{rot_str}",
                font=("Segoe UI", 8, "bold"), justify=tk.CENTER
            ).pack(pady=(2, 4))

            btn_row = ttk.Frame(card_inner)
            btn_row.pack(pady=2)

            ttk.Button(btn_row, text="↺", width=2, command=lambda i=idx: self.rotate_item(i, -90),
                       bootstyle="outline").pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_row, text="↻", width=2, command=lambda i=idx: self.rotate_item(i, 90),
                       bootstyle="outline").pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_row, text="▲", width=2, command=lambda i=idx: self.move_item(i, -1),
                       bootstyle="outline").pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_row, text="▼", width=2, command=lambda i=idx: self.move_item(i, 1),
                       bootstyle="outline").pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_row, text="✖", width=2, command=lambda i=idx: self.remove_item(i),
                       bootstyle="outline-danger").pack(side=tk.LEFT, padx=1)

    def rotate_item(self, idx: int, angle: int) -> None:
        self.items[idx]["rotation"] = (self.items[idx]["rotation"] + angle) % 360
        self.refresh()

    def move_item(self, idx: int, direction: int) -> None:
        target = idx + direction
        if 0 <= target < len(self.items):
            self.items[idx], self.items[target] = self.items[target], self.items[idx]
            self.refresh()

    def remove_item(self, idx: int) -> None:
        self.items.pop(idx)
        self.refresh()

    def run_merge(self) -> None:
        if not self.items:
            messagebox.showinfo("Info", "Add PDF pages first.")
            return

        out = self.app_state.ask_output_file()
        if not out:
            return

        extras.merge_pdf_pages(self.items, out)
        self.app_state.history.record("visual_merge", self.items[0]["file"], out, f"{len(self.items)} pages")
        self.app_state.set_active_file(out)
        self.app_state.notify_success(f"Merged {len(self.items)} pages successfully!")


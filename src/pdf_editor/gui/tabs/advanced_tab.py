"""Advanced Operations Tab (Compress, Page Numbers, Header/Footer, Split, Bookmarks)."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from pdf_editor.operations import advanced

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class AdvancedTab(ttk.Frame):
    """Tab for advanced PDF operations."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state
        self.compress_quality_var = tk.StringVar(value="medium")
        self.compress_desc_var = tk.StringVar(value="Balanced — images resampled to 150 DPI, JPEG 80")
        self._build_ui()

    def _build_ui(self) -> None:
        from pdf_editor.gui.components.cards import build_card_grid

        # Compress Card Section
        comp_frame = ttk.LabelFrame(self, text="📦 PDF File Compression")
        comp_frame.pack(fill=tk.X, pady=(0, 6))

        comp_inner = ttk.Frame(comp_frame, padding=10)
        comp_inner.pack(fill=tk.X)

        quality_row = ttk.Frame(comp_inner)
        quality_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(quality_row, text="Compression Preset:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        for val, label in [("low", "Low (Fast, Lossless)"), ("medium", "Medium (Balanced 150 DPI)"), ("high", "High (Max 96 DPI)")]:
            rb = ttk.Radiobutton(quality_row, text=label, variable=self.compress_quality_var, value=val)
            rb.pack(side=tk.LEFT, padx=6)

        ttk.Label(
            comp_inner, textvariable=self.compress_desc_var,
            font=("Segoe UI", 8, "italic"), bootstyle="info"
        ).pack(anchor=tk.W, pady=(2, 6))
        self.compress_quality_var.trace_add("write", self._on_compress_quality_change)

        ttk.Button(comp_inner, text="Compress PDF File", command=self.on_compress, bootstyle="info", width=20).pack(anchor=tk.W)

        # Advanced Tools Grid
        ttk.Label(self, text="Advanced Document Structure & Formatting Tools", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(8, 4))

        cards_data = [
            {
                "title": "Add Page Numbers",
                "description": "Automatically insert clean page numbers (Page X of Y) at bottom center of every page.",
                "button_text": "Number Pages",
                "command": self.on_page_numbers,
                "icon": "🔢",
                "bootstyle": "info",
            },
            {
                "title": "Header & Footer",
                "description": "Insert custom header text top-left and footer text bottom-left across document pages.",
                "button_text": "Add Header/Footer",
                "command": self.on_header_footer,
                "icon": "🏷️",
                "bootstyle": "info",
            },
            {
                "title": "Split PDF",
                "description": "Split every page of a multi-page PDF document into individual single-page PDF files.",
                "button_text": "Split PDF",
                "command": self.on_split,
                "icon": "📂",
                "bootstyle": "info",
            },
            {
                "title": "Manage Bookmarks",
                "description": "View existing PDF outline bookmarks and add new structured chapter/section jump bookmarks.",
                "button_text": "Bookmarks",
                "command": self.on_manage_bookmarks,
                "icon": "🔖",
                "bootstyle": "info",
            },
        ]

        build_card_grid(self, cards_data, columns=2)

    def _on_compress_quality_change(self, *_args) -> None:
        descriptions = {
            "low": "Fast, lossless — stream compression only",
            "medium": "Balanced — images resampled to 150 DPI, JPEG 80",
            "high": "Max compression — images at 96 DPI, JPEG 50 (smaller file, lower image quality)",
        }
        self.compress_desc_var.set(descriptions.get(self.compress_quality_var.get(), ""))

    def on_compress(self) -> None:
        quality = self.compress_quality_var.get()
        inp = self.app_state.get_input_file("Select PDF to Compress")
        if not inp:
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        result = advanced.compress_pdf(inp, out, quality=quality)
        self.app_state.history.record("compress", inp, out, f"quality={quality}")
        self.app_state.set_active_file(out)
        self.app_state.notify_success(
            f"Compressed [{quality}]! "
            f"{result['original_kb']:.0f} KB → {result['compressed_kb']:.0f} KB "
            f"({result['reduction_pct']:.1f}% smaller)"
        )

    def on_page_numbers(self) -> None:
        inp = self.app_state.get_input_file("Select PDF for Page Numbers")
        if not inp:
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        advanced.add_page_numbers(inp, out)
        self.app_state.history.record("page_numbers", inp, out)
        self.app_state.set_active_file(out)
        self.app_state.notify_success("Page numbers added successfully!")

    def on_header_footer(self) -> None:
        inp = self.app_state.get_input_file("Select PDF for Header/Footer")
        if not inp:
            return
        header = simpledialog.askstring("Header", "Header text (empty for none):", parent=self.app_state.window)
        footer = simpledialog.askstring("Footer", "Footer text (empty for none):", parent=self.app_state.window)
        if not header and not footer:
            messagebox.showinfo("Info", "No header or footer provided.")
            return
        out = self.app_state.ask_output_file()
        if not out:
            return
        advanced.add_header_footer(inp, out, header_text=header or "", footer_text=footer or "")
        self.app_state.history.record("header_footer", inp, out)
        self.app_state.set_active_file(out)
        self.app_state.notify_success("Header/footer added successfully!")

    def on_split(self) -> None:
        inp = self.app_state.get_input_file("Select PDF to Split")
        if not inp:
            return
        out_dir = filedialog.askdirectory(title="Select output directory")
        if not out_dir:
            return
        paths = advanced.split_pdf(inp, out_dir)
        self.app_state.history.record("split", inp, out_dir, f"{len(paths)} pages")
        self.app_state.notify_success(f"PDF split into {len(paths)} pages!")

    def on_manage_bookmarks(self) -> None:
        inp = self.app_state.get_input_file("Select PDF for Bookmarks")
        if not inp:
            return
        existing = advanced.get_bookmarks(inp)

        bm_win = ttk.Toplevel(self.app_state.window)
        bm_win.title("Manage Bookmarks")
        bm_win.geometry("520x550")
        bm_win.grab_set()

        ttk.Label(bm_win, text="Existing Bookmarks", font=("Segoe UI", 12, "bold")).pack(pady=(10, 4))

        lb_frame = ttk.Frame(bm_win)
        lb_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        is_dark = (ttk.Style().theme.name == "darkly")
        lb = tk.Listbox(
            lb_frame, height=10,
            bg="#1e1e1e" if is_dark else "#ffffff",
            fg="#ffffff" if is_dark else "#000000",
            selectbackground="#0d6efd", selectforeground="#ffffff"
        )
        sb = ttk.Scrollbar(lb_frame, orient=tk.VERTICAL, command=lb.yview)
        lb.config(yscrollcommand=sb.set)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for bm in existing:
            indent = "  " * bm.get("depth", 0)
            lb.insert(tk.END, f"{indent}{bm['title']}  (p. {bm['page']})")
        if not existing:
            lb.insert(tk.END, "(no bookmarks)")

        ttk.Separator(bm_win).pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(bm_win, text="Add New Bookmarks", font=("Segoe UI", 12, "bold")).pack(pady=4)

        entries_frame = ttk.Frame(bm_win, padding=8)
        entries_frame.pack(fill=tk.X, padx=10)
        entry_widgets: list[tuple] = []

        def add_row():
            row = ttk.Frame(entries_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text="Title:").pack(side=tk.LEFT)
            te = ttk.Entry(row, width=25)
            te.pack(side=tk.LEFT, padx=4)
            ttk.Label(row, text="Page:").pack(side=tk.LEFT)
            pe = ttk.Entry(row, width=6)
            pe.pack(side=tk.LEFT, padx=4)
            entry_widgets.append((te, pe))

        for _ in range(3):
            add_row()
        ttk.Button(bm_win, text="+ Add Row", command=add_row, bootstyle="outline").pack(pady=4)

        def save():
            bms = []
            for te, pe in entry_widgets:
                t = te.get().strip()
                p = pe.get().strip()
                if t and p:
                    try:
                        bms.append({"title": t, "page": int(p)})
                    except ValueError:
                        pass
            if not bms:
                messagebox.showinfo("Info", "No bookmarks to add.", parent=bm_win)
                return
            out = self.app_state.ask_output_file()
            if not out:
                return
            advanced.add_bookmarks(inp, out, bms)
            self.app_state.history.record("bookmarks", inp, out, f"{len(bms)} bookmarks")
            self.app_state.set_active_file(out)
            self.app_state.notify_success(f"Added {len(bms)} bookmarks!")
            bm_win.destroy()

        ttk.Button(bm_win, text="Save Bookmarks", command=save, bootstyle="success").pack(pady=10)


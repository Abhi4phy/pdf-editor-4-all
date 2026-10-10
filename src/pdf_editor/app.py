"""PDF Editor 4 All — Graphical User Interface.

Modularized Architecture:
- pdf_editor.gui.state.AppState: Centralized state management
- pdf_editor.gui.tabs.*: Fragmented, focused tab modules
- pdf_editor.gui.components.*: Reusable modal dialogs & UI controls
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

from pdf_editor import __app_name__, __version__
from pdf_editor.gui.components.dialogs import show_history_dialog, show_recent_files_dialog
from pdf_editor.gui.state import AppState
from pdf_editor.gui.tabs.advanced_tab import AdvancedTab
from pdf_editor.gui.tabs.basic_tab import BasicTab
from pdf_editor.gui.tabs.batch_tab import BatchTab
from pdf_editor.gui.tabs.compare_tab import CompareTab
from pdf_editor.gui.tabs.convert_tab import ConvertTab
from pdf_editor.gui.tabs.metadata_tab import MetadataTab
from pdf_editor.gui.tabs.preview_tab import PreviewTab
from pdf_editor.gui.tabs.reorder_tab import ReorderTab
from pdf_editor.gui.tabs.security_tab import SecurityTab
from pdf_editor.gui.tabs.signature_tab import SignatureTab
from pdf_editor.gui.tabs.vmerge_tab import VisualMergeTab
from pdf_editor.utils import setup_logging

logger = logging.getLogger("pdf_editor.app")


class PDFEditorApp:
    """Tkinter-based main window application shell."""

    def __init__(self) -> None:
        setup_logging()

        self._dark_mode = False
        self._current_theme = "cosmo"

        self.window = ttk.Window(themename=self._current_theme)
        self.window.title(f"{__app_name__} v{__version__}")
        self.window.geometry("1080x980")
        self.window.minsize(850, 680)

        # Centralized App State
        self.app_state = AppState(self.window)

        self._build_ui()
        self._setup_drag_and_drop()
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        self.window.bind("<Control-o>", lambda e: self.preview_tab.open_pdf())
        self.window.bind("<Control-z>", lambda e: self._on_undo())
        self.window.bind("<Control-plus>", lambda e: self.preview_tab.zoom_in())
        self.window.bind("<Control-equal>", lambda e: self.preview_tab.zoom_in())
        self.window.bind("<Control-minus>", lambda e: self.preview_tab.zoom_out())

    def _build_ui(self) -> None:
        root = ttk.Frame(self.window, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        # Top Bar
        top_bar = ttk.Frame(root)
        top_bar.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(top_bar, text=__app_name__, font=("Segoe UI", 20, "bold")).pack(side=tk.LEFT)
        ttk.Label(top_bar, text=f"v{__version__}", font=("Segoe UI", 9),
                  bootstyle="secondary").pack(side=tk.LEFT, padx=(6, 0), anchor=tk.S)

        right_frame = ttk.Frame(top_bar)
        right_frame.pack(side=tk.RIGHT)

        self._dark_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            right_frame, text="Dark Mode", variable=self._dark_mode_var,
            command=self._toggle_dark_mode, bootstyle="round-toggle"
        ).pack(side=tk.RIGHT, padx=8)

        ttk.Button(right_frame, text="Undo (Ctrl+Z)", command=self._on_undo,
                   bootstyle="outline-secondary", width=12).pack(side=tk.RIGHT, padx=4)

        ttk.Button(right_frame, text="History", command=lambda: show_history_dialog(self.app_state),
                   bootstyle="outline-secondary", width=8).pack(side=tk.RIGHT, padx=4)

        ttk.Button(right_frame, text="Recent Files",
                   command=lambda: show_recent_files_dialog(self.app_state, self.preview_tab.open_pdf),
                   bootstyle="outline-info", width=12).pack(side=tk.RIGHT, padx=4)

        # Active File Banner
        active_bar = ttk.Frame(root)
        active_bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(active_bar, textvariable=self.app_state.active_file_var,
                  font=("Segoe UI", 9, "bold"), bootstyle="info").pack(side=tk.LEFT, padx=2)

        # Progress Bar
        prog_frame = ttk.Frame(root)
        prog_frame.pack(fill=tk.X, pady=(0, 4))
        self._progress_bar = ttk.Progressbar(
            prog_frame, variable=self.app_state.progress_var, maximum=100, bootstyle="success-striped"
        )
        self._progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 8))
        ttk.Label(prog_frame, textvariable=self.app_state.progress_text, font=("Segoe UI", 8)).pack(side=tk.RIGHT)

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(4, 4))

        # Instantiate Fragmented Modular Tabs
        self.preview_tab = PreviewTab(self.notebook, self.app_state)
        self.vmerge_tab = VisualMergeTab(self.notebook, self.app_state)
        self.reorder_tab = ReorderTab(self.notebook, self.app_state)
        self.basic_tab = BasicTab(self.notebook, self.app_state)
        self.advanced_tab = AdvancedTab(self.notebook, self.app_state)
        self.convert_tab = ConvertTab(self.notebook, self.app_state)
        self.security_tab = SecurityTab(self.notebook, self.app_state)
        self.signature_tab = SignatureTab(self.notebook, self.app_state)
        self.batch_tab = BatchTab(self.notebook, self.app_state)
        self.compare_tab = CompareTab(self.notebook, self.app_state)
        self.metadata_tab = MetadataTab(self.notebook, self.app_state)

        # Add tabs to Notebook
        self.notebook.add(self.preview_tab, text="  PDF Preview & Text Edit  ")
        self.notebook.add(self.vmerge_tab, text="  Visual Merge  ")
        self.notebook.add(self.reorder_tab, text="  Visual Reorder  ")
        self.notebook.add(self.basic_tab, text="  Basic  ")
        self.notebook.add(self.advanced_tab, text="  Advanced  ")
        self.notebook.add(self.convert_tab, text="  Convert  ")
        self.notebook.add(self.security_tab, text="  Security  ")
        self.notebook.add(self.signature_tab, text="  Signature  ")
        self.notebook.add(self.batch_tab, text="  Batch Ops  ")
        self.notebook.add(self.compare_tab, text="  Compare  ")
        self.notebook.add(self.metadata_tab, text="  Metadata  ")

        # File Info Panel
        info_frame = ttk.LabelFrame(root, text="File Information")
        info_frame.pack(fill=tk.X, pady=3)
        info_inner = ttk.Frame(info_frame, padding=4)
        info_inner.pack(fill=tk.X)
        self.file_info_text = tk.Text(info_inner, height=3, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9))
        self.file_info_text.pack(fill=tk.X)

        # Status Bar
        status_frame = ttk.Frame(root)
        status_frame.pack(fill=tk.X, pady=(3, 0))
        ttk.Label(status_frame, textvariable=self.app_state.status_var, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttk.Label(status_frame, text="Drop PDF files anywhere!", font=("Segoe UI", 8), bootstyle="secondary").pack(side=tk.RIGHT)

    def _on_undo(self) -> None:
        entry = self.app_state.history.undo_last()
        if entry:
            self.app_state.update_status(f"Undone: {entry['operation']}")
            if os.path.isfile(entry["input_file"]):
                self.preview_tab.open_pdf(entry["input_file"])
            messagebox.showinfo("Undo", f"Reverted: {entry['operation']}\nRestored: {entry['input_file']}")
        else:
            messagebox.showinfo("Undo", "Nothing to undo.")

    def _toggle_dark_mode(self) -> None:
        self._dark_mode = self._dark_mode_var.get()
        new_theme = "darkly" if self._dark_mode else "cosmo"
        self._current_theme = new_theme
        self.window.style.theme_use(new_theme)
        bg = "#2b2b2b" if self._dark_mode else "#f0f0f0"
        self.preview_tab.canvas.config(bg=bg)
        self.compare_tab.canvas_a.config(bg=bg)
        self.compare_tab.canvas_b.config(bg=bg)
        self.app_state.update_status(f"Theme: {new_theme}")

    def _setup_drag_and_drop(self) -> None:
        try:
            from tkinterdnd2 import DND_FILES
            self.window.drop_target_register(DND_FILES)
            self.window.dnd_bind("<<Drop>>", self._on_drop)
            logger.info("Drag-and-drop enabled (tkinterdnd2)")
        except ImportError:
            logger.info("tkinterdnd2 not available — using fallback file dialogs")

    def _on_drop(self, event) -> None:
        files = self.window.tk.splitlist(event.data)
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        img_files = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]

        if pdf_files:
            if len(pdf_files) == 1:
                self.preview_tab.open_pdf(pdf_files[0])
            else:
                self.vmerge_tab.add_files(pdf_files)
                self.notebook.select(1)
                self.app_state.update_status(f"Dropped {len(pdf_files)} PDFs into Visual Merge workspace")

        if img_files:
            if messagebox.askyesno("Images Dropped", f"Convert {len(img_files)} image(s) to PDF?"):
                out = self.app_state.ask_output_file()
                if out:
                    from pdf_editor.operations import extras
                    extras.images_to_pdf(img_files, out)
                    self.app_state.notify_success(f"Created PDF from {len(img_files)} images!")
                    self.preview_tab.open_pdf(out)

    def run(self) -> None:
        try:
            self.window.mainloop()
        finally:
            if self.preview_tab.doc:
                self.preview_tab.doc.close()
            self.app_state.history.cleanup()


def main():
    app = PDFEditorApp()
    app.run()


if __name__ == "__main__":
    main()

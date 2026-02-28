"""PDF Editor 4 All — Graphical User Interface.

Features:
- PDF Preview / Viewer tab
- Drag & Drop file support
- Dark Mode toggle
- Reorder Pages (drag-to-reorder thumbnails)
- Batch Operations
- Image-to-PDF
- Recent Files menu
- Progress Bar for long operations
- Operation History / Undo
- PDF Comparison (side-by-side)
- Metadata Editor
- All original operations (merge, split, extract, rotate, watermark,
  compress, page numbers, header/footer, bookmarks, convert, encrypt,
  decrypt, signature)
"""

from __future__ import annotations

import functools
import logging
import os
import threading
import tkinter as tk
from datetime import datetime
from io import BytesIO
from tkinter import filedialog, messagebox, simpledialog
from typing import Callable, List, Optional

import fitz  # PyMuPDF
import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.constants import *

from pdf_editor import __app_name__, __version__
from pdf_editor.history import OperationHistory, add_recent_file, get_recent_files, clear_recent_files
from pdf_editor.operations import advanced, basic, converter, security, forms
from pdf_editor.operations import extras
from pdf_editor.utils import get_pdf_info, setup_logging

logger = logging.getLogger("pdf_editor.app")

# Available ttkbootstrap themes
LIGHT_THEMES = ["cosmo", "flatly", "journal", "litera", "lumen", "minty", "pulse", "sandstone", "united", "yeti"]
DARK_THEMES = ["cyborg", "darkly", "solar", "superhero", "vapor"]


# ── Decorator for GUI callbacks ─────────────────────────────────────────────

def _gui_action(func):
    """Wrap a GUI callback so exceptions are caught and shown in a dialog."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as exc:
            logger.exception("Error in %s", func.__name__)
            self._update_status(f"Error: {exc}")
            messagebox.showerror("Error", f"An error occurred:\n{exc}")

    return wrapper


# ═════════════════════════════════════════════════════════════════════════════
#  Main Application
# ═════════════════════════════════════════════════════════════════════════════

class PDFEditorApp:
    """Tkinter-based GUI for PDF Editor 4 All."""

    def __init__(self) -> None:
        setup_logging()

        self._dark_mode = False
        self._current_theme = "cosmo"

        self.window = ttk.Window(themename=self._current_theme)
        self.window.title(f"{__app_name__} v{__version__}")
        self.window.geometry("1000x950")
        self.window.minsize(800, 650)

        self.status_var = tk.StringVar(value="Ready")
        self.signature_path: str | None = None
        self.history = OperationHistory()

        # Progress bar variable
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_text = tk.StringVar(value="")

        # Preview state
        self._preview_doc: Optional[fitz.Document] = None
        self._preview_path: str | None = None
        self._preview_page = 1
        self._preview_zoom = 1.0

        self._build_ui()
        self._setup_drag_and_drop()
        self._load_recent_files_menu()

    # ═════════════════════════════════════════════════════════════════════════
    #  UI Construction
    # ═════════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        root = ttk.Frame(self.window, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        # ── Top bar ──────────────────────────────────────────────────────
        top_bar = ttk.Frame(root)
        top_bar.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(top_bar, text=__app_name__, font=("Segoe UI", 20, "bold")).pack(side=tk.LEFT)
        ttk.Label(top_bar, text=f"v{__version__}", font=("Segoe UI", 9),
                  bootstyle="secondary").pack(side=tk.LEFT, padx=(6, 0), anchor=tk.S)

        # Right side: dark mode toggle + undo
        right_frame = ttk.Frame(top_bar)
        right_frame.pack(side=tk.RIGHT)

        self._dark_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            right_frame, text="Dark Mode", variable=self._dark_mode_var,
            command=self._toggle_dark_mode, bootstyle="round-toggle"
        ).pack(side=tk.RIGHT, padx=8)

        ttk.Button(right_frame, text="Undo", command=self._on_undo,
                   bootstyle="outline-secondary", width=6).pack(side=tk.RIGHT, padx=4)

        ttk.Button(right_frame, text="History", command=self._show_history,
                   bootstyle="outline-secondary", width=8).pack(side=tk.RIGHT, padx=4)

        ttk.Button(right_frame, text="Recent Files", command=self._show_recent_files_dialog,
                   bootstyle="outline-info", width=12).pack(side=tk.RIGHT, padx=4)

        # ── Progress bar ─────────────────────────────────────────────────
        prog_frame = ttk.Frame(root)
        prog_frame.pack(fill=tk.X, pady=(0, 4))
        self._progress_bar = ttk.Progressbar(
            prog_frame, variable=self._progress_var, maximum=100, bootstyle="success-striped"
        )
        self._progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 8))
        ttk.Label(prog_frame, textvariable=self._progress_text,
                  font=("Segoe UI", 8)).pack(side=tk.RIGHT)

        # ── Notebook (tabs) ──────────────────────────────────────────────
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(4, 4))

        self._build_preview_tab()
        self._build_basic_tab()
        self._build_advanced_tab()
        self._build_convert_tab()
        self._build_security_tab()
        self._build_forms_tab()
        self._build_batch_tab()
        self._build_reorder_tab()
        self._build_compare_tab()
        self._build_metadata_tab()

        # ── File info ────────────────────────────────────────────────────
        info_frame = ttk.LabelFrame(root, text="File Information", padding=6)
        info_frame.pack(fill=tk.X, pady=3)
        self.file_info_text = tk.Text(info_frame, height=3, wrap=tk.WORD, state=tk.DISABLED,
                                      font=("Consolas", 9))
        self.file_info_text.pack(fill=tk.X)

        # ── Status bar ───────────────────────────────────────────────────
        status_frame = ttk.Frame(root)
        status_frame.pack(fill=tk.X, pady=(3, 0))
        ttk.Label(status_frame, textvariable=self.status_var,
                  font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttk.Label(status_frame, text="Drop PDF files anywhere!",
                  font=("Segoe UI", 8), bootstyle="secondary").pack(side=tk.RIGHT)

    # ── Tab Builders ─────────────────────────────────────────────────────────

    def _btn(self, parent, text, command, style="primary.TButton"):
        ttk.Button(parent, text=text, command=command, style=style).pack(fill=tk.X, pady=2)

    # ─── PDF Preview Tab ─────────────────────────────────────────────────────

    def _build_preview_tab(self):
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="  PDF Preview  ")

        # Controls
        ctrl = ttk.Frame(tab)
        ctrl.pack(fill=tk.X, pady=(0, 4))

        ttk.Button(ctrl, text="Open PDF", command=self._preview_open,
                   bootstyle="primary", width=10).pack(side=tk.LEFT, padx=2)

        ttk.Label(ctrl, text="Page:").pack(side=tk.LEFT, padx=(12, 2))
        self._preview_page_var = tk.IntVar(value=1)
        self._preview_page_spin = ttk.Spinbox(
            ctrl, from_=1, to=1, width=5, textvariable=self._preview_page_var
        )
        self._preview_page_spin.pack(side=tk.LEFT, padx=2)
        self._preview_total_label = ttk.Label(ctrl, text="/ 0")
        self._preview_total_label.pack(side=tk.LEFT, padx=2)

        ttk.Button(ctrl, text="<", command=self._preview_prev, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(ctrl, text=">", command=self._preview_next, width=3).pack(side=tk.LEFT, padx=1)

        ttk.Label(ctrl, text="Zoom:").pack(side=tk.LEFT, padx=(16, 2))
        self._preview_zoom_var = tk.DoubleVar(value=1.0)
        ttk.Scale(ctrl, from_=0.25, to=4.0, variable=self._preview_zoom_var,
                  orient=tk.HORIZONTAL, length=140).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Fit", command=lambda: self._preview_zoom_var.set(1.0),
                   bootstyle="outline", width=4).pack(side=tk.LEFT, padx=2)

        # Canvas
        canvas_frame = ttk.Frame(tab)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        h_sb = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_sb.pack(side=tk.BOTTOM, fill=tk.X)
        v_sb = ttk.Scrollbar(canvas_frame)
        v_sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._preview_canvas = tk.Canvas(
            canvas_frame, bg="#f0f0f0",
            xscrollcommand=h_sb.set, yscrollcommand=v_sb.set
        )
        self._preview_canvas.pack(fill=tk.BOTH, expand=True)
        h_sb.config(command=self._preview_canvas.xview)
        v_sb.config(command=self._preview_canvas.yview)

        # Bind events
        self._preview_page_var.trace_add("write", lambda *_: self._preview_render())
        self._preview_zoom_var.trace_add("write", lambda *_: self._preview_render())

    @_gui_action
    def _preview_open(self, path: str | None = None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        if self._preview_doc:
            self._preview_doc.close()
        self._preview_doc = fitz.open(path)
        self._preview_path = path
        self._preview_page_var.set(1)
        self._preview_page_spin.config(to=self._preview_doc.page_count)
        self._preview_total_label.config(text=f"/ {self._preview_doc.page_count}")
        self._show_file_info(path)
        add_recent_file(path)
        self._update_status(f"Opened: {os.path.basename(path)}")
        self._preview_render()

    def _preview_render(self):
        if not self._preview_doc:
            return
        try:
            page_num = self._preview_page_var.get()
        except tk.TclError:
            return
        if not (1 <= page_num <= self._preview_doc.page_count):
            return

        self._preview_canvas.delete("all")
        zoom = self._preview_zoom_var.get()
        page = self._preview_doc[page_num - 1]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        self._preview_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self._preview_canvas._photo = photo
        self._preview_canvas.config(scrollregion=(0, 0, pix.width, pix.height))

    def _preview_prev(self):
        try:
            p = self._preview_page_var.get()
            if p > 1:
                self._preview_page_var.set(p - 1)
        except tk.TclError:
            pass

    def _preview_next(self):
        if not self._preview_doc:
            return
        try:
            p = self._preview_page_var.get()
            if p < self._preview_doc.page_count:
                self._preview_page_var.set(p + 1)
        except tk.TclError:
            pass

    # ─── Basic Tab ───────────────────────────────────────────────────────────

    def _build_basic_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Basic  ")
        frame = ttk.LabelFrame(tab, text="Common Tasks", padding=10)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Click a button below → you will be prompted to select an input PDF "
                  "and a save location.",
                  font=("Segoe UI", 9), foreground="gray", wraplength=600).pack(anchor=tk.W, pady=(0, 6))

        self._btn(frame, "Merge PDFs", self.on_merge)
        self._btn(frame, "Extract Pages", self.on_extract)
        self._btn(frame, "Rotate PDF", self.on_rotate)
        self._btn(frame, "Add Watermark", self.on_watermark)
        self._btn(frame, "Image(s) to PDF", self.on_images_to_pdf)

        # Hints for each operation
        hints = ttk.LabelFrame(tab, text="What each operation needs", padding=10)
        hints.pack(fill=tk.X, pady=5)
        for txt in [
            "Merge — Select 2+ PDF files → choose save location",
            "Extract — Select a PDF → enter page numbers (e.g. 1,3-5,7) → save",
            "Rotate — Select a PDF → pick angle (90°/180°/270°) → save",
            "Watermark — Select a PDF → select watermark PDF → save",
            "Image(s) to PDF — Select image files → save as PDF",
        ]:
            ttk.Label(hints, text=f"  \u2022 {txt}", font=("Segoe UI", 9)).pack(anchor=tk.W)

    # ─── Advanced Tab ────────────────────────────────────────────────────────

    def _build_advanced_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Advanced  ")

        # ── Compress section with quality selector ──
        comp_frame = ttk.LabelFrame(tab, text="Compress PDF", padding=10)
        comp_frame.pack(fill=tk.X, pady=5)

        ttk.Label(comp_frame, text="Steps: 1) Choose quality → 2) Click Compress → "
                  "3) Select input PDF → 4) Choose save location",
                  font=("Segoe UI", 9), foreground="gray").pack(anchor=tk.W, pady=(0, 6))

        quality_row = ttk.Frame(comp_frame)
        quality_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(quality_row, text="Quality:").pack(side=tk.LEFT, padx=(0, 6))

        self._compress_quality_var = tk.StringVar(value="medium")
        for val, label, tip in [
            ("low",    "Low",    "Fast, lossless — stream compression only"),
            ("medium", "Medium", "Balanced — images resampled to 150 DPI, JPEG 80"),
            ("high",   "High",   "Max compression — images at 96 DPI, JPEG 50"),
        ]:
            rb = ttk.Radiobutton(quality_row, text=label, variable=self._compress_quality_var, value=val)
            rb.pack(side=tk.LEFT, padx=4)

        # Quality description label (updates dynamically)
        self._compress_desc_var = tk.StringVar(value="Balanced — images resampled to 150 DPI, JPEG 80")
        ttk.Label(comp_frame, textvariable=self._compress_desc_var,
                  font=("Segoe UI", 9, "italic"), foreground="gray").pack(anchor=tk.W, pady=(0, 4))
        self._compress_quality_var.trace_add("write", self._on_compress_quality_change)

        self._btn(comp_frame, "Compress PDF", self.on_compress, "info.TButton")

        # ── Other advanced operations ──
        other_frame = ttk.LabelFrame(tab, text="Other Advanced Operations", padding=10)
        other_frame.pack(fill=tk.X, pady=5)

        ttk.Label(other_frame, text="Click a button → follow the prompts to select files and options.",
                  font=("Segoe UI", 9), foreground="gray").pack(anchor=tk.W, pady=(0, 6))

        self._btn(other_frame, "Add Page Numbers", self.on_page_numbers, "info.TButton")
        self._btn(other_frame, "Add Header / Footer", self.on_header_footer, "info.TButton")
        self._btn(other_frame, "Split PDF", self.on_split, "info.TButton")
        self._btn(other_frame, "Manage Bookmarks", self.on_manage_bookmarks, "info.TButton")

    def _on_compress_quality_change(self, *_args):
        descriptions = {
            "low": "Fast, lossless — stream compression only",
            "medium": "Balanced — images resampled to 150 DPI, JPEG 80",
            "high": "Max compression — images at 96 DPI, JPEG 50 (smaller file, lower image quality)",
        }
        self._compress_desc_var.set(descriptions.get(self._compress_quality_var.get(), ""))

    # ─── Convert Tab ─────────────────────────────────────────────────────────

    def _build_convert_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Convert  ")
        frame = ttk.LabelFrame(tab, text="Convert PDF", padding=10)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Select a conversion type → pick the input PDF → choose output location.",
                  font=("Segoe UI", 9), foreground="gray", wraplength=600).pack(anchor=tk.W, pady=(0, 6))

        self._btn(frame, "To Word Document", self.on_pdf_to_word, "success.TButton")
        self._btn(frame, "To Images", self.on_pdf_to_images, "success.TButton")
        self._btn(frame, "To Text File", self.on_pdf_to_text, "success.TButton")

        hints = ttk.LabelFrame(tab, text="What each conversion needs", padding=10)
        hints.pack(fill=tk.X, pady=5)
        for txt in [
            "To Word — Select a PDF → save as .docx",
            "To Images — Select a PDF → choose output folder (one PNG per page)",
            "To Text — Select a PDF → save as .txt",
        ]:
            ttk.Label(hints, text=f"  \u2022 {txt}", font=("Segoe UI", 9)).pack(anchor=tk.W)

    # ─── Security Tab ────────────────────────────────────────────────────────

    def _build_security_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Security  ")
        frame = ttk.LabelFrame(tab, text="Security Options", padding=10)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Encrypt or decrypt PDF files with password protection.",
                  font=("Segoe UI", 9), foreground="gray", wraplength=600).pack(anchor=tk.W, pady=(0, 6))

        self._btn(frame, "Encrypt PDF", self.on_encrypt, "warning.TButton")
        self._btn(frame, "Remove Password", self.on_remove_password, "warning.TButton")

        hints = ttk.LabelFrame(tab, text="What you'll need", padding=10)
        hints.pack(fill=tk.X, pady=5)
        for txt in [
            "Encrypt — Select a PDF → enter a password → save encrypted copy",
            "Remove Password — Select an encrypted PDF → enter current password → save unlocked copy",
        ]:
            ttk.Label(hints, text=f"  \u2022 {txt}", font=("Segoe UI", 9)).pack(anchor=tk.W)

    # ─── Forms & Signature Tab ───────────────────────────────────────────────

    def _build_forms_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Signature  ")
        frame = ttk.LabelFrame(tab, text="Digital Signature", padding=10)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Add a signature image to a specific page of a PDF.",
                  font=("Segoe UI", 9), foreground="gray", wraplength=600).pack(anchor=tk.W, pady=(0, 6))

        self._btn(frame, "Upload Signature Image", self.on_upload_signature, "info.TButton")
        self._btn(frame, "Add Digital Signature", self.on_add_signature, "info.TButton")

        hints = ttk.LabelFrame(tab, text="How to add a signature", padding=10)
        hints.pack(fill=tk.X, pady=5)
        for txt in [
            "Step 1: Upload Signature — Select a PNG/JPG image of your signature",
            "Step 2: Add Signature — Select a PDF → enter page number & position → save",
        ]:
            ttk.Label(hints, text=f"  \u2022 {txt}", font=("Segoe UI", 9)).pack(anchor=tk.W)

    # ─── Batch Operations Tab ────────────────────────────────────────────────

    def _build_batch_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Batch Ops  ")

        ttk.Label(tab, text="Apply an operation to multiple PDF files at once.",
                  font=("Segoe UI", 10)).pack(pady=(0, 8))

        # File list
        list_frame = ttk.LabelFrame(tab, text="Files", padding=8)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        btn_row = ttk.Frame(list_frame)
        btn_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(btn_row, text="Add Files", command=self._batch_add_files,
                   bootstyle="outline").pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Clear", command=self._batch_clear,
                   bootstyle="outline-danger").pack(side=tk.LEFT, padx=2)

        self._batch_listbox = tk.Listbox(list_frame, height=8, selectmode=tk.EXTENDED)
        sb = ttk.Scrollbar(list_frame, command=self._batch_listbox.yview)
        self._batch_listbox.config(yscrollcommand=sb.set)
        self._batch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._batch_files: List[str] = []

        # Operation selector
        op_frame = ttk.LabelFrame(tab, text="Operation", padding=8)
        op_frame.pack(fill=tk.X, pady=4)

        self._batch_op_var = tk.StringVar(value="compress")
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
            ttk.Radiobutton(op_frame, text=label, variable=self._batch_op_var,
                            value=val).pack(anchor=tk.W, pady=1)

        ttk.Button(tab, text="Run Batch Operation", command=self._batch_run,
                   bootstyle="success", width=25).pack(pady=8)

    def _batch_add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for f in files:
            if f not in self._batch_files:
                self._batch_files.append(f)
                self._batch_listbox.insert(tk.END, os.path.basename(f))

    def _batch_clear(self):
        self._batch_files.clear()
        self._batch_listbox.delete(0, tk.END)

    @_gui_action
    def _batch_run(self):
        if not self._batch_files:
            messagebox.showinfo("Info", "Add files first.")
            return
        out_dir = filedialog.askdirectory(title="Select output directory")
        if not out_dir:
            return

        op = self._batch_op_var.get()
        total = len(self._batch_files)

        self._start_progress(f"Batch: {op}")
        errors = []

        for i, f in enumerate(self._batch_files):
            self._set_progress((i / total) * 100, f"Processing {os.path.basename(f)}...")
            base = os.path.splitext(os.path.basename(f))[0]
            try:
                if op == "compress":
                    quality = self._compress_quality_var.get()
                    advanced.compress_pdf(f, os.path.join(out_dir, f"{base}_compressed.pdf"), quality=quality)
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

        self._finish_progress()
        if errors:
            messagebox.showwarning("Batch Complete",
                                   f"Done with {len(errors)} error(s):\n" + "\n".join(errors[:5]))
        else:
            self._success(f"Batch operation complete! {total} files processed.")

    # ─── Reorder Pages Tab ───────────────────────────────────────────────────

    def _build_reorder_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Reorder Pages  ")

        ttk.Label(tab, text="Load a PDF, drag pages to reorder, then save.",
                  font=("Segoe UI", 10)).pack(pady=(0, 6))

        ctrl = ttk.Frame(tab)
        ctrl.pack(fill=tk.X, pady=4)
        ttk.Button(ctrl, text="Load PDF", command=self._reorder_load,
                   bootstyle="primary").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Move Up", command=self._reorder_move_up,
                   bootstyle="outline").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Move Down", command=self._reorder_move_down,
                   bootstyle="outline").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Delete Selected", command=self._reorder_delete,
                   bootstyle="outline-danger").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Save As", command=self._reorder_save,
                   bootstyle="success").pack(side=tk.RIGHT, padx=2)

        self._reorder_listbox = tk.Listbox(tab, height=18, font=("Consolas", 10))
        rsb = ttk.Scrollbar(tab, command=self._reorder_listbox.yview)
        self._reorder_listbox.config(yscrollcommand=rsb.set)
        self._reorder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
        rsb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        self._reorder_file: str | None = None
        self._reorder_order: List[int] = []

    @_gui_action
    def _reorder_load(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        import PyPDF2
        reader = PyPDF2.PdfReader(path)
        total = len(reader.pages)
        self._reorder_file = path
        self._reorder_order = list(range(1, total + 1))
        self._reorder_refresh()
        add_recent_file(path)
        self._show_file_info(path)

    def _reorder_refresh(self):
        self._reorder_listbox.delete(0, tk.END)
        for idx, page in enumerate(self._reorder_order):
            self._reorder_listbox.insert(tk.END, f"  Position {idx + 1}  ←  Original Page {page}")

    def _reorder_move_up(self):
        sel = self._reorder_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self._reorder_order[i], self._reorder_order[i - 1] = (
            self._reorder_order[i - 1], self._reorder_order[i]
        )
        self._reorder_refresh()
        self._reorder_listbox.selection_set(i - 1)

    def _reorder_move_down(self):
        sel = self._reorder_listbox.curselection()
        if not sel or sel[0] >= len(self._reorder_order) - 1:
            return
        i = sel[0]
        self._reorder_order[i], self._reorder_order[i + 1] = (
            self._reorder_order[i + 1], self._reorder_order[i]
        )
        self._reorder_refresh()
        self._reorder_listbox.selection_set(i + 1)

    def _reorder_delete(self):
        sel = self._reorder_listbox.curselection()
        if not sel:
            return
        if len(self._reorder_order) <= 1:
            messagebox.showwarning("Warning", "Cannot delete the last page.")
            return
        for i in reversed(sel):
            self._reorder_order.pop(i)
        self._reorder_refresh()

    @_gui_action
    def _reorder_save(self):
        if not self._reorder_file or not self._reorder_order:
            messagebox.showinfo("Info", "Load a PDF first.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if not out:
            return
        extras.reorder_pages(self._reorder_file, out, self._reorder_order)
        self.history.record("reorder_pages", self._reorder_file, out,
                            f"Order: {self._reorder_order}")
        add_recent_file(out)
        self._success("Pages reordered and saved!")

    # ─── PDF Comparison Tab ──────────────────────────────────────────────────

    def _build_compare_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Compare  ")

        ttk.Label(tab, text="Compare two PDFs side by side.",
                  font=("Segoe UI", 10)).pack(pady=(0, 6))

        ctrl = ttk.Frame(tab)
        ctrl.pack(fill=tk.X, pady=4)

        self._cmp_file_a = tk.StringVar(value="(none)")
        self._cmp_file_b = tk.StringVar(value="(none)")

        ttk.Button(ctrl, text="PDF A", command=lambda: self._cmp_pick("a"),
                   bootstyle="outline").pack(side=tk.LEFT, padx=2)
        ttk.Label(ctrl, textvariable=self._cmp_file_a, font=("Segoe UI", 8),
                  width=30).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="PDF B", command=lambda: self._cmp_pick("b"),
                   bootstyle="outline").pack(side=tk.LEFT, padx=2)
        ttk.Label(ctrl, textvariable=self._cmp_file_b, font=("Segoe UI", 8),
                  width=30).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="Compare", command=self._cmp_run,
                   bootstyle="success").pack(side=tk.RIGHT, padx=2)

        # Page nav
        nav = ttk.Frame(tab)
        nav.pack(fill=tk.X, pady=2)
        ttk.Label(nav, text="Page:").pack(side=tk.LEFT, padx=2)
        self._cmp_page_var = tk.IntVar(value=1)
        self._cmp_page_spin = ttk.Spinbox(nav, from_=1, to=1, width=5,
                                           textvariable=self._cmp_page_var)
        self._cmp_page_spin.pack(side=tk.LEFT, padx=2)
        ttk.Button(nav, text="Show Page", command=self._cmp_show_page,
                   bootstyle="outline", width=10).pack(side=tk.LEFT, padx=4)

        # Side-by-side canvases
        self._cmp_container = ttk.Frame(tab)
        self._cmp_container.pack(fill=tk.BOTH, expand=True, pady=4)

        self._cmp_canvas_a = tk.Canvas(self._cmp_container, bg="#e8e8e8")
        self._cmp_canvas_b = tk.Canvas(self._cmp_container, bg="#e8e8e8")
        self._cmp_canvas_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        self._cmp_canvas_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))

        # Result text
        self._cmp_result = tk.Text(tab, height=3, wrap=tk.WORD, state=tk.DISABLED,
                                    font=("Consolas", 9))
        self._cmp_result.pack(fill=tk.X, pady=4)

        self._cmp_paths = {"a": None, "b": None}

    def _cmp_pick(self, which: str):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self._cmp_paths[which] = path
        name = os.path.basename(path)
        if which == "a":
            self._cmp_file_a.set(name)
        else:
            self._cmp_file_b.set(name)

    @_gui_action
    def _cmp_run(self):
        a, b = self._cmp_paths["a"], self._cmp_paths["b"]
        if not a or not b:
            messagebox.showinfo("Info", "Select both PDFs first.")
            return
        result = extras.compare_pdfs(a, b)

        self._cmp_page_spin.config(to=max(result["pages_a"], result["pages_b"]))
        diffs = result["text_diffs"]

        text = (
            f"PDF A: {result['pages_a']} pages, {result['size_a'] / 1024:.0f} KB  |  "
            f"PDF B: {result['pages_b']} pages, {result['size_b'] / 1024:.0f} KB\n"
            f"Pages with text differences: {len(diffs)}"
        )
        if diffs:
            pages = [str(d["page"]) for d in diffs[:10]]
            text += f"  (pages: {', '.join(pages)}{'...' if len(diffs) > 10 else ''})"

        self._cmp_result.config(state=tk.NORMAL)
        self._cmp_result.delete("1.0", tk.END)
        self._cmp_result.insert("1.0", text)
        self._cmp_result.config(state=tk.DISABLED)

        self._cmp_page_var.set(1)
        self._cmp_show_page()

    @_gui_action
    def _cmp_show_page(self):
        a, b = self._cmp_paths["a"], self._cmp_paths["b"]
        if not a or not b:
            return
        page = self._cmp_page_var.get()
        img_a, img_b = extras.get_comparison_images(a, b, page, zoom=0.8)

        for canvas, img in [(self._cmp_canvas_a, img_a), (self._cmp_canvas_b, img_b)]:
            canvas.delete("all")
            if img:
                photo = ImageTk.PhotoImage(img)
                canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                canvas._photo = photo
                canvas.config(scrollregion=(0, 0, img.width, img.height))
            else:
                canvas.create_text(100, 100, text="(no page)", font=("Segoe UI", 14))

    # ─── Metadata Tab ────────────────────────────────────────────────────────

    def _build_metadata_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Metadata  ")

        ttk.Label(tab, text="View and edit PDF metadata fields.",
                  font=("Segoe UI", 10)).pack(pady=(0, 8))

        ctrl = ttk.Frame(tab)
        ctrl.pack(fill=tk.X, pady=4)
        ttk.Button(ctrl, text="Load PDF", command=self._meta_load,
                   bootstyle="primary").pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Save As", command=self._meta_save,
                   bootstyle="success").pack(side=tk.RIGHT, padx=2)

        fields_frame = ttk.LabelFrame(tab, text="Metadata Fields", padding=10)
        fields_frame.pack(fill=tk.X, pady=6)

        self._meta_entries = {}
        for field in ["title", "author", "subject", "keywords"]:
            row = ttk.Frame(fields_frame)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=f"{field.title()}:", width=10, font=("Segoe UI", 10)).pack(
                side=tk.LEFT
            )
            entry = ttk.Entry(row, font=("Segoe UI", 10))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            self._meta_entries[field] = entry

        self._meta_file: str | None = None

    @_gui_action
    def _meta_load(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self._meta_file = path
        meta = extras.get_metadata(path)
        for field, entry in self._meta_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, meta.get(field, ""))
        add_recent_file(path)
        self._show_file_info(path)
        self._update_status(f"Loaded metadata: {os.path.basename(path)}")

    @_gui_action
    def _meta_save(self):
        if not self._meta_file:
            messagebox.showinfo("Info", "Load a PDF first.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if not out:
            return
        extras.edit_metadata(
            self._meta_file, out,
            title=self._meta_entries["title"].get() or None,
            author=self._meta_entries["author"].get() or None,
            subject=self._meta_entries["subject"].get() or None,
            keywords=self._meta_entries["keywords"].get() or None,
        )
        self.history.record("edit_metadata", self._meta_file, out)
        add_recent_file(out)
        self._success("Metadata saved!")

    # ═════════════════════════════════════════════════════════════════════════
    #  Drag & Drop
    # ═════════════════════════════════════════════════════════════════════════

    def _setup_drag_and_drop(self):
        """Register drag-and-drop handlers using tkinter DnD if available."""
        try:
            # Try tkinterdnd2 if installed
            from tkinterdnd2 import DND_FILES
            self.window.drop_target_register(DND_FILES)
            self.window.dnd_bind("<<Drop>>", self._on_drop)
            logger.info("Drag-and-drop enabled (tkinterdnd2)")
        except ImportError:
            # Fallback: add a manual "Open File" area instead
            logger.info("tkinterdnd2 not available — using file-dialog fallback for drag-and-drop")
            # We still support it through the Open button in Preview tab

    def _on_drop(self, event):
        """Handle dropped files."""
        files = self.window.tk.splitlist(event.data)
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        img_files = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]

        if pdf_files:
            # Open first PDF in preview
            self._preview_open(pdf_files[0])
            # If multiple, add to batch
            if len(pdf_files) > 1:
                for f in pdf_files:
                    if f not in self._batch_files:
                        self._batch_files.append(f)
                        self._batch_listbox.insert(tk.END, os.path.basename(f))
                self.notebook.select(6)  # Batch tab
                self._update_status(f"Dropped {len(pdf_files)} PDFs into batch")

        if img_files:
            # Offer to convert images to PDF
            if messagebox.askyesno("Images Dropped",
                                   f"Convert {len(img_files)} image(s) to PDF?"):
                out = filedialog.asksaveasfilename(defaultextension=".pdf")
                if out:
                    extras.images_to_pdf(img_files, out)
                    self._success(f"Created PDF from {len(img_files)} images!")
                    self._preview_open(out)

    # ═════════════════════════════════════════════════════════════════════════
    #  Dark Mode
    # ═════════════════════════════════════════════════════════════════════════

    def _toggle_dark_mode(self):
        self._dark_mode = self._dark_mode_var.get()
        new_theme = "darkly" if self._dark_mode else "cosmo"
        self._current_theme = new_theme
        self.window.style.theme_use(new_theme)
        # Update canvas backgrounds
        bg = "#2b2b2b" if self._dark_mode else "#f0f0f0"
        self._preview_canvas.config(bg=bg)
        self._cmp_canvas_a.config(bg=bg)
        self._cmp_canvas_b.config(bg=bg)
        self._update_status(f"Theme: {new_theme}")

    # ═════════════════════════════════════════════════════════════════════════
    #  Recent Files
    # ═════════════════════════════════════════════════════════════════════════

    def _load_recent_files_menu(self):
        pass  # Used during init; actual display via dialog

    def _show_recent_files_dialog(self):
        recents = get_recent_files()
        if not recents:
            messagebox.showinfo("Recent Files", "No recent files.")
            return

        win = ttk.Toplevel(self.window)
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
                    self._preview_open(path)
                    self.notebook.select(0)  # Preview tab
                    win.destroy()
                else:
                    messagebox.showwarning("Not Found", f"File no longer exists:\n{path}")

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btn_frame, text="Open", command=open_selected,
                   bootstyle="primary").pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear History",
                   command=lambda: (clear_recent_files(), win.destroy()),
                   bootstyle="outline-danger").pack(side=tk.RIGHT, padx=2)

    # ═════════════════════════════════════════════════════════════════════════
    #  Progress Bar
    # ═════════════════════════════════════════════════════════════════════════

    def _start_progress(self, label: str = "Working..."):
        self._progress_var.set(0)
        self._progress_text.set(label)
        self.window.update_idletasks()

    def _set_progress(self, pct: float, label: str = ""):
        self._progress_var.set(min(pct, 100))
        if label:
            self._progress_text.set(label)
        self.window.update_idletasks()

    def _finish_progress(self):
        self._progress_var.set(100)
        self._progress_text.set("Done")
        self.window.after(2000, lambda: (self._progress_var.set(0), self._progress_text.set("")))

    # ═════════════════════════════════════════════════════════════════════════
    #  Operation History / Undo
    # ═════════════════════════════════════════════════════════════════════════

    def _on_undo(self):
        entry = self.history.undo_last()
        if entry:
            self._update_status(f"Undone: {entry['operation']}")
            messagebox.showinfo("Undo", f"Reverted: {entry['operation']}\nRestored: {entry['output_file']}")
        else:
            messagebox.showinfo("Undo", "Nothing to undo.")

    def _show_history(self):
        entries = self.history.entries
        if not entries:
            messagebox.showinfo("History", "No operations recorded yet.")
            return

        win = ttk.Toplevel(self.window)
        win.title("Operation History")
        win.geometry("600x350")
        win.grab_set()

        cols = ("time", "operation", "input", "output", "details")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
        tree.heading("time", text="Time")
        tree.heading("operation", text="Operation")
        tree.heading("input", text="Input")
        tree.heading("output", text="Output")
        tree.heading("details", text="Details")

        tree.column("time", width=60, stretch=False)
        tree.column("operation", width=110, stretch=False)
        tree.column("input", width=150)
        tree.column("output", width=150)
        tree.column("details", width=120)

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

    # ═════════════════════════════════════════════════════════════════════════
    #  Helpers
    # ═════════════════════════════════════════════════════════════════════════

    def _update_status(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"{ts}  —  {msg}")

    def _show_file_info(self, path: str) -> None:
        try:
            info = get_pdf_info(path)
            text = (
                f"Title: {info['title']}  |  Author: {info['author']}  |  "
                f"Pages: {info['pages']}  |  Created: {info['created']}  |  "
                f"Size: {info['file_size'] / 1024:.1f} KB"
            )
        except Exception:
            text = "Could not read file information."
        self.file_info_text.config(state=tk.NORMAL)
        self.file_info_text.delete("1.0", tk.END)
        self.file_info_text.insert("1.0", text)
        self.file_info_text.config(state=tk.DISABLED)

    def _ask_input(self, title="Select PDF", multiple=False):
        ft = [("PDF files", "*.pdf")]
        if multiple:
            paths = filedialog.askopenfilenames(title=title, filetypes=ft)
            for p in paths:
                add_recent_file(p)
            return paths
        path = filedialog.askopenfilename(title=title, filetypes=ft)
        if path:
            add_recent_file(path)
        return path

    def _ask_output(self, ext=".pdf"):
        return filedialog.asksaveasfilename(defaultextension=ext)

    def _success(self, msg: str) -> None:
        self._update_status(msg)
        messagebox.showinfo("Success", msg)

    # ═════════════════════════════════════════════════════════════════════════
    #  Operation Callbacks — same as before but with history recording
    # ═════════════════════════════════════════════════════════════════════════

    @_gui_action
    def on_merge(self):
        files = self._ask_input("Select PDFs to merge", multiple=True)
        if not files:
            return
        out = self._ask_output()
        if not out:
            return
        self._start_progress("Merging PDFs...")
        basic.merge_pdfs(list(files), out)
        self.history.record("merge", str(files[0]), out, f"{len(files)} files")
        self._finish_progress()
        self._show_file_info(out)
        self._success("PDFs merged successfully!")

    @_gui_action
    def on_extract(self):
        inp = self._ask_input()
        if not inp:
            return
        pages_str = simpledialog.askstring(
            "Extract Pages", "Enter page numbers (e.g. 1,3-5,7):", parent=self.window
        )
        if not pages_str:
            return
        out = self._ask_output()
        if not out:
            return
        basic.extract_pages(inp, out, pages_str)
        self.history.record("extract_pages", inp, out, f"Pages: {pages_str}")
        self._show_file_info(out)
        self._success("Pages extracted successfully!")

    @_gui_action
    def on_rotate(self):
        inp = self._ask_input()
        if not inp:
            return
        angle = simpledialog.askinteger(
            "Rotate PDF", "Enter rotation angle (90, 180, or 270):",
            parent=self.window, minvalue=90, maxvalue=270
        )
        if angle not in (90, 180, 270):
            messagebox.showwarning("Warning", "Angle must be 90, 180, or 270.")
            return
        out = self._ask_output()
        if not out:
            return
        basic.rotate_pdf(inp, out, angle)
        self.history.record("rotate", inp, out, f"{angle}°")
        self._show_file_info(out)
        self._success("PDF rotated successfully!")

    @_gui_action
    def on_watermark(self):
        inp = self._ask_input("Select source PDF")
        if not inp:
            return
        wm = filedialog.askopenfilename(title="Select watermark PDF",
                                         filetypes=[("PDF files", "*.pdf")])
        if not wm:
            return
        out = self._ask_output()
        if not out:
            return
        basic.add_watermark(inp, out, wm)
        self.history.record("watermark", inp, out)
        self._show_file_info(out)
        self._success("Watermark added successfully!")

    @_gui_action
    def on_images_to_pdf(self):
        files = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
        )
        if not files:
            return
        out = self._ask_output()
        if not out:
            return
        self._start_progress("Converting images...")
        extras.images_to_pdf(list(files), out)
        self.history.record("images_to_pdf", str(files[0]), out, f"{len(files)} images")
        self._finish_progress()
        self._preview_open(out)
        self._success(f"Created PDF from {len(files)} images!")

    @_gui_action
    def on_compress(self):
        quality = self._compress_quality_var.get()
        inp = self._ask_input()
        if not inp:
            return
        out = self._ask_output()
        if not out:
            return
        self._start_progress(f"Compressing ({quality})...")
        result = advanced.compress_pdf(inp, out, quality=quality)
        self.history.record("compress", inp, out, f"quality={quality}")
        self._finish_progress()
        self._show_file_info(out)
        self._success(
            f"Compressed [{quality}]! "
            f"{result['original_kb']:.0f} KB → {result['compressed_kb']:.0f} KB "
            f"({result['reduction_pct']:.1f}% smaller)"
        )

    @_gui_action
    def on_page_numbers(self):
        inp = self._ask_input()
        if not inp:
            return
        out = self._ask_output()
        if not out:
            return
        advanced.add_page_numbers(inp, out)
        self.history.record("page_numbers", inp, out)
        self._show_file_info(out)
        self._success("Page numbers added successfully!")

    @_gui_action
    def on_header_footer(self):
        inp = self._ask_input()
        if not inp:
            return
        header = simpledialog.askstring("Header", "Header text (empty for none):", parent=self.window)
        footer = simpledialog.askstring("Footer", "Footer text (empty for none):", parent=self.window)
        if not header and not footer:
            messagebox.showinfo("Info", "No header or footer provided.")
            return
        out = self._ask_output()
        if not out:
            return
        advanced.add_header_footer(inp, out, header_text=header or "", footer_text=footer or "")
        self.history.record("header_footer", inp, out)
        self._show_file_info(out)
        self._success("Header/footer added successfully!")

    @_gui_action
    def on_split(self):
        inp = self._ask_input()
        if not inp:
            return
        out_dir = filedialog.askdirectory(title="Select output directory")
        if not out_dir:
            return
        paths = advanced.split_pdf(inp, out_dir)
        self.history.record("split", inp, out_dir, f"{len(paths)} pages")
        self._success(f"PDF split into {len(paths)} pages!")

    @_gui_action
    def on_manage_bookmarks(self):
        inp = self._ask_input()
        if not inp:
            return
        self._show_file_info(inp)
        existing = advanced.get_bookmarks(inp)

        bm_win = ttk.Toplevel(self.window)
        bm_win.title("Manage Bookmarks")
        bm_win.geometry("520x550")
        bm_win.grab_set()

        ttk.Label(bm_win, text="Existing Bookmarks", font=("Segoe UI", 12, "bold")).pack(pady=(10, 4))

        lb_frame = ttk.Frame(bm_win)
        lb_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        lb = tk.Listbox(lb_frame, height=10)
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
            out = self._ask_output()
            if not out:
                return
            advanced.add_bookmarks(inp, out, bms)
            self.history.record("bookmarks", inp, out, f"{len(bms)} bookmarks")
            self._success(f"Added {len(bms)} bookmarks!")
            bm_win.destroy()

        ttk.Button(bm_win, text="Save Bookmarks", command=save, bootstyle="success").pack(pady=10)

    # ── Convert ──────────────────────────────────────────────────────────────

    @_gui_action
    def on_pdf_to_word(self):
        inp = self._ask_input()
        if not inp:
            return
        out = filedialog.asksaveasfilename(defaultextension=".docx",
                                            filetypes=[("Word files", "*.docx")])
        if not out:
            return
        self._start_progress("Converting to Word...")
        converter.pdf_to_word(inp, out)
        self.history.record("to_word", inp, out)
        self._finish_progress()
        self._success("PDF converted to Word!")

    @_gui_action
    def on_pdf_to_images(self):
        inp = self._ask_input()
        if not inp:
            return
        out_dir = filedialog.askdirectory(title="Output directory for images")
        if not out_dir:
            return
        self._start_progress("Converting to images...")
        paths = converter.pdf_to_images(inp, out_dir)
        self.history.record("to_images", inp, out_dir, f"{len(paths)} pages")
        self._finish_progress()
        self._success(f"Converted {len(paths)} pages to images!")

    @_gui_action
    def on_pdf_to_text(self):
        inp = self._ask_input()
        if not inp:
            return
        out = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt")])
        if not out:
            return
        converter.pdf_to_text(inp, out)
        self.history.record("to_text", inp, out)
        self._success("PDF converted to text!")

    # ── Security ─────────────────────────────────────────────────────────────

    @_gui_action
    def on_encrypt(self):
        inp = self._ask_input()
        if not inp:
            return
        pw = simpledialog.askstring("Encrypt", "Enter password:", show="*", parent=self.window)
        if not pw:
            return
        out = self._ask_output()
        if not out:
            return
        security.encrypt_pdf(inp, out, pw)
        self.history.record("encrypt", inp, out)
        self._show_file_info(out)
        self._success("PDF encrypted!")

    @_gui_action
    def on_remove_password(self):
        inp = self._ask_input()
        if not inp:
            return
        pw = simpledialog.askstring("Decrypt", "Enter current password:", show="*",
                                     parent=self.window)
        if not pw:
            return
        out = self._ask_output()
        if not out:
            return
        security.remove_password(inp, out, pw)
        self.history.record("remove_password", inp, out)
        self._show_file_info(out)
        self._success("Password removed!")

    # ── Signature ────────────────────────────────────────────────────────────

    @_gui_action
    def on_upload_signature(self):
        path = filedialog.askopenfilename(
            title="Select signature image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if path:
            self.signature_path = path
            self._success("Signature image uploaded!")

    @_gui_action
    def on_add_signature(self):
        if not self.signature_path:
            messagebox.showwarning("Warning", "Upload a signature image first!")
            return
        inp = self._ask_input()
        if not inp:
            return
        self._show_file_info(inp)
        self._open_signature_placer(inp)

    def _open_signature_placer(self, input_file: str) -> None:
        sig_win = ttk.Toplevel(self.window)
        sig_win.title("Place Signature")
        sig_win.geometry("920x820")
        sig_win.grab_set()

        doc = fitz.open(input_file)
        sig_win._doc = doc

        ctrl = ttk.Frame(sig_win, padding=6)
        ctrl.pack(fill=tk.X)

        ttk.Label(ctrl, text="Page:").pack(side=tk.LEFT, padx=(0, 4))
        page_var = tk.IntVar(value=1)
        ttk.Spinbox(ctrl, from_=1, to=doc.page_count, width=5,
                    textvariable=page_var).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(ctrl, text="Zoom:").pack(side=tk.LEFT, padx=(0, 4))
        zoom_var = tk.DoubleVar(value=1.0)
        ttk.Scale(ctrl, from_=0.5, to=3.0, variable=zoom_var, orient=tk.HORIZONTAL,
                  length=140).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(ctrl, text="Sig Size:").pack(side=tk.LEFT, padx=(0, 4))
        size_var = tk.DoubleVar(value=1.0)
        ttk.Scale(ctrl, from_=0.1, to=3.0, variable=size_var, orient=tk.HORIZONTAL,
                  length=140).pack(side=tk.LEFT)

        canvas_frame = ttk.Frame(sig_win)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        h_sb = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_sb.pack(side=tk.BOTTOM, fill=tk.X)
        v_sb = ttk.Scrollbar(canvas_frame)
        v_sb.pack(side=tk.RIGHT, fill=tk.Y)
        cv = tk.Canvas(canvas_frame, bg="white", xscrollcommand=h_sb.set, yscrollcommand=v_sb.set)
        cv.pack(fill=tk.BOTH, expand=True)
        h_sb.config(command=cv.xview)
        v_sb.config(command=cv.yview)

        sig_img = Image.open(self.signature_path)
        sig_pos = {"x": 0, "y": 0, "placed": False}

        def redraw(*_):
            try:
                pn = page_var.get()
                if not (1 <= pn <= doc.page_count):
                    return
            except tk.TclError:
                return
            cv.delete("all")
            zoom = zoom_var.get()
            page = doc[pn - 1]
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)
            cv.create_image(0, 0, anchor=tk.NW, image=photo)
            cv._photo = photo
            cv.config(scrollregion=(0, 0, pix.width, pix.height))
            if sig_pos["placed"]:
                sw = int(200 * size_var.get() * zoom)
                sh = int(100 * size_var.get() * zoom)
                sp = sig_img.resize((max(sw, 1), max(sh, 1)))
                sp_photo = ImageTk.PhotoImage(sp)
                cv.create_image(sig_pos["x"], sig_pos["y"], anchor=tk.NW, image=sp_photo)
                cv._sig_photo = sp_photo

        def on_click(event):
            sig_pos["x"] = cv.canvasx(event.x)
            sig_pos["y"] = cv.canvasy(event.y)
            sig_pos["placed"] = True
            redraw()

        def apply_sig():
            if not sig_pos["placed"]:
                messagebox.showwarning("Warning", "Click on PDF to place signature first.")
                return
            out = self._ask_output()
            if not out:
                return
            zoom = zoom_var.get()
            pdf_x = sig_pos["x"] / zoom
            pdf_y = sig_pos["y"] / zoom
            sig_w = 200 * size_var.get()
            sig_h = 100 * size_var.get()
            forms.add_signature_image(
                input_file, out, self.signature_path,
                page_number=page_var.get(),
                x=pdf_x, y=pdf_y, width=sig_w, height=sig_h,
            )
            self.history.record("signature", input_file, out, f"Page {page_var.get()}")
            self._success("Signature added!")
            doc.close()
            sig_win.destroy()

        cv.bind("<Button-1>", on_click)
        page_var.trace_add("write", redraw)
        zoom_var.trace_add("write", redraw)
        size_var.trace_add("write", redraw)

        btn_frame = ttk.Frame(sig_win, padding=6)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Apply Signature", command=apply_sig,
                   bootstyle="success").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel",
                   command=lambda: (doc.close(), sig_win.destroy()),
                   bootstyle="secondary").pack(side=tk.RIGHT, padx=4)

        sig_win.protocol("WM_DELETE_WINDOW", lambda: (doc.close(), sig_win.destroy()))
        redraw()

    # ═════════════════════════════════════════════════════════════════════════
    #  Run
    # ═════════════════════════════════════════════════════════════════════════

    def run(self) -> None:
        try:
            self.window.mainloop()
        finally:
            if self._preview_doc:
                self._preview_doc.close()
            self.history.cleanup()


def main():
    app = PDFEditorApp()
    app.run()


if __name__ == "__main__":
    main()

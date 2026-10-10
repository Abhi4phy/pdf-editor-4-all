"""PDF Preview & In-Place Text Editing Tab."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Optional

import fitz  # PyMuPDF
import ttkbootstrap as ttk
from PIL import Image, ImageTk

from pdf_editor.operations import extras

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState

logger = logging.getLogger("pdf_editor.gui.preview")


class PreviewTab(ttk.Frame):
    """PDF Viewer with Live In-Place Text Editing, Font Formatting (Bold, Italic, Strikethrough/Cross), Font Size selection, and Mouse Scroll."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=8)
        self.app_state = app_state

        self.doc: Optional[fitz.Document] = None
        self.doc_path: str | None = None
        self.is_modified = False

        self.zoom_var = tk.DoubleVar(value=1.0)
        self.page_var = tk.IntVar(value=1)

        # In-place text edit state
        self.text_edit_mode_var = tk.BooleanVar(value=False)
        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.font_size_var = tk.StringVar(value="Auto")
        self.bold_var = tk.BooleanVar(value=False)
        self.italic_var = tk.BooleanVar(value=False)
        self.cross_var = tk.BooleanVar(value=False)
        self.unsaved_status_var = tk.StringVar(value="")
        self.rect_start = None
        self.rect_id = None

        self._build_ui()

    def _build_ui(self) -> None:
        # Card 1: Navigation & Save Bar
        nav_card = ttk.LabelFrame(self, text="Document Navigation & Export")
        nav_card.pack(fill=tk.X, pady=(0, 4), padx=2)

        ctrl1 = ttk.Frame(nav_card, padding=4)
        ctrl1.pack(fill=tk.X)

        ttk.Button(
            ctrl1, text="📂 Open PDF (Ctrl+O)", command=self.open_pdf,
            bootstyle="primary", width=17
        ).pack(side=tk.LEFT, padx=2)

        self.save_btn = ttk.Button(
            ctrl1, text="💾 Save PDF As...", command=self.save_pdf,
            bootstyle="success", width=15
        )
        self.save_btn.pack(side=tk.LEFT, padx=2)

        ttk.Label(ctrl1, textvariable=self.unsaved_status_var, font=("Segoe UI", 9, "bold"), foreground="orange").pack(side=tk.LEFT, padx=6)

        ttk.Separator(ctrl1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(ctrl1, text="Page:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(4, 2))
        self.page_spin = ttk.Spinbox(
            ctrl1, from_=1, to=1, width=4, textvariable=self.page_var
        )
        self.page_spin.pack(side=tk.LEFT, padx=2)
        self.total_label = ttk.Label(ctrl1, text="/ 0", font=("Segoe UI", 9))
        self.total_label.pack(side=tk.LEFT, padx=2)

        ttk.Button(ctrl1, text="◀", command=self.prev_page, width=3, bootstyle="outline").pack(side=tk.LEFT, padx=1)
        ttk.Button(ctrl1, text="▶", command=self.next_page, width=3, bootstyle="outline").pack(side=tk.LEFT, padx=1)

        ttk.Separator(ctrl1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(ctrl1, text="Zoom:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(4, 2))
        ttk.Scale(
            ctrl1, from_=0.25, to=4.0, variable=self.zoom_var,
            orient=tk.HORIZONTAL, length=120
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(ctrl1, text="Fit", command=lambda: self.zoom_var.set(1.0),
                   bootstyle="outline", width=4).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl1, text="➕", command=self.zoom_in, width=3, bootstyle="outline").pack(side=tk.LEFT, padx=1)
        ttk.Button(ctrl1, text="➖", command=self.zoom_out, width=3, bootstyle="outline").pack(side=tk.LEFT, padx=1)

        # Card 2: In-Place Text Editing Bar with Font Size & Style Options
        ctrl2 = ttk.LabelFrame(self, text="✍️ Live In-Place Text Editor & Font Options")
        ctrl2.pack(fill=tk.X, pady=(2, 4), padx=2)

        inner2 = ttk.Frame(ctrl2, padding=4)
        inner2.pack(fill=tk.X)

        ttk.Label(inner2, text="Find:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(4, 2))
        ttk.Entry(inner2, textvariable=self.find_var, width=12).pack(side=tk.LEFT, padx=2)

        ttk.Label(inner2, text="Replace:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(6, 2))
        ttk.Entry(inner2, textvariable=self.replace_var, width=12).pack(side=tk.LEFT, padx=2)

        ttk.Label(inner2, text="Size:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(6, 2))
        self.font_size_combo = ttk.Combobox(
            inner2, textvariable=self.font_size_var,
            values=["Auto", "8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48", "72"],
            width=5
        )
        self.font_size_combo.pack(side=tk.LEFT, padx=2)

        # Formatting Toggles
        ttk.Checkbutton(inner2, text="B", variable=self.bold_var, bootstyle="outline-toolbutton", width=3).pack(side=tk.LEFT, padx=1)
        ttk.Checkbutton(inner2, text="I", variable=self.italic_var, bootstyle="outline-toolbutton", width=3).pack(side=tk.LEFT, padx=1)
        ttk.Checkbutton(inner2, text="S̶", variable=self.cross_var, bootstyle="outline-toolbutton", width=3).pack(side=tk.LEFT, padx=1)

        ttk.Button(
            inner2, text="⚡ Preview Replace", command=self.on_in_place_replace,
            bootstyle="warning", width=16
        ).pack(side=tk.LEFT, padx=6)

        ttk.Checkbutton(
            inner2, text="✎ Drag & Edit Region",
            variable=self.text_edit_mode_var, bootstyle="outline-toolbutton"
        ).pack(side=tk.LEFT, padx=6)

        ttk.Label(
            inner2, text="(Exact baseline alignment)",
            font=("Segoe UI", 8, "italic"), bootstyle="info"
        ).pack(side=tk.RIGHT, padx=4)

        # Canvas Frame
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        h_sb = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_sb.pack(side=tk.BOTTOM, fill=tk.X)
        v_sb = ttk.Scrollbar(canvas_frame)
        v_sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(
            canvas_frame, bg="#f0f0f0",
            xscrollcommand=h_sb.set, yscrollcommand=v_sb.set
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        h_sb.config(command=self.canvas.xview)
        v_sb.config(command=self.canvas.yview)

        # Mouse & Canvas Event Bindings
        self._bind_events()

        self.page_var.trace_add("write", lambda *_: self.render_page())
        self.zoom_var.trace_add("write", lambda *_: self.render_page())

    def _bind_events(self) -> None:
        """Bind mouse wheel scrolling, zooming, and canvas selection."""
        # Canvas Drag & Select
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Mouse wheel vertical scrolling
        self.canvas.bind("<MouseWheel>", self._on_canvas_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))

        # Shift + Mouse wheel horizontal scrolling
        self.canvas.bind("<Shift-MouseWheel>", self._on_canvas_shift_mousewheel)

        # Ctrl + Mouse wheel zoom
        self.canvas.bind("<Control-MouseWheel>", self._on_canvas_ctrl_mousewheel)

        # Focus canvas on mouse enter so scrolling works immediately
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())

    def open_pdf(self, path: str | None = None) -> None:
        if not path:
            path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return

        if self.doc:
            self.doc.close()

        try:
            self.doc = fitz.open(path)
            self.doc_path = path
            self.is_modified = False
            self.unsaved_status_var.set("")
            self.app_state.set_active_file(path)

            self.page_var.set(1)
            self.page_spin.config(to=self.doc.page_count)
            self.total_label.config(text=f"/ {self.doc.page_count}")
            self.app_state.update_status(f"Opened: {os.path.basename(path)}")
            self.render_page()
            self.canvas.focus_set()
        except Exception as exc:
            logger.exception("Failed to open PDF")
            messagebox.showerror("Open Error", f"Could not open PDF file:\n{exc}")

    def render_page(self) -> None:
        if not self.doc:
            return
        try:
            p_num = self.page_var.get()
        except tk.TclError:
            return

        if not (1 <= p_num <= self.doc.page_count):
            return

        self.canvas.delete("all")
        zoom = self.zoom_var.get()
        page = self.doc[p_num - 1]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas._photo = photo
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))

    def zoom_in(self) -> None:
        v = self.zoom_var.get()
        self.zoom_var.set(min(round(v + 0.25, 2), 4.0))

    def zoom_out(self) -> None:
        v = self.zoom_var.get()
        self.zoom_var.set(max(round(v - 0.25, 2), 0.25))

    def prev_page(self) -> None:
        try:
            p = self.page_var.get()
            if p > 1:
                self.page_var.set(p - 1)
        except tk.TclError:
            pass

    def next_page(self) -> None:
        if not self.doc:
            return
        try:
            p = self.page_var.get()
            if p < self.doc.page_count:
                self.page_var.set(p + 1)
        except tk.TclError:
            pass

    def _on_canvas_mousewheel(self, event) -> None:
        """Vertical scrolling via mouse wheel."""
        if hasattr(event, "delta") and event.delta:
            units = -2 if event.delta > 0 else 2
            self.canvas.yview_scroll(units, "units")

    def _on_canvas_shift_mousewheel(self, event) -> None:
        """Horizontal scrolling via Shift + mouse wheel."""
        if hasattr(event, "delta") and event.delta:
            units = -2 if event.delta > 0 else 2
            self.canvas.xview_scroll(units, "units")

    def _on_canvas_ctrl_mousewheel(self, event) -> None:
        """Zooming via Ctrl + mouse wheel."""
        if hasattr(event, "delta") and event.delta:
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def _on_canvas_press(self, event) -> None:
        if not self.text_edit_mode_var.get():
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.rect_start = (x, y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

    def _on_canvas_drag(self, event) -> None:
        if not self.text_edit_mode_var.get() or not self.rect_start:
            return
        x0, y0 = self.rect_start
        x1 = self.canvas.canvasx(event.x)
        y1 = self.canvas.canvasy(event.y)

        if self.rect_id:
            self.canvas.coords(self.rect_id, x0, y0, x1, y1)
        else:
            self.rect_id = self.canvas.create_rectangle(
                x0, y0, x1, y1, outline="red", width=2, dash=(4, 4)
            )

    def _on_canvas_release(self, event) -> None:
        if not self.text_edit_mode_var.get() or not self.doc or not self.doc_path:
            return
        if not self.rect_start:
            return

        x0, y0 = self.rect_start
        x1 = self.canvas.canvasx(event.x)
        y1 = self.canvas.canvasy(event.y)
        self.rect_start = None

        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

        if abs(x1 - x0) < 6 or abs(y1 - y0) < 6:
            return

        zoom = self.zoom_var.get()
        pdf_rect = (
            min(x0, x1) / zoom,
            min(y0, y1) / zoom,
            max(x0, x1) / zoom,
            max(y0, y1) / zoom,
        )

        p_num = self.page_var.get()
        page = self.doc[p_num - 1]
        existing_text = page.get_text("text", clip=fitz.Rect(pdf_rect))

        self._open_in_place_edit_dialog(p_num, pdf_rect, existing_text)

    def _open_in_place_edit_dialog(self, page_num: int, pdf_rect: tuple, existing_text: str) -> None:
        page = self.doc[page_num - 1]
        r = fitz.Rect(pdf_rect)

        # Inspect existing text spans to extract baseline origin & font size
        clip_dict = page.get_text("dict", clip=r)
        detected_size = 11.0
        origin_y = None

        if clip_dict and "blocks" in clip_dict:
            for b in clip_dict["blocks"]:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            if s.get("text", "").strip():
                                detected_size = round(s["size"], 1)
                                origin_y = s["origin"][1]
                                break
                        if origin_y is not None:
                            break
                if origin_y is not None:
                    break

        win = ttk.Toplevel(self.app_state.window)
        win.title(f"In-Place Text Editor — Page {page_num}")
        win.geometry("560x460")
        win.grab_set()

        ttk.Label(win, text=f"Edit Text Region (Page {page_num})", font=("Segoe UI", 12, "bold")).pack(pady=(10, 4))

        # Font Formatting Options Row
        fmt_row = ttk.Frame(win, padding=(10, 0))
        fmt_row.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(fmt_row, text="Text Size:").pack(side=tk.LEFT, padx=(0, 4))
        font_size_combo = ttk.Combobox(
            fmt_row, values=["Auto", "8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48", "72"],
            width=5
        )
        display_sz_str = str(int(detected_size)) if (isinstance(detected_size, float) and detected_size.is_integer()) else str(detected_size)
        font_size_combo.set(display_sz_str)
        font_size_combo.pack(side=tk.LEFT, padx=4)

        dlg_bold_var = tk.BooleanVar(value=self.bold_var.get())
        dlg_italic_var = tk.BooleanVar(value=self.italic_var.get())
        dlg_cross_var = tk.BooleanVar(value=self.cross_var.get())

        ttk.Checkbutton(fmt_row, text="B", variable=dlg_bold_var, bootstyle="outline-toolbutton", width=3).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(fmt_row, text="I", variable=dlg_italic_var, bootstyle="outline-toolbutton", width=3).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(fmt_row, text="S̶", variable=dlg_cross_var, bootstyle="outline-toolbutton", width=3).pack(side=tk.LEFT, padx=2)

        ttk.Label(
            win,
            text="Original text in box is erased and replaced in-place at exact baseline origin.",
            font=("Segoe UI", 9), bootstyle="info"
        ).pack(pady=(0, 4))

        is_dark = (ttk.Style().theme.name == "darkly")
        tb = tk.Text(
            win, height=10, font=("Consolas", 10), wrap=tk.WORD,
            bg="#1e1e1e" if is_dark else "#ffffff",
            fg="#ffffff" if is_dark else "#000000",
            insertbackground="#ffffff" if is_dark else "#000000"
        )
        tb.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        tb.insert("1.0", existing_text.strip())

        btn_frame = ttk.Frame(win, padding=8)
        btn_frame.pack(fill=tk.X)

        def apply_preview():
            new_txt = tb.get("1.0", tk.END).strip()
            sz_val = font_size_combo.get()
            try:
                final_sz = float(sz_val) if (sz_val and sz_val != "Auto") else detected_size
            except ValueError:
                final_sz = detected_size

            fontname = extras._resolve_font_name(bold=dlg_bold_var.get(), italic=dlg_italic_var.get())
            strikethrough = dlg_cross_var.get()

            # 1. Erase old vector text stream in-memory
            page.add_redact_annot(r, fill=(1, 1, 1))
            page.apply_redactions()

            # 2. Insert new text at exact baseline origin
            if new_txt:
                lines = new_txt.split("\n")
                start_y = origin_y if origin_y is not None else (r.y0 + final_sz * 0.85)
                for i, line in enumerate(lines):
                    if line:
                        line_y = start_y + i * (final_sz * 1.25)
                        page.insert_text((r.x0, line_y), line, fontsize=final_sz, fontname=fontname, color=(0, 0, 0))
                        if strikethrough:
                            text_w = fitz.get_text_length(line, fontname=fontname, fontsize=final_sz)
                            y_mid = line_y - final_sz * 0.35
                            page.draw_line((r.x0, y_mid), (r.x0 + text_w, y_mid), color=(0, 0, 0), width=1.5)

            self.is_modified = True
            self.unsaved_status_var.set("* Unsaved Edits")
            self.render_page()
            self.app_state.update_status(f"Edited page {page_num} in preview. Click 'Save PDF As...' to save.")
            win.destroy()

        ttk.Button(btn_frame, text="Apply Preview Edit", command=apply_preview, bootstyle="warning").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy, bootstyle="secondary").pack(side=tk.RIGHT, padx=4)

    def on_in_place_replace(self) -> None:
        if not self.doc:
            messagebox.showinfo("Info", "Open a PDF first.")
            return

        find_str = self.find_var.get().strip()
        replace_str = self.replace_var.get()
        if not find_str:
            messagebox.showwarning("Warning", "Enter text to find.")
            return

        font_sz_val = self.font_size_var.get()
        custom_size = None
        if font_sz_val and font_sz_val != "Auto":
            try:
                custom_size = float(font_sz_val)
            except ValueError:
                pass

        bold = self.bold_var.get()
        italic = self.italic_var.get()
        strikethrough = self.cross_var.get()
        fontname = extras._resolve_font_name(bold=bold, italic=italic)

        total_replaced = 0
        for page in self.doc:
            rects = page.search_for(find_str)
            if not rects:
                continue

            replacements = []
            for rect in rects:
                clip_dict = page.get_text("dict", clip=rect)
                detected_size = 11.0
                origin_y = None

                if clip_dict and "blocks" in clip_dict:
                    for b in clip_dict["blocks"]:
                        if "lines" in b:
                            for l in b["lines"]:
                                for s in l["spans"]:
                                    if s.get("text", "").strip():
                                        detected_size = s["size"]
                                        origin_y = s["origin"][1]
                                        break
                                if origin_y is not None:
                                    break
                        if origin_y is not None:
                            break

                final_size = custom_size if custom_size else detected_size
                final_y = origin_y if origin_y is not None else (rect.y0 + final_size * 0.85)
                replacements.append((rect, rect.x0, final_y, final_size))

            # Apply redactions to erase original text stream
            for rect, _, _, _ in replacements:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

            # Insert replacement text at exact baseline origin
            for _, x_pos, y_pos, f_sz in replacements:
                page.insert_text((x_pos, y_pos), replace_str, fontsize=f_sz, fontname=fontname, color=(0, 0, 0))
                if strikethrough and replace_str:
                    text_w = fitz.get_text_length(replace_str, fontname=fontname, fontsize=f_sz)
                    y_mid = y_pos - f_sz * 0.35
                    page.draw_line((x_pos, y_mid), (x_pos + text_w, y_mid), color=(0, 0, 0), width=1.5)
                total_replaced += 1

        if total_replaced == 0:
            messagebox.showinfo("In-Place Replace", f"No instances of '{find_str}' found in document.")
            return

        self.is_modified = True
        self.unsaved_status_var.set("* Unsaved Edits")
        self.render_page()
        self.app_state.update_status(
            f"Replaced {total_replaced} instance(s) of '{find_str}' in preview. Click 'Save PDF As...' to export."
        )

    def save_pdf(self) -> None:
        if not self.doc:
            messagebox.showinfo("Info", "Open a PDF first.")
            return

        out = self.app_state.ask_output_file()
        if not out:
            return

        try:
            self.doc.save(out)
            self.app_state.history.record("save_pdf", self.doc_path or out, out, details="Exported edited PDF")
            self.is_modified = False
            self.unsaved_status_var.set("")
            self.app_state.set_active_file(out)
            self.app_state.notify_success(f"PDF saved successfully -> {os.path.basename(out)}")
        except Exception as exc:
            logger.exception("Failed to save PDF")
            messagebox.showerror("Save Error", f"Could not save PDF:\n{exc}")

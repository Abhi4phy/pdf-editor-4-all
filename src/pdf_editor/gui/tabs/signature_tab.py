"""Digital Signature Placement Tab."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import fitz
import ttkbootstrap as ttk
from PIL import Image, ImageTk

from pdf_editor.operations import forms

if TYPE_CHECKING:
    from pdf_editor.gui.state import AppState


class SignatureTab(ttk.Frame):
    """Tab for adding signature images to PDFs."""

    def __init__(self, parent: ttk.Notebook, app_state: AppState) -> None:
        super().__init__(parent, padding=10)
        self.app_state = app_state
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.LabelFrame(self, text="Digital Signature")
        frame.pack(fill=tk.X, pady=5)

        inner = ttk.Frame(frame, padding=10)
        inner.pack(fill=tk.X)

        ttk.Button(inner, text="Upload Signature Image", command=self.on_upload_signature, style="info.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(inner, text="Add Digital Signature", command=self.on_add_signature, style="info.TButton").pack(fill=tk.X, pady=2)

    def on_upload_signature(self) -> None:
        path = filedialog.askopenfilename(
            title="Select signature image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if path:
            self.app_state.signature_path = path
            self.app_state.notify_success("Signature image uploaded!")

    def on_add_signature(self) -> None:
        if not self.app_state.signature_path:
            messagebox.showwarning("Warning", "Upload a signature image first!")
            return
        inp = self.app_state.get_input_file("Select PDF for Signature")
        if not inp:
            return
        self._open_signature_placer(inp)

    def _open_signature_placer(self, input_file: str) -> None:
        sig_win = ttk.Toplevel(self.app_state.window)
        sig_win.title("Place Signature")
        sig_win.geometry("920x820")
        sig_win.grab_set()

        doc = fitz.open(input_file)
        ctrl = ttk.Frame(sig_win, padding=6)
        ctrl.pack(fill=tk.X)

        ttk.Label(ctrl, text="Page:").pack(side=tk.LEFT, padx=(0, 4))
        page_var = tk.IntVar(value=1)
        ttk.Spinbox(ctrl, from_=1, to=doc.page_count, width=5, textvariable=page_var).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(ctrl, text="Zoom:").pack(side=tk.LEFT, padx=(0, 4))
        zoom_var = tk.DoubleVar(value=1.0)
        ttk.Scale(ctrl, from_=0.5, to=3.0, variable=zoom_var, orient=tk.HORIZONTAL, length=140).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(ctrl, text="Sig Size:").pack(side=tk.LEFT, padx=(0, 4))
        size_var = tk.DoubleVar(value=1.0)
        ttk.Scale(ctrl, from_=0.1, to=3.0, variable=size_var, orient=tk.HORIZONTAL, length=140).pack(side=tk.LEFT)

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

        sig_img = Image.open(self.app_state.signature_path)
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
            out = self.app_state.ask_output_file()
            if not out:
                return
            zoom = zoom_var.get()
            pdf_x = sig_pos["x"] / zoom
            pdf_y = sig_pos["y"] / zoom
            sig_w = 200 * size_var.get()
            sig_h = 100 * size_var.get()
            forms.add_signature_image(
                input_file, out, self.app_state.signature_path,
                page_number=page_var.get(),
                x=pdf_x, y=pdf_y, width=sig_w, height=sig_h,
            )
            self.app_state.history.record("signature", input_file, out, f"Page {page_var.get()}")
            self.app_state.set_active_file(out)
            self.app_state.notify_success("Signature added!")
            doc.close()
            sig_win.destroy()

        cv.bind("<Button-1>", on_click)
        page_var.trace_add("write", redraw)
        zoom_var.trace_add("write", redraw)
        size_var.trace_add("write", redraw)

        btn_frame = ttk.Frame(sig_win, padding=6)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Apply Signature", command=apply_sig, bootstyle="success").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=lambda: (doc.close(), sig_win.destroy()), bootstyle="secondary").pack(side=tk.RIGHT, padx=4)

        sig_win.protocol("WM_DELETE_WINDOW", lambda: (doc.close(), sig_win.destroy()))
        redraw()


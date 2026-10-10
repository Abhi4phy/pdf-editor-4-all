"""Image-to-PDF, reorder pages, metadata editing, and PDF comparison."""

from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import Dict, List, Optional

import fitz  # PyMuPDF
import pikepdf
import PyPDF2
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas

from pdf_editor.utils import ensure_output_dir, validate_input_file

logger = logging.getLogger("pdf_editor.extras")


# ── Image to PDF ─────────────────────────────────────────────────────────────

@ensure_output_dir
def images_to_pdf(image_paths: List[str], output_file: str, page_size: str = "auto") -> str:
    """Convert one or more images into a single PDF.

    Parameters
    ----------
    image_paths : list[str]
        Paths to image files (PNG, JPG, BMP, etc.).
    output_file : str
        Destination PDF path.
    page_size : str
        ``'auto'`` (match each image), ``'letter'``, or ``'a4'``.
    """
    if not image_paths:
        raise ValueError("No image files provided.")

    for p in image_paths:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Image not found: {p}")

    doc = fitz.open()
    try:
        for img_path in image_paths:
            img = Image.open(img_path)
            img_rgb = img.convert("RGB")

            buf = BytesIO()
            img_rgb.save(buf, format="PNG")
            buf.seek(0)

            img_doc = fitz.open(stream=buf.read(), filetype="png")
            pdf_bytes = img_doc.convert_to_pdf()
            img_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

            doc.insert_pdf(img_pdf)
            img_doc.close()
            img_pdf.close()

        doc.save(output_file)
    finally:
        doc.close()

    logger.info("Created PDF from %d images → %s", len(image_paths), output_file)
    return output_file


# ── Reorder Pages ────────────────────────────────────────────────────────────

@validate_input_file
@ensure_output_dir
def reorder_pages(input_file: str, output_file: str, new_order: List[int]) -> str:
    """Reorder pages of a PDF.

    Parameters
    ----------
    new_order : list[int]
        List of 1-based page numbers in the desired order.
        Example: ``[3, 1, 2]`` puts page 3 first.
    """
    reader = PyPDF2.PdfReader(input_file)
    writer = PyPDF2.PdfWriter()
    total = len(reader.pages)

    for page_num in new_order:
        if not (1 <= page_num <= total):
            raise ValueError(f"Invalid page number {page_num}. PDF has {total} pages.")
        writer.add_page(reader.pages[page_num - 1])

    with open(output_file, "wb") as f:
        writer.write(f)

    logger.info("Reordered %d pages → %s", len(new_order), output_file)
    return output_file


# ── Delete Pages ─────────────────────────────────────────────────────────────

@validate_input_file
@ensure_output_dir
def delete_pages(input_file: str, output_file: str, pages_to_delete: List[int]) -> str:
    """Delete specific pages from a PDF.

    Parameters
    ----------
    pages_to_delete : list[int]
        1-based page numbers to remove.
    """
    reader = PyPDF2.PdfReader(input_file)
    writer = PyPDF2.PdfWriter()
    total = len(reader.pages)
    delete_set = set(pages_to_delete)

    kept = 0
    for idx in range(total):
        if (idx + 1) not in delete_set:
            writer.add_page(reader.pages[idx])
            kept += 1

    if kept == 0:
        raise ValueError("Cannot delete all pages.")

    with open(output_file, "wb") as f:
        writer.write(f)

    logger.info("Deleted %d pages, kept %d → %s", len(delete_set), kept, output_file)
    return output_file


# ── Metadata Editor ──────────────────────────────────────────────────────────

def get_metadata(input_file: str) -> Dict[str, str]:
    """Read PDF metadata fields."""
    with pikepdf.Pdf.open(input_file) as pdf:
        info = pdf.docinfo
        return {
            "title": str(info.get("/Title", "")),
            "author": str(info.get("/Author", "")),
            "subject": str(info.get("/Subject", "")),
            "keywords": str(info.get("/Keywords", "")),
            "creator": str(info.get("/Creator", "")),
            "producer": str(info.get("/Producer", "")),
        }


@validate_input_file
@ensure_output_dir
def edit_metadata(
    input_file: str,
    output_file: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[str] = None,
) -> str:
    """Edit PDF metadata fields."""
    with pikepdf.Pdf.open(input_file) as pdf:
        with pdf.open_metadata() as meta:
            if title is not None:
                meta["dc:title"] = title
            if author is not None:
                meta["dc:creator"] = [author]
            if subject is not None:
                meta["dc:description"] = subject
            if keywords is not None:
                meta["pdf:Keywords"] = keywords

        pdf.save(output_file)

    logger.info("Metadata updated → %s", output_file)
    return output_file


# ── PDF Comparison ───────────────────────────────────────────────────────────

def compare_pdfs(file_a: str, file_b: str) -> dict:
    """Compare two PDFs and return a summary of differences.

    Returns
    -------
    dict
        Keys: ``pages_a``, ``pages_b``, ``text_diffs`` (list of page-level diff info).
    """
    doc_a = fitz.open(file_a)
    doc_b = fitz.open(file_b)

    result = {
        "pages_a": doc_a.page_count,
        "pages_b": doc_b.page_count,
        "size_a": os.path.getsize(file_a),
        "size_b": os.path.getsize(file_b),
        "text_diffs": [],
    }

    max_pages = max(doc_a.page_count, doc_b.page_count)
    for i in range(max_pages):
        text_a = doc_a[i].get_text() if i < doc_a.page_count else ""
        text_b = doc_b[i].get_text() if i < doc_b.page_count else ""

        if text_a != text_b:
            result["text_diffs"].append({
                "page": i + 1,
                "in_a": i < doc_a.page_count,
                "in_b": i < doc_b.page_count,
                "chars_a": len(text_a),
                "chars_b": len(text_b),
            })

    doc_a.close()
    doc_b.close()

    logger.info("Compared %s vs %s — %d page diffs", file_a, file_b, len(result["text_diffs"]))
    return result


def get_comparison_images(file_a: str, file_b: str, page: int, zoom: float = 1.0):
    """Get rendered images of a specific page from both PDFs for visual comparison.

    Returns
    -------
    tuple[PIL.Image, PIL.Image | None]
    """
    doc_a = fitz.open(file_a)
    doc_b = fitz.open(file_b)

    mat = fitz.Matrix(zoom, zoom)

    img_a = None
    img_b = None

    if page - 1 < doc_a.page_count:
        pix = doc_a[page - 1].get_pixmap(matrix=mat)
        img_a = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    if page - 1 < doc_b.page_count:
        pix = doc_b[page - 1].get_pixmap(matrix=mat)
        img_b = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    doc_a.close()
    doc_b.close()

    return img_a, img_b


# ── In-Place Text Editing ───────────────────────────────────────────────────

def _resolve_font_name(bold: bool = False, italic: bool = False) -> str:
    if bold and italic:
        return "Helvetica-BoldOblique"
    elif bold:
        return "Helvetica-Bold"
    elif italic:
        return "Helvetica-Oblique"
    return "Helvetica"


@validate_input_file
@ensure_output_dir
def replace_text_in_pdf(
    input_file: str,
    output_file: str,
    search_str: str,
    replace_str: str,
    page_num: Optional[int] = None,
    font_size: Optional[float] = None,
    bold: bool = False,
    italic: bool = False,
    strikethrough: bool = False,
    font_color: tuple[float, float, float] = (0, 0, 0),
) -> int:
    """Replace occurrences of text in-place with optional bold, italic, strikethrough formatting.

    Parameters
    ----------
    bold : bool
        Apply bold font weight.
    italic : bool
        Apply italic font style.
    strikethrough : bool
        Draw strikethrough (cross-out) line across replacement text.
    """
    if not search_str:
        raise ValueError("Search string cannot be empty.")

    doc = fitz.open(input_file)
    total_replacements = 0
    fontname = _resolve_font_name(bold=bold, italic=italic)

    try:
        pages = [page_num - 1] if page_num is not None else range(doc.page_count)

        for p_idx in pages:
            if not (0 <= p_idx < doc.page_count):
                continue
            page = doc[p_idx]
            rects = page.search_for(search_str)
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

                final_size = font_size if (font_size and font_size > 0) else detected_size
                final_y = origin_y if origin_y is not None else (rect.y0 + final_size * 0.85)
                replacements.append((rect, rect.x0, final_y, final_size))

            # Apply redactions to erase original text stream
            for rect, _, _, _ in replacements:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

            # Insert replacement text at exact baseline origin
            for _, x_pos, y_pos, f_sz in replacements:
                page.insert_text((x_pos, y_pos), replace_str, fontsize=f_sz, fontname=fontname, color=font_color)
                if strikethrough and replace_str:
                    text_w = fitz.get_text_length(replace_str, fontname=fontname, fontsize=f_sz)
                    y_mid = y_pos - f_sz * 0.35
                    page.draw_line((x_pos, y_mid), (x_pos + text_w, y_mid), color=font_color, width=1.5)
                total_replacements += 1

        doc.save(output_file)
    finally:
        doc.close()

    logger.info("In-place replaced %d instances of '%s' -> '%s'", total_replacements, search_str, replace_str)
    return total_replacements


@validate_input_file
@ensure_output_dir
def edit_text_region(
    input_file: str,
    output_file: str,
    page_num: int,
    rect: tuple[float, float, float, float],
    new_text: str,
    font_size: Optional[float] = None,
    bold: bool = False,
    italic: bool = False,
    strikethrough: bool = False,
    font_color: tuple[float, float, float] = (0, 0, 0),
) -> str:
    """In-place edit a specific rectangular region on a PDF page with optional bold, italic, strikethrough formatting."""
    doc = fitz.open(input_file)
    fontname = _resolve_font_name(bold=bold, italic=italic)

    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Invalid page number {page_num}.")

        page = doc[page_num - 1]
        r = fitz.Rect(rect)

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
                                detected_size = s["size"]
                                origin_y = s["origin"][1]
                                break
                        if origin_y is not None:
                            break
                if origin_y is not None:
                    break

        final_size = font_size if (font_size and font_size > 0) else detected_size

        # 1. Erase old vector text stream
        page.add_redact_annot(r, fill=(1, 1, 1))
        page.apply_redactions()

        # 2. Insert new text at exact baseline origin
        if new_text.strip():
            lines = new_text.split("\n")
            start_y = origin_y if origin_y is not None else (r.y0 + final_size * 0.85)
            for i, line in enumerate(lines):
                if line:
                    line_y = start_y + i * (final_size * 1.25)
                    page.insert_text((r.x0, line_y), line, fontsize=final_size, fontname=fontname, color=font_color)
                    if strikethrough:
                        text_w = fitz.get_text_length(line, fontname=fontname, fontsize=final_size)
                        y_mid = line_y - final_size * 0.35
                        page.draw_line((r.x0, y_mid), (r.x0 + text_w, y_mid), color=font_color, width=1.5)

        doc.save(output_file)
    finally:
        doc.close()

    logger.info("Edited text region on page %d in-place -> %s", page_num, output_file)
    return output_file




# ── Page-Level Visual Merging & Thumbnails ──────────────────────────────────

def get_page_thumbnail(pdf_path: str, page_num: int = 1, width: int = 160) -> Image.Image:
    """Render a PIL thumbnail of a specific PDF page.

    Parameters
    ----------
    pdf_path : str
        Source PDF.
    page_num : int
        1-based page number.
    width : int
        Target pixel width of the thumbnail.
    """
    doc = fitz.open(pdf_path)
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Invalid page {page_num}")
        page = doc[page_num - 1]
        rect = page.rect
        zoom = width / rect.width if rect.width > 0 else 1.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    finally:
        doc.close()


@ensure_output_dir
def merge_pdf_pages(page_specs: List[Dict], output_file: str) -> str:
    """Merge custom list of pages (from same or different PDFs) with individual rotations.

    Parameters
    ----------
    page_specs : list[dict]
        Each dict has:
        - ``file``: path to PDF
        - ``page``: 1-based page number
        - ``rotation``: optional extra rotation angle (0, 90, 180, 270)
    """
    if not page_specs:
        raise ValueError("No pages specified for merging.")

    out_doc = fitz.open()
    try:
        for spec in page_specs:
            src_file = spec["file"]
            p_num = spec.get("page", 1)
            rot = spec.get("rotation", 0)

            if not os.path.isfile(src_file):
                raise FileNotFoundError(f"File not found: {src_file}")

            src_doc = fitz.open(src_file)
            if not (1 <= p_num <= src_doc.page_count):
                src_doc.close()
                raise ValueError(f"Page {p_num} out of range for {src_file}")

            # Insert page into out_doc
            out_doc.insert_pdf(src_doc, from_page=p_num - 1, to_page=p_num - 1)
            if rot:
                out_doc[-1].set_rotation((out_doc[-1].rotation + rot) % 360)
            src_doc.close()

        out_doc.save(output_file)
    finally:
        out_doc.close()

    logger.info("Merged %d pages visually -> %s", len(page_specs), output_file)
    return output_file


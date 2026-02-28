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

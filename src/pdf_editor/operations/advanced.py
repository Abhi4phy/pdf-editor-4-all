"""Advanced PDF operations — compress, page numbers, header/footer, split, bookmarks."""

from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import Literal

import fitz  # PyMuPDF
import pikepdf
import PyPDF2
from pdfrw import PageMerge, PdfReader as PdfrwReader, PdfWriter as PdfrwWriter
from reportlab.lib.colors import black
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

from pdf_editor.utils import ensure_output_dir, validate_input_file

logger = logging.getLogger("pdf_editor.advanced")

# ── Compression quality presets ──────────────────────────────────────────────

COMPRESS_PRESETS = {
    "low": {
        "description": "Minimal compression — fast, preserves full quality",
        "compress_streams": True,
        "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        "image_dpi": None,       # No image downsampling
        "image_quality": None,   # No image re-encoding
    },
    "medium": {
        "description": "Balanced — good compression with minor quality loss",
        "compress_streams": True,
        "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        "image_dpi": 150,        # Downsample images to 150 DPI
        "image_quality": 80,     # JPEG quality 80
    },
    "high": {
        "description": "Maximum compression — smaller file, noticeable quality loss on images",
        "compress_streams": True,
        "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        "image_dpi": 96,         # Downsample images to 96 DPI
        "image_quality": 50,     # JPEG quality 50
    },
}


# ── Compress ─────────────────────────────────────────────────────────────────

@validate_input_file
@ensure_output_dir
def compress_pdf(
    input_file: str,
    output_file: str,
    quality: Literal["low", "medium", "high"] = "medium",
) -> dict:
    """Compress a PDF with selectable quality level.

    Parameters
    ----------
    input_file : str
        Path to the source PDF.
    output_file : str
        Path for the compressed PDF.
    quality : ``"low"`` | ``"medium"`` | ``"high"``
        Compression preset (default: ``"medium"``).

        * **low** — stream compression only, no image changes.
        * **medium** — stream compression + images downsampled to 150 DPI / JPEG 80.
        * **high** — aggressive: images downsampled to 96 DPI / JPEG 50.

    Returns
    -------
    dict
        ``{"output": str, "original_kb": float, "compressed_kb": float, "reduction_pct": float}``
    """
    preset = COMPRESS_PRESETS.get(quality, COMPRESS_PRESETS["medium"])

    if preset["image_dpi"] is not None:
        # Use PyMuPDF to downsample & re-encode images, then save a temp copy
        doc = fitz.open(input_file)
        target_dpi = preset["image_dpi"]
        jpeg_quality = preset["image_quality"]

        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)
            for img_info in images:
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    if base_image is None:
                        continue
                    img_bytes = base_image["image"]
                    ext = base_image["ext"]
                    width = base_image["width"]
                    height = base_image["height"]

                    from PIL import Image as PILImage
                    import io

                    pil_img = PILImage.open(io.BytesIO(img_bytes))

                    # Calculate scale factor based on target DPI
                    # Assume original is ~300 DPI baseline
                    scale = target_dpi / 300.0
                    if scale < 1.0:
                        new_w = max(1, int(width * scale))
                        new_h = max(1, int(height * scale))
                        pil_img = pil_img.resize((new_w, new_h), PILImage.LANCZOS)

                    # Re-encode as JPEG
                    buf = io.BytesIO()
                    if pil_img.mode in ("RGBA", "P"):
                        pil_img = pil_img.convert("RGB")
                    pil_img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
                    new_bytes = buf.getvalue()

                    # Only replace if we actually made it smaller
                    if len(new_bytes) < len(img_bytes):
                        doc._deleteObject(xref)
                        page.insert_image(
                            page.rect, stream=new_bytes, keep_proportion=True
                        )
                except Exception:
                    # Skip images that can't be processed
                    continue

        doc.save(output_file, garbage=4, deflate=True, clean=True)
        doc.close()

        # Run pikepdf on top for stream-level compression (via temp file to avoid overwrite error)
        import tempfile, shutil
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)
        try:
            with pikepdf.Pdf.open(output_file) as pdf:
                pdf.save(
                    tmp_path,
                    compress_streams=preset["compress_streams"],
                    object_stream_mode=preset["object_stream_mode"],
                )
            shutil.move(tmp_path, output_file)
        except Exception:
            # If pikepdf pass fails, keep the PyMuPDF output as-is
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    else:
        # Low quality — pikepdf stream compression only
        with pikepdf.Pdf.open(input_file) as pdf:
            pdf.save(
                output_file,
                compress_streams=preset["compress_streams"],
                object_stream_mode=preset["object_stream_mode"],
            )

    original = os.path.getsize(input_file)
    compressed = os.path.getsize(output_file)
    ratio = (1 - compressed / original) * 100 if original > 0 else 0
    logger.info(
        "Compressed [%s] %s → %s  (%.1f%% reduction)",
        quality, input_file, output_file, ratio,
    )
    return {
        "output": output_file,
        "original_kb": original / 1024,
        "compressed_kb": compressed / 1024,
        "reduction_pct": round(ratio, 1),
    }


# ── Split ────────────────────────────────────────────────────────────────────

@validate_input_file
def split_pdf(input_file: str, output_dir: str) -> list[str]:
    """Split every page of a PDF into its own file.

    Returns
    -------
    list[str]
        Paths to the generated single-page PDFs.
    """
    os.makedirs(output_dir, exist_ok=True)
    reader = PyPDF2.PdfReader(input_file)
    output_paths: list[str] = []

    for idx, page in enumerate(reader.pages):
        writer = PyPDF2.PdfWriter()
        writer.add_page(page)
        path = os.path.join(output_dir, f"page_{idx + 1}.pdf")
        with open(path, "wb") as f:
            writer.write(f)
        output_paths.append(path)

    logger.info("Split %d pages → %s/", len(output_paths), output_dir)
    return output_paths


# ── Page Numbers ─────────────────────────────────────────────────────────────

def _create_page_number_overlay(
    page_num: int,
    total_pages: int,
    page_width: float,
    page_height: float,
    position: str = "bottom-center",
    font_name: str = "Helvetica",
    font_size: int = 10,
) -> bytes:
    """Create a single-page PDF containing only a page number string.

    Parameters
    ----------
    position : str
        One of ``bottom-center``, ``bottom-right``, ``bottom-left``,
        ``top-center``, ``top-right``, ``top-left``.
    """
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(page_width, page_height))
    c.setFont(font_name, font_size)
    c.setFillColor(black)

    text = f"{page_num} / {total_pages}"
    text_width = c.stringWidth(text, font_name, font_size)

    margin = 36  # 0.5 inch
    # Horizontal position
    if "center" in position:
        x = (page_width - text_width) / 2
    elif "right" in position:
        x = page_width - margin - text_width
    else:
        x = margin

    # Vertical position
    if position.startswith("top"):
        y = page_height - margin
    else:
        y = margin / 2

    c.drawString(x, y, text)
    c.save()
    return buf.getvalue()


@validate_input_file
@ensure_output_dir
def add_page_numbers(
    input_file: str,
    output_file: str,
    position: str = "bottom-center",
    font_size: int = 10,
) -> str:
    """Add page numbers to every page of a PDF."""
    reader = PdfrwReader(input_file)
    writer = PdfrwWriter(output_file)

    total = len(reader.pages)
    for idx, page in enumerate(reader.pages):
        # Get page dimensions
        mbox = page.MediaBox
        pw = float(mbox[2]) - float(mbox[0])
        ph = float(mbox[3]) - float(mbox[1])

        overlay_bytes = _create_page_number_overlay(
            page_num=idx + 1,
            total_pages=total,
            page_width=pw,
            page_height=ph,
            position=position,
            font_size=font_size,
        )
        overlay_page = PdfrwReader(fdata=overlay_bytes).pages[0]
        merger = PageMerge(page)
        merger.add(overlay_page).render()
        writer.addpage(page)

    writer.write()
    logger.info("Added page numbers (%s) → %s", position, output_file)
    return output_file


# ── Header / Footer ─────────────────────────────────────────────────────────

def _create_header_footer_overlay(
    page_width: float,
    page_height: float,
    header_text: str = "",
    footer_text: str = "",
    font_name: str = "Helvetica",
    font_size: int = 10,
) -> bytes:
    """Create a single-page PDF with header and/or footer text."""
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(page_width, page_height))
    c.setFont(font_name, font_size)
    c.setFillColor(black)

    margin = 36

    if header_text:
        tw = c.stringWidth(header_text, font_name, font_size)
        x = (page_width - tw) / 2
        y = page_height - margin
        c.drawString(x, y, header_text)

    if footer_text:
        tw = c.stringWidth(footer_text, font_name, font_size)
        x = (page_width - tw) / 2
        y = margin / 2
        c.drawString(x, y, footer_text)

    c.save()
    return buf.getvalue()


@validate_input_file
@ensure_output_dir
def add_header_footer(
    input_file: str,
    output_file: str,
    header_text: str = "",
    footer_text: str = "",
) -> str:
    """Add header and/or footer text to every page."""
    if not header_text and not footer_text:
        raise ValueError("At least one of header_text or footer_text must be provided.")

    reader = PdfrwReader(input_file)
    writer = PdfrwWriter(output_file)

    for page in reader.pages:
        mbox = page.MediaBox
        pw = float(mbox[2]) - float(mbox[0])
        ph = float(mbox[3]) - float(mbox[1])

        overlay_bytes = _create_header_footer_overlay(
            page_width=pw,
            page_height=ph,
            header_text=header_text,
            footer_text=footer_text,
        )
        overlay_page = PdfrwReader(fdata=overlay_bytes).pages[0]
        PageMerge(page).add(overlay_page).render()
        writer.addpage(page)

    writer.write()
    logger.info("Added header/footer → %s", output_file)
    return output_file


# ── Bookmarks ────────────────────────────────────────────────────────────────

def get_bookmarks(input_file: str) -> list[dict]:
    """Read existing bookmarks/outlines from a PDF.

    Returns
    -------
    list[dict]
        Each dict has ``title`` (str) and ``page`` (int, 1-based).
    """
    reader = PyPDF2.PdfReader(input_file)
    results: list[dict] = []

    def _walk(outlines, depth=0):
        for item in outlines:
            if isinstance(item, list):
                _walk(item, depth + 1)
            else:
                page_idx = reader.get_destination_page_number(item)
                results.append({
                    "title": item.title,
                    "page": page_idx + 1,
                    "depth": depth,
                })

    if reader.outline:
        _walk(reader.outline)
    return results


@validate_input_file
@ensure_output_dir
def add_bookmarks(
    input_file: str,
    output_file: str,
    bookmarks: list[dict],
) -> str:
    """Add bookmarks to a PDF.

    Parameters
    ----------
    bookmarks : list[dict]
        Each dict must have ``title`` (str) and ``page`` (int, 1-based).
    """
    reader = PyPDF2.PdfReader(input_file)
    writer = PyPDF2.PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    for bm in bookmarks:
        writer.add_outline_item(bm["title"], bm["page"] - 1)

    with open(output_file, "wb") as f:
        writer.write(f)

    logger.info("Added %d bookmarks → %s", len(bookmarks), output_file)
    return output_file

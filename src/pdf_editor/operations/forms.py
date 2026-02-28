"""Forms and digital-signature operations."""

from __future__ import annotations

import logging
import os
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image

from pdf_editor.utils import validate_input_file

logger = logging.getLogger("pdf_editor.forms")


@validate_input_file
def add_signature_image(
    input_file: str,
    output_file: str,
    signature_path: str,
    page_number: int = 1,
    x: float = 100,
    y: float = 100,
    width: float = 200,
    height: float = 100,
) -> str:
    """Stamp a signature image onto a specific page of a PDF.

    Parameters
    ----------
    signature_path : str
        Path to the signature image (PNG/JPG).
    page_number : int
        1-based page number.
    x, y : float
        Top-left position in PDF points.
    width, height : float
        Size of the signature in PDF points.
    """
    if not os.path.isfile(signature_path):
        raise FileNotFoundError(f"Signature image not found: {signature_path}")

    doc = fitz.open(input_file)
    try:
        if not (1 <= page_number <= doc.page_count):
            raise ValueError(
                f"Invalid page number {page_number}. PDF has {doc.page_count} pages."
            )

        page = doc[page_number - 1]
        rect = fitz.Rect(x, y, x + width, y + height)

        sig_img = Image.open(signature_path)
        sig_bytes = BytesIO()
        sig_img.save(sig_bytes, format=sig_img.format or "PNG")

        page.insert_image(rect, stream=sig_bytes.getvalue())

        out_dir = os.path.dirname(output_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        doc.save(output_file)
    finally:
        doc.close()

    logger.info("Signature added (page %d) → %s", page_number, output_file)
    return output_file

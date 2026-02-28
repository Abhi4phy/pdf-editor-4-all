"""PDF conversion operations — to Word, images, text."""

from __future__ import annotations

import logging
import os

import fitz  # PyMuPDF
from pdf2docx import Converter

from pdf_editor.utils import validate_input_file

logger = logging.getLogger("pdf_editor.converter")


@validate_input_file
def pdf_to_word(input_file: str, output_file: str) -> str:
    """Convert a PDF to a Word document (.docx)."""
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cv = Converter(input_file)
    try:
        cv.convert(output_file)
    finally:
        cv.close()

    logger.info("Converted PDF → DOCX: %s", output_file)
    return output_file


@validate_input_file
def pdf_to_images(input_file: str, output_dir: str, dpi: int = 300, fmt: str = "png") -> list[str]:
    """Convert each page of a PDF to an image file.

    Parameters
    ----------
    dpi : int
        Resolution in dots per inch (default 300).
    fmt : str
        Image format — ``png``, ``jpg``, etc.

    Returns
    -------
    list[str]
        Paths to the generated image files.
    """
    os.makedirs(output_dir, exist_ok=True)
    scale = dpi / 72
    doc = fitz.open(input_file)
    paths: list[str] = []

    try:
        for idx in range(doc.page_count):
            page = doc[idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            path = os.path.join(output_dir, f"page_{idx + 1}.{fmt}")
            pix.save(path)
            paths.append(path)
    finally:
        doc.close()

    logger.info("Converted %d pages → images in %s/", len(paths), output_dir)
    return paths


@validate_input_file
def pdf_to_text(input_file: str, output_file: str) -> str:
    """Extract all text from a PDF and save to a ``.txt`` file."""
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    doc = fitz.open(input_file)
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for page in doc:
                text = page.get_text()
                f.write(text)
                f.write("\n")
    finally:
        doc.close()

    logger.info("Extracted text → %s", output_file)
    return output_file

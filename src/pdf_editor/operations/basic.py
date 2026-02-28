"""Basic PDF operations — merge, extract, rotate, watermark."""

from __future__ import annotations

import logging
import os
from typing import List, Set

import PyPDF2

from pdf_editor.utils import ensure_output_dir, parse_page_ranges, validate_input_file

logger = logging.getLogger("pdf_editor.basic")


# ── Merge ────────────────────────────────────────────────────────────────────

@ensure_output_dir
def merge_pdfs(input_files: List[str], output_file: str) -> str:
    """Merge multiple PDF files into a single PDF.

    Parameters
    ----------
    input_files : list[str]
        Paths to the source PDF files (in order).
    output_file : str
        Destination path for the merged PDF.

    Returns
    -------
    str
        The output file path.
    """
    if not input_files:
        raise ValueError("No input files provided.")

    merger = PyPDF2.PdfMerger()
    try:
        for pdf_path in input_files:
            if not os.path.isfile(pdf_path):
                raise FileNotFoundError(f"File not found: {pdf_path}")
            merger.append(pdf_path)
        merger.write(output_file)
    finally:
        merger.close()

    logger.info("Merged %d PDFs → %s", len(input_files), output_file)
    return output_file


# ── Extract Pages ────────────────────────────────────────────────────────────

@validate_input_file
@ensure_output_dir
def extract_pages(input_file: str, output_file: str, pages: str | Set[int]) -> str:
    """Extract specific pages from a PDF.

    Parameters
    ----------
    input_file : str
        Source PDF path.
    output_file : str
        Destination PDF path.
    pages : str | set[int]
        Either a page-range string (``'1,3-5,7'``) or a set of 1-based page numbers.

    Returns
    -------
    str
        The output file path.
    """
    if isinstance(pages, str):
        pages = parse_page_ranges(pages)

    reader = PyPDF2.PdfReader(input_file)
    writer = PyPDF2.PdfWriter()
    total = len(reader.pages)

    extracted = 0
    for page_num in sorted(pages):
        if 1 <= page_num <= total:
            writer.add_page(reader.pages[page_num - 1])
            extracted += 1
        else:
            logger.warning("Skipping invalid page %d (PDF has %d pages)", page_num, total)

    if extracted == 0:
        raise ValueError("No valid pages to extract.")

    with open(output_file, "wb") as f:
        writer.write(f)

    logger.info("Extracted %d pages → %s", extracted, output_file)
    return output_file


# ── Rotate ───────────────────────────────────────────────────────────────────

@validate_input_file
@ensure_output_dir
def rotate_pdf(input_file: str, output_file: str, angle: int) -> str:
    """Rotate every page of a PDF by a given angle.

    Parameters
    ----------
    angle : int
        Must be 90, 180, or 270.
    """
    if angle not in (90, 180, 270):
        raise ValueError(f"Invalid rotation angle: {angle}. Must be 90, 180, or 270.")

    reader = PyPDF2.PdfReader(input_file)
    writer = PyPDF2.PdfWriter()

    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)

    with open(output_file, "wb") as f:
        writer.write(f)

    logger.info("Rotated %d pages by %d° → %s", len(reader.pages), angle, output_file)
    return output_file


# ── Watermark ────────────────────────────────────────────────────────────────

@validate_input_file
@ensure_output_dir
def add_watermark(input_file: str, output_file: str, watermark_file: str) -> str:
    """Overlay a watermark PDF onto every page of the source PDF.

    Parameters
    ----------
    watermark_file : str
        Path to a single-page PDF used as the watermark.
    """
    if not os.path.isfile(watermark_file):
        raise FileNotFoundError(f"Watermark file not found: {watermark_file}")

    reader = PyPDF2.PdfReader(input_file)
    watermark_reader = PyPDF2.PdfReader(watermark_file)
    writer = PyPDF2.PdfWriter()

    watermark_page = watermark_reader.pages[0]

    for page in reader.pages:
        page.merge_page(watermark_page)
        writer.add_page(page)

    with open(output_file, "wb") as f:
        writer.write(f)

    logger.info("Added watermark → %s", output_file)
    return output_file

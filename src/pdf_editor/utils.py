"""Shared utilities — decorators, helpers, logging."""

from __future__ import annotations

import functools
import logging
import os
from typing import Callable, Set

import PyPDF2

logger = logging.getLogger("pdf_editor")


# ── Logging setup ────────────────────────────────────────────────────────────

def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    )
    root = logging.getLogger("pdf_editor")
    root.setLevel(level)
    root.addHandler(handler)


# ── Decorators ───────────────────────────────────────────────────────────────

def validate_input_file(func: Callable) -> Callable:
    """Decorator that validates the first positional ``input_file`` argument exists and is a PDF."""

    @functools.wraps(func)
    def wrapper(input_file: str, *args, **kwargs):
        if not os.path.isfile(input_file):
            raise FileNotFoundError(f"File not found: {input_file}")
        if not input_file.lower().endswith(".pdf"):
            raise ValueError(f"Not a PDF file: {input_file}")
        return func(input_file, *args, **kwargs)

    return wrapper


def ensure_output_dir(func: Callable) -> Callable:
    """Decorator that creates the output directory tree if necessary.

    Looks for ``output_file`` or ``output_dir`` in *kwargs* (or 2nd positional arg).
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        path = kwargs.get("output_file") or kwargs.get("output_dir")
        if path is None and len(args) >= 2:
            path = args[1]
        if path:
            directory = os.path.dirname(path) if not os.path.isdir(path) else path
            if directory:
                os.makedirs(directory, exist_ok=True)
        return func(*args, **kwargs)

    return wrapper


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_page_ranges(pages_str: str) -> Set[int]:
    """Parse a page-range string like ``'1,3-5,7'`` into a set of 1-based page numbers."""
    pages: Set[int] = set()
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start_s, end_s = part.split("-", maxsplit=1)
            start, end = int(start_s.strip()), int(end_s.strip())
            if start > end:
                raise ValueError(f"Invalid range: {part}")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    return pages


def get_pdf_info(input_file: str) -> dict:
    """Return basic metadata for a PDF file."""
    import pikepdf

    with pikepdf.Pdf.open(input_file) as pdf:
        info = pdf.docinfo
        return {
            "title": str(info.get("/Title", "N/A")),
            "author": str(info.get("/Author", "N/A")),
            "pages": len(pdf.pages),
            "created": str(info.get("/CreationDate", "N/A")),
            "file_size": os.path.getsize(input_file),
        }

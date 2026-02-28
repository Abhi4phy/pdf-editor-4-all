"""Tests for PDF conversion operations."""

from __future__ import annotations

import os

import PyPDF2
import pytest

from pdf_editor.operations.converter import pdf_to_images, pdf_to_text


@pytest.fixture
def sample_pdf_with_text(tmp_path) -> str:
    """Create a PDF that contains actual text content (using reportlab)."""
    from io import BytesIO

    from reportlab.pdfgen import canvas

    path = str(tmp_path / "with_text.pdf")
    c = canvas.Canvas(path)
    c.drawString(100, 700, "Hello PDF Editor 4 All Test")
    c.showPage()
    c.save()
    return path


class TestPdfToImages:
    def test_converts_all_pages(self, sample_pdf_with_text, tmp_path):
        out_dir = str(tmp_path / "images")
        paths = pdf_to_images(sample_pdf_with_text, out_dir, dpi=72)
        assert len(paths) == 1
        assert os.path.isfile(paths[0])
        assert paths[0].endswith(".png")


class TestPdfToText:
    def test_extracts_text(self, sample_pdf_with_text, tmp_path):
        out = str(tmp_path / "output.txt")
        pdf_to_text(sample_pdf_with_text, out)
        assert os.path.isfile(out)
        content = open(out, encoding="utf-8").read()
        assert "Hello PDF Editor 4 All Test" in content

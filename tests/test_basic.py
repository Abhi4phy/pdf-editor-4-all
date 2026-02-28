"""Tests for basic PDF operations."""

from __future__ import annotations

import os
import tempfile

import PyPDF2
import pytest

from pdf_editor.operations.basic import add_watermark, extract_pages, merge_pdfs, rotate_pdf


@pytest.fixture
def sample_pdf(tmp_path) -> str:
    """Create a minimal 3-page PDF for testing."""
    path = str(tmp_path / "sample.pdf")
    writer = PyPDF2.PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)
    return path


@pytest.fixture
def another_pdf(tmp_path) -> str:
    """Create a second minimal PDF."""
    path = str(tmp_path / "another.pdf")
    writer = PyPDF2.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)
    return path


class TestMerge:
    def test_merge_two_pdfs(self, sample_pdf, another_pdf, tmp_path):
        out = str(tmp_path / "merged.pdf")
        merge_pdfs([sample_pdf, another_pdf], out)
        reader = PyPDF2.PdfReader(out)
        assert len(reader.pages) == 4  # 3 + 1

    def test_merge_no_files(self, tmp_path):
        out = str(tmp_path / "merged.pdf")
        with pytest.raises(ValueError, match="No input files"):
            merge_pdfs([], out)

    def test_merge_missing_file(self, tmp_path):
        out = str(tmp_path / "merged.pdf")
        with pytest.raises(FileNotFoundError):
            merge_pdfs(["nonexistent.pdf"], out)


class TestExtract:
    def test_extract_single_page(self, sample_pdf, tmp_path):
        out = str(tmp_path / "extracted.pdf")
        extract_pages(sample_pdf, out, "2")
        reader = PyPDF2.PdfReader(out)
        assert len(reader.pages) == 1

    def test_extract_range(self, sample_pdf, tmp_path):
        out = str(tmp_path / "extracted.pdf")
        extract_pages(sample_pdf, out, "1-2")
        reader = PyPDF2.PdfReader(out)
        assert len(reader.pages) == 2

    def test_extract_invalid_page(self, sample_pdf, tmp_path):
        out = str(tmp_path / "extracted.pdf")
        # Page 99 doesn't exist — should extract page 1 only
        extract_pages(sample_pdf, out, "1,99")
        reader = PyPDF2.PdfReader(out)
        assert len(reader.pages) == 1

    def test_extract_all_invalid(self, sample_pdf, tmp_path):
        out = str(tmp_path / "extracted.pdf")
        with pytest.raises(ValueError, match="No valid pages"):
            extract_pages(sample_pdf, out, "99")


class TestRotate:
    @pytest.mark.parametrize("angle", [90, 180, 270])
    def test_rotate_valid_angles(self, sample_pdf, tmp_path, angle):
        out = str(tmp_path / "rotated.pdf")
        rotate_pdf(sample_pdf, out, angle)
        reader = PyPDF2.PdfReader(out)
        assert len(reader.pages) == 3

    def test_rotate_invalid_angle(self, sample_pdf, tmp_path):
        out = str(tmp_path / "rotated.pdf")
        with pytest.raises(ValueError, match="Invalid rotation"):
            rotate_pdf(sample_pdf, out, 45)


class TestWatermark:
    def test_watermark(self, sample_pdf, another_pdf, tmp_path):
        out = str(tmp_path / "watermarked.pdf")
        add_watermark(sample_pdf, out, another_pdf)
        reader = PyPDF2.PdfReader(out)
        assert len(reader.pages) == 3

    def test_watermark_missing_file(self, sample_pdf, tmp_path):
        out = str(tmp_path / "watermarked.pdf")
        with pytest.raises(FileNotFoundError):
            add_watermark(sample_pdf, out, "nonexistent.pdf")

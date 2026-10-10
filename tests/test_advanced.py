"""Tests for advanced PDF operations."""

from __future__ import annotations

import os

import PyPDF2
import pytest

from pdf_editor.operations.advanced import (
    add_bookmarks,
    add_header_footer,
    add_page_numbers,
    compress_pdf,
    get_bookmarks,
    split_pdf,
)


@pytest.fixture
def sample_pdf(tmp_path) -> str:
    path = str(tmp_path / "sample.pdf")
    writer = PyPDF2.PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)
    return path


class TestCompress:
    def test_compress_creates_output(self, sample_pdf, tmp_path):
        out = str(tmp_path / "compressed.pdf")
        result = compress_pdf(sample_pdf, out)
        assert os.path.isfile(out)
        assert result["output"] == out
        assert result["original_kb"] > 0
        assert result["compressed_kb"] > 0
        assert isinstance(result["reduction_pct"], float)

    def test_compress_quality_levels(self, sample_pdf, tmp_path):
        for quality in ("low", "medium", "high"):
            out = str(tmp_path / f"compressed_{quality}.pdf")
            result = compress_pdf(sample_pdf, out, quality=quality)
            assert os.path.isfile(out)
            assert isinstance(result["reduction_pct"], float)


class TestSplit:
    def test_split_creates_pages(self, sample_pdf, tmp_path):
        out_dir = str(tmp_path / "pages")
        paths = split_pdf(sample_pdf, out_dir)
        assert len(paths) == 3
        for p in paths:
            assert os.path.isfile(p)
            reader = PyPDF2.PdfReader(p)
            assert len(reader.pages) == 1


class TestPageNumbers:
    def test_add_page_numbers(self, sample_pdf, tmp_path):
        out = str(tmp_path / "numbered.pdf")
        add_page_numbers(sample_pdf, out)
        assert os.path.isfile(out)
        reader = PyPDF2.PdfReader(out)
        assert len(reader.pages) == 3


class TestHeaderFooter:
    def test_add_header_only(self, sample_pdf, tmp_path):
        out = str(tmp_path / "headered.pdf")
        add_header_footer(sample_pdf, out, header_text="Test Header")
        assert os.path.isfile(out)

    def test_add_both(self, sample_pdf, tmp_path):
        out = str(tmp_path / "hf.pdf")
        add_header_footer(sample_pdf, out, header_text="Header", footer_text="Footer")
        assert os.path.isfile(out)

    def test_no_text_raises(self, sample_pdf, tmp_path):
        out = str(tmp_path / "empty.pdf")
        with pytest.raises(ValueError, match="At least one"):
            add_header_footer(sample_pdf, out)


class TestBookmarks:
    def test_add_and_read_bookmarks(self, sample_pdf, tmp_path):
        out = str(tmp_path / "bookmarked.pdf")
        bms = [{"title": "Chapter 1", "page": 1}, {"title": "Chapter 2", "page": 2}]
        add_bookmarks(sample_pdf, out, bms)
        assert os.path.isfile(out)

        result = get_bookmarks(out)
        assert len(result) == 2
        assert result[0]["title"] == "Chapter 1"


class TestInPlaceEditing:
    def test_replace_text_in_pdf(self, tmp_path):
        import fitz
        from pdf_editor.operations.extras import replace_text_in_pdf

        pdf_path = str(tmp_path / "test_text.pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Hello PyMuPDF test")
        doc.save(pdf_path)
        doc.close()

        out_path = str(tmp_path / "test_replaced.pdf")
        count = replace_text_in_pdf(pdf_path, out_path, "PyMuPDF", "World")
        assert count == 1
        assert os.path.isfile(out_path)

        doc_res = fitz.open(out_path)
        res_text = doc_res[0].get_text()
        doc_res.close()
        assert "World" in res_text

    def test_edit_text_region(self, tmp_path):
        import fitz
        from pdf_editor.operations.extras import edit_text_region

        pdf_path = str(tmp_path / "test_region.pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Original Text Region")
        doc.save(pdf_path)
        doc.close()

        out_path = str(tmp_path / "test_region_edited.pdf")
        edit_text_region(pdf_path, out_path, 1, (90, 80, 250, 120), "New Region Content")
        assert os.path.isfile(out_path)

        doc_res = fitz.open(out_path)
        res_text = doc_res[0].get_text()
        doc_res.close()
        assert "New Region Content" in res_text


class TestVisualMerge:
    def test_merge_pdf_pages(self, sample_pdf, tmp_path):
        import fitz
        from pdf_editor.operations.extras import get_page_thumbnail, merge_pdf_pages

        thumb = get_page_thumbnail(sample_pdf, 1, width=100)
        assert thumb is not None
        assert thumb.width == 100

        out_path = str(tmp_path / "visually_merged.pdf")
        specs = [
            {"file": sample_pdf, "page": 1, "rotation": 90},
            {"file": sample_pdf, "page": 3, "rotation": 0},
        ]
        merge_pdf_pages(specs, out_path)
        assert os.path.isfile(out_path)

        doc = fitz.open(out_path)
        assert doc.page_count == 2
        assert doc[0].rotation == 90
        doc.close()


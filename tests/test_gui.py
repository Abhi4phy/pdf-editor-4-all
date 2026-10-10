"""Test GUI module imports and initialization."""

import pytest
import os


def test_gui_import():
    import pdf_editor.app as app_module
    assert hasattr(app_module, "PDFEditorApp")


def test_extras_in_place_editing(tmp_path):
    import fitz
    from pdf_editor.operations.extras import replace_text_in_pdf, edit_text_region

    pdf_file = str(tmp_path / "test.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Sample Text for In-Place Replacement")
    doc.save(pdf_file)
    doc.close()

    out_file = str(tmp_path / "replaced.pdf")
    count = replace_text_in_pdf(pdf_file, out_file, "Sample", "Target")
    assert count == 1
    assert os.path.isfile(out_file)

    doc_out = fitz.open(out_file)
    assert "Target" in doc_out[0].get_text()
    doc_out.close()


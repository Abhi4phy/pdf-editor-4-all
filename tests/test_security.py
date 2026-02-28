"""Tests for PDF security operations."""

from __future__ import annotations

import os

import pikepdf
import PyPDF2
import pytest

from pdf_editor.operations.security import encrypt_pdf, remove_password


@pytest.fixture
def sample_pdf(tmp_path) -> str:
    path = str(tmp_path / "sample.pdf")
    writer = PyPDF2.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)
    return path


class TestEncrypt:
    def test_encrypt_creates_protected_pdf(self, sample_pdf, tmp_path):
        out = str(tmp_path / "encrypted.pdf")
        encrypt_pdf(sample_pdf, out, "testpass123")
        assert os.path.isfile(out)

        # Should fail to open without password
        with pytest.raises(pikepdf.PasswordError):
            pikepdf.Pdf.open(out)

        # Should succeed with password
        with pikepdf.Pdf.open(out, password="testpass123") as pdf:
            assert len(pdf.pages) == 1

    def test_encrypt_empty_password(self, sample_pdf, tmp_path):
        out = str(tmp_path / "encrypted.pdf")
        with pytest.raises(ValueError, match="empty"):
            encrypt_pdf(sample_pdf, out, "")


class TestRemovePassword:
    def test_remove_password(self, sample_pdf, tmp_path):
        encrypted = str(tmp_path / "encrypted.pdf")
        encrypt_pdf(sample_pdf, encrypted, "mypass")

        decrypted = str(tmp_path / "decrypted.pdf")
        remove_password(encrypted, decrypted, "mypass")
        assert os.path.isfile(decrypted)

        # Should open without password
        with pikepdf.Pdf.open(decrypted) as pdf:
            assert len(pdf.pages) == 1

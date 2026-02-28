"""PDF security operations — encrypt, remove password."""

from __future__ import annotations

import logging

import pikepdf

from pdf_editor.utils import ensure_output_dir, validate_input_file

logger = logging.getLogger("pdf_editor.security")


@validate_input_file
@ensure_output_dir
def encrypt_pdf(input_file: str, output_file: str, password: str) -> str:
    """Encrypt a PDF with a user/owner password.

    Parameters
    ----------
    password : str
        The password that will be set as both user and owner password.
    """
    if not password:
        raise ValueError("Password must not be empty.")

    with pikepdf.Pdf.open(input_file) as pdf:
        pdf.save(
            output_file,
            encryption=pikepdf.Encryption(owner=password, user=password),
        )

    logger.info("Encrypted → %s", output_file)
    return output_file


@validate_input_file
@ensure_output_dir
def remove_password(input_file: str, output_file: str, password: str) -> str:
    """Remove encryption from a PDF (requires the current password).

    Parameters
    ----------
    password : str
        The current password of the encrypted PDF.
    """
    with pikepdf.Pdf.open(input_file, password=password) as pdf:
        pdf.save(output_file)

    logger.info("Password removed → %s", output_file)
    return output_file

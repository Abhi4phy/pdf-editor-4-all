"""Entry point for the PDF Editor application."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="pdf-editor",
        description="PDF Editor 4 All — merge, split, compress, encrypt, convert, and more.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        default=False,
        help="Launch the graphical user interface",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── Merge ────────────────────────────────────────────────────────────────
    merge_p = subparsers.add_parser("merge", help="Merge multiple PDFs into one")
    merge_p.add_argument("files", nargs="+", help="PDF files to merge")
    merge_p.add_argument("-o", "--output", required=True, help="Output file path")

    # ── Split ────────────────────────────────────────────────────────────────
    split_p = subparsers.add_parser("split", help="Split PDF into individual pages")
    split_p.add_argument("file", help="Input PDF file")
    split_p.add_argument("-o", "--output-dir", required=True, help="Output directory")

    # ── Extract ──────────────────────────────────────────────────────────────
    extract_p = subparsers.add_parser("extract", help="Extract specific pages")
    extract_p.add_argument("file", help="Input PDF file")
    extract_p.add_argument("-p", "--pages", required=True, help="Pages to extract (e.g. 1,3-5,7)")
    extract_p.add_argument("-o", "--output", required=True, help="Output file path")

    # ── Rotate ───────────────────────────────────────────────────────────────
    rotate_p = subparsers.add_parser("rotate", help="Rotate all pages in a PDF")
    rotate_p.add_argument("file", help="Input PDF file")
    rotate_p.add_argument("-a", "--angle", type=int, required=True, choices=[90, 180, 270])
    rotate_p.add_argument("-o", "--output", required=True, help="Output file path")

    # ── Compress ─────────────────────────────────────────────────────────────
    compress_p = subparsers.add_parser("compress", help="Compress a PDF")
    compress_p.add_argument("file", help="Input PDF file")
    compress_p.add_argument("-o", "--output", required=True, help="Output file path")
    compress_p.add_argument(
        "-q", "--quality", default="medium", choices=["low", "medium", "high"],
        help="Compression level: low (fast, lossless), medium (balanced), high (smallest, lossy images). Default: medium",
    )

    # ── Encrypt ──────────────────────────────────────────────────────────────
    encrypt_p = subparsers.add_parser("encrypt", help="Encrypt a PDF with a password")
    encrypt_p.add_argument("file", help="Input PDF file")
    encrypt_p.add_argument("-p", "--password", required=True, help="Password")
    encrypt_p.add_argument("-o", "--output", required=True, help="Output file path")

    # ── Decrypt ──────────────────────────────────────────────────────────────
    decrypt_p = subparsers.add_parser("decrypt", help="Remove password from a PDF")
    decrypt_p.add_argument("file", help="Input PDF file")
    decrypt_p.add_argument("-p", "--password", required=True, help="Current password")
    decrypt_p.add_argument("-o", "--output", required=True, help="Output file path")

    # ── Watermark ────────────────────────────────────────────────────────────
    watermark_p = subparsers.add_parser("watermark", help="Add watermark to a PDF")
    watermark_p.add_argument("file", help="Input PDF file")
    watermark_p.add_argument("-w", "--watermark", required=True, help="Watermark PDF file")
    watermark_p.add_argument("-o", "--output", required=True, help="Output file path")

    # ── Page Numbers ─────────────────────────────────────────────────────────
    pnum_p = subparsers.add_parser("page-numbers", help="Add page numbers to a PDF")
    pnum_p.add_argument("file", help="Input PDF file")
    pnum_p.add_argument("-o", "--output", required=True, help="Output file path")
    pnum_p.add_argument(
        "--position", default="bottom-center",
        choices=["bottom-center", "bottom-right", "bottom-left", "top-center", "top-right", "top-left"],
        help="Position of page numbers (default: bottom-center)",
    )

    # ── Header/Footer ────────────────────────────────────────────────────────
    hf_p = subparsers.add_parser("header-footer", help="Add header and/or footer to a PDF")
    hf_p.add_argument("file", help="Input PDF file")
    hf_p.add_argument("-o", "--output", required=True, help="Output file path")
    hf_p.add_argument("--header", default="", help="Header text")
    hf_p.add_argument("--footer", default="", help="Footer text")

    # ── Convert ──────────────────────────────────────────────────────────────
    convert_p = subparsers.add_parser("convert", help="Convert PDF to another format")
    convert_p.add_argument("file", help="Input PDF file")
    convert_p.add_argument(
        "-f", "--format", required=True, choices=["docx", "images", "text"],
        help="Output format",
    )
    convert_p.add_argument("-o", "--output", required=True, help="Output file/directory path")
    convert_p.add_argument(
        "--dpi", type=int, default=300,
        help="DPI for image conversion (default: 300)",
    )

    # ── Info ──────────────────────────────────────────────────────────────────
    info_p = subparsers.add_parser("info", help="Show PDF metadata")
    info_p.add_argument("file", help="Input PDF file")

    # ── Images to PDF ────────────────────────────────────────────────────────
    img_p = subparsers.add_parser("images-to-pdf", help="Convert images to a PDF")
    img_p.add_argument("files", nargs="+", help="Image files (PNG, JPG, etc.)")
    img_p.add_argument("-o", "--output", required=True, help="Output PDF path")

    # ── Reorder ──────────────────────────────────────────────────────────────
    reorder_p = subparsers.add_parser("reorder", help="Reorder pages in a PDF")
    reorder_p.add_argument("file", help="Input PDF file")
    reorder_p.add_argument("-p", "--pages", required=True,
                           help="New page order as comma-separated numbers (e.g. 3,1,2)")
    reorder_p.add_argument("-o", "--output", required=True, help="Output file path")

    # ── Delete Pages ─────────────────────────────────────────────────────────
    del_p = subparsers.add_parser("delete-pages", help="Delete specific pages from a PDF")
    del_p.add_argument("file", help="Input PDF file")
    del_p.add_argument("-p", "--pages", required=True,
                       help="Pages to delete (e.g. 2,4,6)")
    del_p.add_argument("-o", "--output", required=True, help="Output file path")

    # ── Metadata ─────────────────────────────────────────────────────────────
    meta_p = subparsers.add_parser("metadata", help="View or edit PDF metadata")
    meta_p.add_argument("file", help="Input PDF file")
    meta_p.add_argument("-o", "--output", help="Output file (omit to just view metadata)")
    meta_p.add_argument("--title", help="Set title")
    meta_p.add_argument("--author", help="Set author")
    meta_p.add_argument("--subject", help="Set subject")
    meta_p.add_argument("--keywords", help="Set keywords")

    args = parser.parse_args()

    # No command and no --gui → show help
    if not args.command and not args.gui:
        parser.print_help()
        sys.exit(0)

    # Launch GUI
    if args.gui:
        from pdf_editor.app import PDFEditorApp

        app = PDFEditorApp()
        app.run()
        sys.exit(0)

    # ── Execute CLI commands ─────────────────────────────────────────────────
    from pdf_editor.cli import run_command

    run_command(args)


if __name__ == "__main__":
    main()

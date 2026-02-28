"""CLI command dispatcher for PDF Editor 4 All."""

from __future__ import annotations

import sys

from pdf_editor.operations import advanced, basic, converter, extras, security
from pdf_editor.utils import get_pdf_info, setup_logging


def run_command(args) -> None:
    """Execute the CLI sub-command described by *args*."""
    setup_logging()

    dispatch = {
        "merge": _cmd_merge,
        "split": _cmd_split,
        "extract": _cmd_extract,
        "rotate": _cmd_rotate,
        "compress": _cmd_compress,
        "encrypt": _cmd_encrypt,
        "decrypt": _cmd_decrypt,
        "watermark": _cmd_watermark,
        "page-numbers": _cmd_page_numbers,
        "header-footer": _cmd_header_footer,
        "convert": _cmd_convert,
        "info": _cmd_info,
        "images-to-pdf": _cmd_images_to_pdf,
        "reorder": _cmd_reorder,
        "delete-pages": _cmd_delete_pages,
        "metadata": _cmd_metadata,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)

    try:
        handler(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


# ── Individual command handlers ──────────────────────────────────────────────

def _cmd_merge(args):
    basic.merge_pdfs(args.files, args.output)
    print(f"Merged {len(args.files)} PDFs → {args.output}")


def _cmd_split(args):
    paths = advanced.split_pdf(args.file, args.output_dir)
    print(f"Split into {len(paths)} pages → {args.output_dir}/")


def _cmd_extract(args):
    basic.extract_pages(args.file, args.output, args.pages)
    print(f"Extracted pages → {args.output}")


def _cmd_rotate(args):
    basic.rotate_pdf(args.file, args.output, args.angle)
    print(f"Rotated by {args.angle}° → {args.output}")


def _cmd_compress(args):
    from pdf_editor.operations.advanced import COMPRESS_PRESETS

    preset = COMPRESS_PRESETS[args.quality]
    print(f"Compression quality: {args.quality}")
    print(f"  → {preset['description']}")
    print(f"  Compressing...")
    result = advanced.compress_pdf(args.file, args.output, quality=args.quality)
    print(f"  Done! {result['original_kb']:.0f} KB → {result['compressed_kb']:.0f} KB  ({result['reduction_pct']:.1f}% smaller)")


def _cmd_encrypt(args):
    security.encrypt_pdf(args.file, args.output, args.password)
    print(f"Encrypted → {args.output}")


def _cmd_decrypt(args):
    security.remove_password(args.file, args.output, args.password)
    print(f"Decrypted → {args.output}")


def _cmd_watermark(args):
    basic.add_watermark(args.file, args.output, args.watermark)
    print(f"Watermark added → {args.output}")


def _cmd_page_numbers(args):
    advanced.add_page_numbers(args.file, args.output, position=args.position)
    print(f"Page numbers added ({args.position}) → {args.output}")


def _cmd_header_footer(args):
    advanced.add_header_footer(
        args.file, args.output, header_text=args.header, footer_text=args.footer
    )
    print(f"Header/footer added → {args.output}")


def _cmd_convert(args):
    fmt = args.format
    if fmt == "docx":
        converter.pdf_to_word(args.file, args.output)
        print(f"Converted → {args.output}")
    elif fmt == "images":
        paths = converter.pdf_to_images(args.file, args.output, dpi=args.dpi)
        print(f"Converted {len(paths)} pages → {args.output}/")
    elif fmt == "text":
        converter.pdf_to_text(args.file, args.output)
        print(f"Extracted text → {args.output}")


def _cmd_info(args):
    info = get_pdf_info(args.file)
    print(f"  Title:    {info['title']}")
    print(f"  Author:   {info['author']}")
    print(f"  Pages:    {info['pages']}")
    print(f"  Created:  {info['created']}")
    print(f"  Size:     {info['file_size'] / 1024:.1f} KB")


def _cmd_images_to_pdf(args):
    extras.images_to_pdf(args.images, args.output)
    print(f"Created PDF from {len(args.images)} image(s) → {args.output}")


def _cmd_reorder(args):
    page_order = [int(p.strip()) for p in args.pages.split(",")]
    extras.reorder_pages(args.file, args.output, page_order)
    print(f"Reordered pages → {args.output}")


def _cmd_delete_pages(args):
    pages = [int(p.strip()) for p in args.pages.split(",")]
    extras.delete_pages(args.file, args.output, pages)
    print(f"Deleted {len(pages)} page(s) → {args.output}")


def _cmd_metadata(args):
    if not any([args.title, args.author, args.subject, args.keywords]):
        meta = extras.get_metadata(args.file)
        for k, v in meta.items():
            print(f"  {k:12s}: {v}")
    else:
        out = args.output or args.file
        meta = {}
        if args.title:
            meta["title"] = args.title
        if args.author:
            meta["author"] = args.author
        if args.subject:
            meta["subject"] = args.subject
        if args.keywords:
            meta["keywords"] = args.keywords
        extras.edit_metadata(args.file, out, meta)
        print(f"Metadata updated → {out}")

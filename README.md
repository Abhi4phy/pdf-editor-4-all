# PDF Editor 4 All

A feature-rich PDF editor for everyone — with both a **GUI** (ttkbootstrap) and **CLI** interface.  
Merge, split, compress, encrypt, convert, watermark, preview, batch-process, compare, and more — all from a single tool.

![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## Features

| Category | Operations |
|---|---|
| **Preview** | Built-in PDF viewer with zoom & page navigation |
| **Basic** | Merge PDFs, Extract Pages, Rotate, Add Watermark |
| **Advanced** | Compress (low/medium/high quality), Add Page Numbers, Header/Footer, Split, Manage Bookmarks |
| **Convert** | PDF → Word (.docx), PDF → Images (PNG), PDF → Text, Images → PDF |
| **Security** | Encrypt with Password, Remove Password |
| **Signature** | Place a signature image on any page with visual positioning |
| **Batch Ops** | Run any operation on multiple files at once with progress tracking |
| **Reorder / Delete** | Drag-and-drop page reordering, delete selected pages |
| **Compare** | Side-by-side visual + text comparison of two PDFs |
| **Metadata** | View and edit title, author, subject, keywords |

### GUI Highlights

- **Dark Mode** — Toggle between light (cosmo) and dark (darkly) themes
- **Drag & Drop** — Drop PDF files onto the window (requires `tkinterdnd2`)
- **Recent Files** — Quick access to recently opened files (persisted across sessions)
- **Progress Bar** — Visual feedback for long-running operations
- **Undo / History** — Roll back the last file operation with automatic backups
- **In-App Guidance** — Every tab shows step-by-step instructions so you always know what to do

---

## Installation

### From source (recommended)

```bash
git clone https://github.com/abhi4phy/pdf-editor-4-all.git
cd pdf-editor-4-all
pip install -e .
```

### Dependencies only

```bash
pip install -r requirements.txt
```

### Optional extras

```bash
pip install tkinterdnd2   # Native drag-and-drop support in the GUI
```

---

## Usage

### GUI Mode

```bash
# After installing the package
pdf-editor --gui

# Or via module (no install needed)
python -m pdf_editor --gui
```

### CLI Mode

Every operation is available as a sub-command:

```bash
# Merge multiple PDFs
pdf-editor merge file1.pdf file2.pdf file3.pdf -o merged.pdf

# Split a PDF into individual pages
pdf-editor split input.pdf -o ./output_pages/

# Extract specific pages
pdf-editor extract input.pdf -p "1,3-5,8" -o extracted.pdf

# Rotate all pages
pdf-editor rotate input.pdf -a 90 -o rotated.pdf

# Compress a PDF (default: medium quality)
pdf-editor compress input.pdf -o compressed.pdf

# Compress with quality level: low (fast, lossless), medium (balanced), high (smallest)
pdf-editor compress input.pdf -o compressed.pdf -q high

# Add page numbers
pdf-editor page-numbers input.pdf -o numbered.pdf --position bottom-center

# Add header and footer
pdf-editor header-footer input.pdf -o output.pdf --header "My Document" --footer "Confidential"

# Encrypt with password
pdf-editor encrypt input.pdf -p "mysecretpass" -o encrypted.pdf

# Remove password protection
pdf-editor decrypt encrypted.pdf -p "mysecretpass" -o decrypted.pdf

# Add a watermark
pdf-editor watermark input.pdf -w watermark.pdf -o watermarked.pdf

# Convert to Word
pdf-editor convert input.pdf -f docx -o output.docx

# Convert to images (300 DPI)
pdf-editor convert input.pdf -f images -o ./images/ --dpi 300

# Convert to text
pdf-editor convert input.pdf -f text -o output.txt

# Show PDF metadata
pdf-editor info input.pdf

# Convert images to a single PDF
pdf-editor images-to-pdf img1.png img2.jpg -o album.pdf

# Reorder pages (move page 3 first, then 1, then 2)
pdf-editor reorder input.pdf -o reordered.pdf -p "3,1,2"

# Delete specific pages
pdf-editor delete-pages input.pdf -o trimmed.pdf -p "2,5"

# View metadata
pdf-editor metadata input.pdf

# Edit metadata
pdf-editor metadata input.pdf -o updated.pdf --title "My Doc" --author "Jane"
```

---

## Project Structure

```
pdf-editor-4-all/
├── pyproject.toml          # Package metadata & build config
├── requirements.txt        # Dependencies
├── run.py                  # Quick launcher (no install needed)
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   └── pdf_editor/
│       ├── __init__.py     # Version & app name
│       ├── __main__.py     # Entry point (CLI arg parsing)
│       ├── app.py          # GUI application (ttkbootstrap, 10 tabs)
│       ├── cli.py          # CLI command dispatcher
│       ├── utils.py        # Shared helpers, decorators, logging
│       ├── history.py      # Recent files & undo/operation history
│       └── operations/
│           ├── __init__.py
│           ├── basic.py    # Merge, extract, rotate, watermark
│           ├── advanced.py # Compress, page numbers, header/footer, split, bookmarks
│           ├── converter.py# PDF → Word / Images / Text
│           ├── security.py # Encrypt, remove password
│           ├── forms.py    # Digital signature placement
│           └── extras.py   # Images→PDF, reorder, delete, metadata, compare
└── tests/
    ├── __init__.py
    ├── test_basic.py
    ├── test_advanced.py
    ├── test_converter.py
    └── test_security.py
```

---

## Architecture

The project follows a clean **separation of concerns**:

- **`operations/`** — Pure business logic. No UI dependencies. Each function takes file paths and parameters, performs the PDF operation, and returns the result. Fully testable and reusable.
- **`app.py`** — GUI layer (10 tabs). Thin callbacks that collect user input via dialogs, delegate to `operations.*`, and display results. Supports dark mode, drag & drop, progress bars, and undo.
- **`cli.py`** — CLI layer. Maps 16 argparse sub-commands to the same `operations.*` functions.
- **`history.py`** — Recent-files persistence and in-memory operation history with file-backup undo.
- **`utils.py`** — Cross-cutting concerns: input validation decorators, page-range parsing, PDF metadata reading, logging setup.

---

## Screenshots

_Coming soon — contributions welcome!_

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome-feature`)
3. Commit your changes (`git commit -m 'Add awesome feature'`)
4. Push to the branch (`git push origin feature/awesome-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

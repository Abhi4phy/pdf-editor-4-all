"""Quick launcher — run the app without installing the package."""

import sys
import os

# Add src/ to the module search path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pdf_editor.__main__ import main

main()

# # GUI
# python run.py --gui

# # CLI
# python run.py --help
# python run.py compress input.pdf -o output.pdf
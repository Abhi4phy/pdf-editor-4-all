"""Recent files tracking and operation history for PDF Editor 4 All."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("pdf_editor.history")

# Persistent config location
_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".pdf_editor_4_all")
_RECENT_FILE = os.path.join(_CONFIG_DIR, "recent_files.json")
_MAX_RECENT = 15


# ═════════════════════════════════════════════════════════════════════════════
#  Recent Files
# ═════════════════════════════════════════════════════════════════════════════

def _ensure_config_dir():
    os.makedirs(_CONFIG_DIR, exist_ok=True)


def get_recent_files() -> List[Dict[str, str]]:
    """Return list of recent files, newest first.

    Each entry: ``{"path": str, "timestamp": str}``
    """
    if not os.path.isfile(_RECENT_FILE):
        return []
    try:
        with open(_RECENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Remove entries whose files no longer exist
        return [e for e in data if os.path.isfile(e.get("path", ""))]
    except Exception:
        return []


def add_recent_file(path: str) -> None:
    """Add a file path to the recent files list."""
    _ensure_config_dir()
    recents = get_recent_files()

    # Remove duplicate
    recents = [e for e in recents if e["path"] != path]

    # Add at front
    recents.insert(0, {
        "path": path,
        "timestamp": datetime.now().isoformat(),
    })

    # Trim
    recents = recents[:_MAX_RECENT]

    with open(_RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump(recents, f, indent=2)


def clear_recent_files() -> None:
    """Clear the recent files list."""
    _ensure_config_dir()
    with open(_RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)


# ═════════════════════════════════════════════════════════════════════════════
#  Operation History (in-memory, per session)
# ═════════════════════════════════════════════════════════════════════════════

class OperationHistory:
    """Track operations performed in the current session for undo / review."""

    def __init__(self, max_entries: int = 50) -> None:
        self._history: List[Dict[str, Any]] = []
        self._max = max_entries
        self._backup_dir = tempfile.mkdtemp(prefix="pdf_editor_undo_")

    @property
    def entries(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def record(
        self,
        operation: str,
        input_file: str,
        output_file: str,
        details: Optional[str] = None,
    ) -> None:
        """Record an operation and back up the input file for undo."""
        backup_path = None
        try:
            if os.path.isfile(input_file):
                backup_name = f"{len(self._history)}_{os.path.basename(input_file)}"
                backup_path = os.path.join(self._backup_dir, backup_name)
                shutil.copy2(input_file, backup_path)
        except Exception as e:
            logger.warning("Could not back up file for undo: %s", e)

        entry = {
            "id": len(self._history),
            "operation": operation,
            "input_file": input_file,
            "output_file": output_file,
            "backup_path": backup_path,
            "details": details or "",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        self._history.append(entry)

        if len(self._history) > self._max:
            old = self._history.pop(0)
            if old.get("backup_path") and os.path.isfile(old["backup_path"]):
                os.remove(old["backup_path"])

        logger.info("Recorded: %s on %s → %s", operation, input_file, output_file)

    def undo_last(self) -> Optional[Dict[str, Any]]:
        """Undo the last operation by restoring the backup file.

        Returns the entry that was undone, or None if nothing to undo.
        """
        if not self._history:
            return None

        entry = self._history.pop()
        backup = entry.get("backup_path")
        output = entry.get("output_file")

        if backup and os.path.isfile(backup) and output:
            try:
                shutil.copy2(backup, output)
                logger.info("Undone: %s → restored %s", entry["operation"], output)
            except Exception as e:
                logger.error("Undo failed: %s", e)

        return entry

    def cleanup(self) -> None:
        """Remove all backup files."""
        try:
            shutil.rmtree(self._backup_dir, ignore_errors=True)
        except Exception:
            pass

"""Reusable Action Card and Grid Components for Modern GUI."""

from __future__ import annotations

import tkinter as tk
from typing import Callable
import ttkbootstrap as ttk


class ActionCard(ttk.Frame):
    """Modern action tile card displaying icon, title, description, and primary button."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        description: str,
        button_text: str,
        command: Callable[[], None],
        icon: str = "⚙️",
        bootstyle: str = "primary",
        **kwargs,
    ) -> None:
        super().__init__(parent, padding=2, **kwargs)

        # Outer Card Container
        card = ttk.LabelFrame(self, text=f"{icon} {title}")
        card.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        inner = ttk.Frame(card, padding=8)
        inner.pack(fill=tk.BOTH, expand=True)

        # Description text with high-contrast theme-aware styling
        ttk.Label(
            inner,
            text=description,
            font=("Segoe UI", 9),
            wraplength=220,
            justify=tk.LEFT,
        ).pack(fill=tk.BOTH, expand=True, anchor=tk.NW, pady=(0, 8))

        # Action Button
        ttk.Button(
            inner,
            text=button_text,
            command=command,
            bootstyle=bootstyle,
        ).pack(fill=tk.X, side=tk.BOTTOM)


def build_card_grid(
    parent: tk.Widget,
    cards_data: list[dict],
    columns: int = 2,
) -> ttk.Frame:
    """Builds a responsive grid frame of ActionCards.
    
    cards_data item schema:
    {
        "title": str,
        "description": str,
        "button_text": str,
        "command": callable,
        "icon": str (optional),
        "bootstyle": str (optional),
    }
    """
    grid_frame = ttk.Frame(parent)
    grid_frame.pack(fill=tk.BOTH, expand=True, pady=4)

    for i in range(columns):
        grid_frame.columnconfigure(i, weight=1)

    for idx, item in enumerate(cards_data):
        row = idx // columns
        col = idx % columns

        card_widget = ActionCard(
            grid_frame,
            title=item["title"],
            description=item["description"],
            button_text=item["button_text"],
            command=item["command"],
            icon=item.get("icon", "📄"),
            bootstyle=item.get("bootstyle", "primary"),
        )
        card_widget.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

    return grid_frame


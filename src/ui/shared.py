"""Shared constants and helpers for UI components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.card_component import CardComponent
    from src.ui.column_component import ColumnComponent


@dataclass
class DragState:
    """Mutable drag state shared between column and card components."""

    drag_card: CardComponent | None = None
    drop_target: CardComponent | None = None
    drag_column: ColumnComponent | None = None


# Events
EVENT_KEYDOWN_ENTER = "keydown.enter.prevent"

# Icon button styling
ICON_BTN_OPACITY = "opacity:0.6;"
ICON_BTN_PROPS = "flat dense round size=xs"

# Thresholds
LUMINANCE_THRESHOLD = 0.45

# Opacity
OPACITY_COLUMN_DELETE = "opacity:0.5;"
OPACITY_COMPLETED_LABELED = "opacity:0.45;"
OPACITY_COMPLETED_PLAIN = "opacity:0.5;"

# Colors
COLOR_CARD_BG = "white"
COLOR_CARD_COMPLETED_BG = "#f5f5f5"
COLOR_COLUMN_BG = "#eceff1"
COLOR_COLUMN_HIGHLIGHT = "#cfd8dc"
COLOR_TEXT_DARK = "#222"
COLOR_TEXT_LIGHT = "#fff"


def contrast_color(hex_color: str) -> str:
    """Return black or white text color based on background luminance."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:  # noqa: PLR2004
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return COLOR_TEXT_DARK if luminance > LUMINANCE_THRESHOLD else COLOR_TEXT_LIGHT


# -- Prio icons & labels (used by card context menu and bulk bar) --

PRIO_ICON_SET = "flag"
PRIO_ICON_UNSET = "outlined_flag"
PRIO_ICON_CLEAR = "flag_circle"

# -- Repeat icons --

REPEAT_ICON_SET = "repeat"
REPEAT_ICON_UNSET = "remove_circle_outline"

# -- Label icons --

LABEL_ICON_REMOVE = "label_off"

# -- Completed card cutoff --
COMPLETED_CUTOFF_DAYS = 14


PRIO_CHOICES: list[tuple[bool | None, str, str]] = [
    (True, PRIO_ICON_SET, "Mark Important"),
    (False, PRIO_ICON_UNSET, "Mark Not Important"),
    (None, PRIO_ICON_CLEAR, "Remove Prio"),
]


def prio_choices(current: bool | None) -> list[tuple[bool | None, str, str]]:  # noqa: FBT001
    """Return (value, icon, label) for each prio option except current."""
    return [(v, i, lb) for v, i, lb in PRIO_CHOICES if v is not current]

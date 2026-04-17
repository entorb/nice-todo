"""Shared constants and helpers for UI components."""

# Events
_EVENT_KEYDOWN_ENTER = "keydown.enter"

# Icon button styling
_ICON_BTN_OPACITY = "opacity:0.6;"
_ICON_BTN_PROPS = "flat dense round size=xs"

# Thresholds
_LUMINANCE_THRESHOLD = 0.45

# Opacity
_OPACITY_COLUMN_DELETE = "opacity:0.5;"
_OPACITY_COMPLETED_LABELED = "opacity:0.45;"
_OPACITY_COMPLETED_PLAIN = "opacity:0.5;"

# Colors
_COLOR_CARD_BG = "white"
_COLOR_CARD_COMPLETED_BG = "#f5f5f5"
_COLOR_COLUMN_BG = "#eceff1"
_COLOR_COLUMN_HIGHLIGHT = "#cfd8dc"
_COLOR_TEXT_DARK = "#222"
_COLOR_TEXT_LIGHT = "#fff"


def _contrast_color(hex_color: str) -> str:
    """Return black or white text color based on background luminance."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:  # noqa: PLR2004
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return _COLOR_TEXT_DARK if luminance > _LUMINANCE_THRESHOLD else _COLOR_TEXT_LIGHT


# -- Prio icons & labels (used by card context menu and bulk bar) --

PRIO_ICON_SET = "flag"
PRIO_ICON_UNSET = "outlined_flag"
PRIO_ICON_CLEAR = "flag_circle"

# -- Template icons --

TEMPLATE_ICON_SET = "push_pin"
TEMPLATE_ICON_UNSET = "remove_circle_outline"

# -- Label icons --

LABEL_ICON_REMOVE = "label_off"


def prio_action_icon(current: bool | None) -> str:  # noqa: FBT001
    """Return icon representing the action (what clicking will set)."""
    if current is True:
        return PRIO_ICON_UNSET
    if current is False:
        return PRIO_ICON_CLEAR
    return PRIO_ICON_SET


def prio_action_label(current: bool | None) -> str:  # noqa: FBT001
    """Return menu label for the prio action."""
    if current is True:
        return "Mark Not Important"
    if current is False:
        return "Clear Flag"
    return "Mark Important"


def next_prio(current: bool | None) -> bool | None:  # noqa: FBT001
    """Cycle prio: True -> False -> None -> True."""
    if current is True:
        return False
    if current is False:
        return None
    return True

"""Dialog components for the TODO board."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.models import Board, Column, Label


def confirm_dialog(message: str, on_confirm: Callable[[], None]) -> ui.dialog:
    """Show a confirmation dialog with Cancel/Confirm buttons."""
    with ui.dialog() as dialog, ui.card().classes("p-4"):
        ui.label(message).classes("text-body1")
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Confirm",
                on_click=lambda: (on_confirm(), dialog.close()),
            ).props("color=negative")
    dialog.open()
    return dialog


def label_editor_dialog(
    label: Label | None,
    on_save: Callable[[str, str], None],
) -> ui.dialog:
    """Show a create/edit label dialog with name input and color picker."""
    is_edit = label is not None
    title = "Edit Label" if is_edit else "Create Label"
    initial_name = label.name if is_edit else ""
    initial_color = label.color if is_edit else "#cccccc"

    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[300px]"):
        ui.label(title).classes("text-h6")
        name_input = ui.input(
            label="Name",
            value=initial_name,
        ).classes("w-full")
        color_input = ui.color_input(
            label="Color",
            value=initial_color,
        ).classes("w-full")
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Save",
                on_click=lambda: _save_label(dialog, name_input, color_input, on_save),
            ).props("color=primary")
    dialog.open()
    return dialog


def _save_label(
    dialog: ui.dialog,
    name_input: ui.input,
    color_input: ui.color_input,
    on_save: Callable[[str, str], None],
) -> None:
    """Validate and save label from the editor dialog."""
    name = (name_input.value or "").strip()
    color = (color_input.value or "#cccccc").lower()
    if not color.startswith("#"):
        color = "#cccccc"
    if not name:
        ui.notify("Label name is required", type="warning")
        return
    on_save(name, color)
    dialog.close()


def export_dialog(markdown: str) -> ui.dialog:
    """Show generated markdown with a copy-to-clipboard button."""
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[400px]"):
        ui.label("Export").classes("text-h6")
        textarea = (
            ui.textarea(
                value=markdown,
            )
            .classes("w-full font-mono")
            .props("readonly autogrow")
        )
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(
                "Copy to clipboard",
                icon="content_copy",
                on_click=lambda: _copy_to_clipboard(textarea.value or ""),
            ).props("color=primary")
            ui.button("Close", on_click=dialog.close).props("flat")
    dialog.open()
    return dialog


async def _copy_to_clipboard(text: str) -> None:
    """Copy text to clipboard via browser JS."""
    escaped = text.replace("\\", "\\\\").replace("`", "\\`")
    await ui.run_javascript(f"navigator.clipboard.writeText(`{escaped}`)")
    ui.notify("Copied to clipboard", type="positive")


def rename_board_dialog(
    current_name: str,
    current_key: str,
    on_save: Callable[[str, str], None],
    validate_key: Callable[[str], str | None],
) -> ui.dialog:
    """Show a dialog to rename the board and edit its key."""
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[300px]"):
        ui.label("Rename Board").classes("text-h6")
        name_input = ui.input(label="Board Name", value=current_name).classes("w-full")
        key_input = ui.input(label="Board Key", value=current_key).classes("w-full")
        error_label = ui.label("").classes("text-negative text-caption")
        error_label.set_visibility(False)
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Save",
                on_click=lambda: _save_rename_board(
                    dialog, name_input, key_input, error_label, on_save, validate_key
                ),
            ).props("color=primary")
    dialog.open()
    return dialog


def _save_rename_board(  # noqa: PLR0913
    dialog: ui.dialog,
    name_input: ui.input,
    key_input: ui.input,
    error_label: ui.label,
    on_save: Callable[[str, str], None],
    validate_key: Callable[[str], str | None],
) -> None:
    """Validate and save the board name and key."""
    name = (name_input.value or "").strip()
    if not name:
        error_label.text = "Board name is required"
        error_label.set_visibility(True)
        return
    new_key = (key_input.value or "").strip()
    error = validate_key(new_key)
    if error:
        error_label.text = error
        error_label.set_visibility(True)
        return
    on_save(name, new_key)
    dialog.close()


def export_scope_dialog(on_export: Callable[[bool], None]) -> ui.dialog:
    """Show a dialog to choose export scope (all or completed only)."""
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[300px]"):
        ui.label("Export").classes("text-h6")
        scope = ui.toggle(
            {False: "All Cards", True: "Completed Only"},
            value=False,
        ).classes("w-full")
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Export",
                on_click=lambda: (dialog.close(), on_export(scope.value)),
            ).props("color=primary")
    dialog.open()
    return dialog


def delete_cards_dialog(on_delete: Callable[[bool], None]) -> ui.dialog:
    """Show a dialog to choose which cards to delete."""
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[300px]"):
        ui.label("Delete Cards").classes("text-h6")
        scope = ui.toggle(
            {True: "Finished Only", False: "All Cards"},
            value=True,
        ).classes("w-full")
        ui.label("Non-template cards will be deleted.").classes(
            "text-caption text-grey"
        )
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Delete",
                on_click=lambda: (dialog.close(), on_delete(scope.value)),
            ).props("color=negative")
    dialog.open()
    return dialog


def pick_board_dialog(
    boards: list[Board],
    on_select: Callable[[Board], None],
) -> ui.dialog:
    """Show a dialog to pick a target board."""
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[300px]"):
        ui.label("Move to Board").classes("text-h6")
        for b in boards:
            ui.button(
                b.name,
                on_click=lambda _, board=b: (dialog.close(), on_select(board)),
            ).classes("w-full").props("flat align=left").style("text-transform:none;")
        ui.separator()
        ui.button("Cancel", on_click=dialog.close).props("flat").classes("w-full")
    dialog.open()
    return dialog


def pick_column_dialog(
    columns: list[Column],
    on_select: Callable[[int, ui.dialog], None],
) -> ui.dialog:
    """Show a dialog to pick a target column."""
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[300px]"):
        ui.label("Pick Target Column").classes("text-h6")
        for col in columns:
            ui.button(
                col.name,
                on_click=lambda _, cid=col.id: on_select(cid, dialog),
            ).classes("w-full").props("flat align=left").style("text-transform:none;")
        ui.separator()
        ui.button("Cancel", on_click=dialog.close).props("flat").classes("w-full")
    dialog.open()
    return dialog

"""Board page - main NiceGUI page rendering the Kanban board."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import app, ui

from src.services.export_service import export as _export
from src.ui import dialogs
from src.ui.column_component import ColumnComponent
from src.ui.shared import (
    COMPLETED_CUTOFF_DAYS,
    LABEL_ICON_REMOVE,
    PRIO_CHOICES,
    REPEAT_ICON_SET,
    DragState,
)

if TYPE_CHECKING:
    from src.database import Database
    from src.models import Board, Card, Label
    from src.ui.card_component import CardComponent


def _init_polyfill() -> str:
    """Return touch-drag polyfill script tag."""
    lines = [
        "(function() {",
        "var dragEl=null,lastOver=null;",
        "document.addEventListener('touchstart',function(e){",
        "var h=e.target.closest('.cursor-grab');if(!h)return;",
        "var c=h.closest('.nicegui-card,.q-card')||h.closest('[draggable]');",
        "if(!c)return;c.setAttribute('draggable','true');dragEl=c;",
        "c.dispatchEvent(new Event('dragstart',{bubbles:true}));",
        "},{passive:true});",
        "document.addEventListener('touchmove',function(e){",
        "if(!dragEl)return;e.preventDefault();var t=e.touches[0];",
        "var el=document.elementFromPoint(t.clientX,t.clientY);",
        "if(el&&el!==lastOver){lastOver=el;",
        "el.dispatchEvent(new Event('dragover',{bubbles:true,cancelable:true}));}",
        "},{passive:false});",
        "document.addEventListener('touchend',function(e){",
        "if(!dragEl)return;var t=e.changedTouches[0];",
        "var el=document.elementFromPoint(t.clientX,t.clientY);",
        "if(el)el.dispatchEvent(new Event('drop',{bubbles:true}));",
        "dragEl.removeAttribute('draggable');dragEl=null;lastOver=null;",
        "},{passive:true});",
        "})();",
    ]
    return "<scr" + "ipt>" + "\n".join(lines) + "</scr" + "ipt>"


_PAGE_STYLE = (
    "<style>"
    "body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%) !important;"
    "background-attachment:fixed !important;min-height:100vh;}"
    ".nicegui-content{padding:16px 24px !important;}"
    "@media(max-width:600px){"
    ".board-columns{flex-direction:column !important;flex-wrap:nowrap !important;}"
    ".board-columns .board-col{min-width:100% !important;max-width:100% !important;}"
    ".nicegui-content{padding:8px 8px !important;}"
    "}"
    ".board-switcher .q-field__native{min-height:unset !important;"
    "padding:0 !important;line-height:1.4 !important;}"
    ".board-switcher .q-field__control{height:auto !important;"
    "min-height:unset !important;padding:0 4px !important;}"
    ".board-switcher .q-field__marginal{height:auto !important;}"
    ".card-dark .q-btn,.card-dark .q-icon,"
    ".card-dark .q-field__native,.card-dark .q-checkbox__inner{color:#222 !important}"
    ".card-light .q-btn,.card-light .q-icon,"
    ".card-light .q-field__native,.card-light .q-checkbox__inner{color:#fff !important}"
    "</style>"
)


_BULK_BTN_STYLE = "border-radius:16px;text-transform:none;"


class BoardPageController:
    """Encapsulates board page state and event handlers."""

    def __init__(
        self,
        key: str,
        db: Database,
    ) -> None:
        """Set up controller state."""
        self._key = key
        self._db = db
        self._board: Board | None = None
        self._labels: list[Label] = []
        self._bulk_active = False
        self._bulk_selected: set[int] = set()
        self._card_components: dict[int, CardComponent] = {}
        self._column_components: dict[int, ColumnComponent] = {}
        self._boards_cache: list[Board] | None = None
        self._drag_state = DragState()
        self._container = ui.element("div").classes("w-full")

    @property
    def _board_required(self) -> Board:
        """Return loaded board; handlers only run on a board page."""
        assert self._board is not None
        return self._board

    @property
    def _board_id_required(self) -> int:
        """Return board id; boards are always persisted after creation."""
        board = self._board_required
        assert board.id is not None
        return board.id

    # -- lifecycle --

    def load_and_render(self) -> None:
        """Load data and perform initial render."""
        self._reload_data()
        self._touch_last_login_if_needed()
        with self._container:
            self._render_board()

    def _touch_last_login_if_needed(self) -> None:
        """
        Record last_login only on first login, board create, or board switch.

        Skipped for plain reloads of the same board and for card modifications
        (which re-render via _refresh without touching last_login).
        """
        board = self._board
        if board is None or board.id is None:
            return
        is_first_login = board.last_login is None
        is_board_switch = app.storage.tab.get("last_board_key") != self._key
        if is_first_login or is_board_switch:
            self._db.touch_last_login(board.id)
        app.storage.tab["last_board_key"] = self._key

    def _refresh(self) -> None:
        self._reload_data()
        self._container.clear()
        with self._container:
            self._render_board()

    def _reload_data(self) -> None:
        board = self._db.get_board_by_key(self._key)
        if board is not None:
            self._board = board
        self._labels = self._db.get_labels()

    # -- render --

    def _render_board(self) -> None:
        assert self._board is not None
        self._render_heading()
        self._render_bulk_bar()
        self._render_columns()

    def _render_heading(self) -> None:
        with ui.row().classes("items-center gap-3 q-mb-md"):
            self._render_board_switcher()
            ui.button(
                icon="checklist",
                on_click=self._on_toggle_bulk,
            ).props("flat dense round").classes("text-white").tooltip("Bulk edit mode")
            ui.button(
                icon="swap_vert",
                on_click=self._on_sort_cards_by_prio_label_name,
            ).props("flat dense round").classes("text-white").tooltip(
                "Sort cards (prio / label / title)"
            )
            ui.button(
                icon="calendar_month",
                on_click=self._on_sort_cards_by_date,
            ).props("flat dense round").classes("text-white").tooltip(
                "Sort cards by date"
            )
            ui.button(
                icon="sync",
                on_click=self._refresh,
            ).props("flat dense round").classes("text-white").tooltip(
                "Sync from server"
            )
            with (
                ui.button(icon="more_vert")
                .props("flat dense round")
                .classes("text-white")
                .tooltip("Board actions"),
                ui.menu(),
            ):
                self._render_menu()

    def _render_board_switcher(self) -> None:
        """Render a dropdown to quickly switch between boards."""
        all_boards = self._boards_cache
        if all_boards is None:
            all_boards = self._db.get_all_boards()
            self._boards_cache = all_boards
        if len(all_boards) <= 1:
            ui.label(self._board_required.name).classes("text-h5").style(
                "font-weight:700;color:white;letter-spacing:-0.5px;"
            )
            return
        options = {b.key: b.name for b in all_boards}
        ui.select(
            options=options,
            value=self._key,
            on_change=lambda e: ui.navigate.to(f"/?key={e.value}"),
        ).props('dense borderless dark color="white"').classes(
            "text-white board-switcher",
        ).style(
            "min-width:140px;font-weight:700;font-size:1.5rem;letter-spacing:-0.5px;"
        ).tooltip("Switch board")

    def _render_menu(self) -> None:
        ui.menu_item("Rename Board", on_click=self._on_rename_board)
        ui.menu_item("New Board", on_click=self._on_new_board)
        ui.menu_item("Add Column", on_click=self._on_add_column)
        ui.separator()
        ui.menu_item("Manage Labels", on_click=self._on_manage_labels)
        ui.separator()
        ui.menu_item("Export", on_click=self._on_export)
        ui.menu_item("Delete Cards", on_click=self._on_delete_cards)
        ui.separator()
        ui.menu_item("Logout", on_click=lambda: ui.navigate.to("/logout"))

    def _render_bulk_bar(self) -> None:
        if not self._bulk_active:
            return
        _btn = "flat dense round"
        _btn_style = "color:white !important;"
        _unset_btn = "dense round"
        _unset_style = (
            "background-color:rgba(255,255,255,0.25) !important;color:white !important;"
        )
        with ui.row().classes("items-center gap-1 q-mb-md flex-wrap"):
            ui.icon("checklist").classes("text-white")
            ui.label("Select cards, then:").classes("text-body2 text-white")

            # Repeat
            ui.button(
                icon=REPEAT_ICON_SET,
                on_click=lambda: self._on_bulk_repeat(is_repeat=True),
            ).props(_btn).style(_btn_style).tooltip("Set repeat")
            ui.button(
                icon=REPEAT_ICON_SET,
                on_click=lambda: self._on_bulk_repeat(is_repeat=False),
            ).props(_unset_btn).style(_unset_style).tooltip("Unset repeat")

            ui.separator().props("vertical")

            # Prio
            _prio_props = {True: f"{_btn} color=red", False: _btn, None: _unset_btn}
            _prio_style = {True: "", False: _btn_style, None: _unset_style}
            for pv, p_icon, p_label in PRIO_CHOICES:
                ui.button(
                    icon=p_icon,
                    on_click=lambda _, v=pv: self._on_bulk_prio(prio=v),
                ).props(_prio_props[pv]).style(_prio_style[pv]).tooltip(p_label)

            ui.separator().props("vertical")

            # Label buttons (colored chips)
            for lbl in self._labels:
                ui.button(
                    lbl.name,
                    on_click=lambda _, lid=lbl.id: self._on_bulk_label(lid),
                ).style(
                    f"background-color:{lbl.color} !important;"
                    "color:white !important;"
                    f"{_BULK_BTN_STYLE}font-weight:500;"
                )
            if self._labels:
                ui.button(
                    icon=LABEL_ICON_REMOVE,
                    on_click=lambda: self._on_bulk_label(None),
                ).props(_unset_btn).style(_unset_style).tooltip("Remove label")

            ui.separator().props("vertical")

            ui.button(
                icon="close",
                on_click=self._on_toggle_bulk,
            ).props(_btn).style(_btn_style).tooltip("Cancel bulk edit")

    def _render_columns(self) -> None:
        self._card_components = {}
        self._column_components = {}
        cbs = {
            "on_toggle_completed": self._on_toggle_completed,
            "on_toggle_repeat": self._on_toggle_repeat,
            "on_toggle_prio": self._on_toggle_prio,
            "on_edit_title": self._on_edit_title,
            "on_delete": self._on_delete_card,
            "on_select": self._on_select_card,
            "on_set_label": self._on_set_card_label,
            "on_move_copy": self._on_move_copy,
            "available_labels": self._labels,
            "on_mount": self._on_card_mount,
        }
        with (
            ui.row()
            .classes("items-start gap-3 flex-nowrap overflow-x-auto board-columns")
            .style("min-height:400px;padding-bottom:16px;")
        ) as columns_row:
            self._columns_container = columns_row
            for col in self._board_required.columns:
                comp = ColumnComponent(
                    col,
                    drag_state=self._drag_state,
                    labels=self._labels,
                    on_rename=self._on_rename_column,
                    on_add_card=self._on_add_card,
                    on_delete_column=self._on_delete_column,
                    on_drop_card=self._on_drop_card,
                    on_drop_column=self._on_drop_column,
                    card_callbacks=cbs,
                    bulk_mode=self._bulk_active,
                )
                if col.id is not None:
                    self._column_components[col.id] = comp

    # -- column handlers --

    def _on_add_column(self) -> None:
        self._db.create_column(self._board_id_required)
        self._refresh()

    def _on_rename_column(self, column_id: int, name: str) -> None:
        error = self._db.update_column_name(column_id, name, self._board_id_required)
        if error:
            ui.notify(error, type="warning")
            self._refresh()

    def _on_delete_column(self, column_id: int) -> None:
        def do_delete() -> None:
            self._db.delete_column(column_id)
            self._refresh()

        dialogs.confirm_dialog("Delete this column and all its cards?", do_delete)

    # -- card handlers --

    def _on_add_card(self, column_id: int, title: str) -> None:
        col_comp = self._column_components.get(column_id)
        if col_comp is None:
            pos = len(self._db.get_cards(column_id))
            self._db.create_card(column_id, title, pos)
            self._refresh()
        else:
            pos = len(col_comp.column_data.cards)
            card = self._db.create_card(column_id, title, pos)
            col_comp.column_data.cards.append(card)
            col_comp.add_card(card)
        ui.run_javascript(
            f"""setTimeout(function() {{
                var q = '.add-card-input-col-{column_id} input';
                var el = document.querySelector(q);
                if (el) el.focus();
            }}, 200)"""
        )

    def _on_edit_title(self, card_id: int, title: str) -> None:
        self._db.update_card_title(card_id, title)

    def _on_set_card_label(self, card_id: int, label_id: int | None) -> None:
        self._db.update_card_label(card_id, label_id)
        cc = self._card_components.get(card_id)
        if cc:
            cc.card_data.label_id = label_id
            new_label = next((lbl for lbl in self._labels if lbl.id == label_id), None)
            cc.set_label(new_label)

    def _on_toggle_completed(self, card_id: int, is_completed: bool) -> None:  # noqa: FBT001
        """Save card completion (UI already updated optimistically)."""
        self._db.update_card_completed(card_id, is_completed=is_completed)

    def _on_toggle_repeat(self, card_id: int, is_repeat: bool) -> None:  # noqa: FBT001
        self._db.update_card_repeat(card_id, is_repeat=is_repeat)
        cc = self._card_components.get(card_id)
        if cc:
            cc.card_data.is_repeat = is_repeat
            cc.sync_visuals()

    def _on_toggle_prio(self, card_id: int, prio: bool | None) -> None:  # noqa: FBT001
        self._db.update_card_prio(card_id, prio)
        cc = self._card_components.get(card_id)
        if cc:
            cc.card_data.prio = prio
            cc.sync_visuals()

    def _on_delete_card(self, card_id: int) -> None:
        self._db.delete_card(card_id)
        cc = self._card_components.pop(card_id, None)
        if cc is None:
            self._refresh()
            return
        cc.delete()
        for col in self._board_required.columns:
            col.cards[:] = [c for c in col.cards if c.id != card_id]

    def _on_drop_card(
        self,
        card_id: int,
        target_column_id: int,
        position: int,
    ) -> None:
        self._db.move_card(card_id, target_column_id, position)
        moved: Card | None = None
        for col in self._board_required.columns:
            for i, c in enumerate(col.cards):
                if c.id == card_id:
                    moved = col.cards.pop(i)
                    break
            if moved is not None:
                break
        if moved is None:
            self._refresh()
            return
        moved.column_id = target_column_id
        moved.position = position
        for col in self._board_required.columns:
            if col.id == target_column_id:
                col.cards.insert(position, moved)
                break

    def _on_drop_column(self, src_id: int, tgt_id: int) -> None:
        col_ids = [c.id for c in self._board_required.columns if c.id is not None]
        if src_id in col_ids and tgt_id in col_ids:
            col_ids.remove(src_id)
            tgt_idx = col_ids.index(tgt_id)
            col_ids.insert(tgt_idx, src_id)
            positions = [(cid, idx) for idx, cid in enumerate(col_ids)]
            self._db.update_column_positions(positions)
            by_id = {c.id: c for c in self._board_required.columns}
            self._board_required.columns[:] = [by_id[cid] for cid in col_ids]
            for idx, cid in enumerate(col_ids):
                col_comp = self._column_components.get(cid)
                if col_comp is not None:
                    col_comp.column_data.position = idx
            src_comp = self._column_components.get(src_id)
            if src_comp is not None and self._columns_container is not None:
                src_comp.move(
                    target_container=self._columns_container,
                    target_index=tgt_idx,
                )

    def _on_card_mount(self, card_id: int, component: CardComponent) -> None:
        """Register a card component for targeted visual updates."""
        self._card_components[card_id] = component

    def _on_select_card(self, card_id: int, selected: bool) -> None:  # noqa: FBT001
        if selected:
            self._bulk_selected.add(card_id)
        else:
            self._bulk_selected.discard(card_id)

    # -- move / copy --

    def _on_move_copy(self, card_id: int, action: str) -> None:
        source_col_name = self._find_card_column_name(card_id)
        # Load boards with columns eagerly (no card trees) for the dialog
        loaded_boards = [
            b
            for b in self._db.get_boards_with_columns()
            if b.id != self._board_id_required and b.columns
        ]

        def on_confirm(col_id: int, act: str) -> None:
            if act == "move":
                self._db.move_card(card_id, col_id, len(self._db.get_cards(col_id)))
                ui.notify("Card moved", type="positive")
            else:
                self._db.copy_card(card_id, col_id, len(self._db.get_cards(col_id)))
                ui.notify("Card copied", type="positive")
            self._refresh()

        dialogs.move_copy_dialog(
            action,
            loaded_boards,
            self._board_required,
            source_col_name,
            on_confirm,
        )

    def _find_card_column_name(self, card_id: int) -> str | None:
        for col in self._board_required.columns:
            for c in col.cards:
                if c.id == card_id:
                    return col.name
        return None

    # -- bulk handlers --

    def _on_toggle_bulk(self) -> None:
        self._bulk_active = not self._bulk_active
        self._bulk_selected = set()
        self._refresh()

    def _on_bulk_label(self, label_id: int | None) -> None:
        if self._bulk_selected:
            self._db.bulk_set_label(list(self._bulk_selected), label_id)
            self._bulk_selected = set()
            self._bulk_active = False
            self._refresh()

    def _on_bulk_repeat(self, *, is_repeat: bool) -> None:
        if self._bulk_selected:
            self._db.bulk_set_repeat(
                list(self._bulk_selected),
                is_repeat=is_repeat,
            )
            self._bulk_selected = set()
            self._bulk_active = False
            self._refresh()

    def _on_bulk_prio(self, *, prio: bool | None) -> None:
        if self._bulk_selected:
            self._db.bulk_set_prio(
                list(self._bulk_selected),
                prio,
            )
            self._bulk_selected = set()
            self._bulk_active = False
            self._refresh()

    # -- board-level handlers --

    def _on_sort_cards_by_prio_label_name(self) -> None:
        self._db.sort_cards_by_prio_label_name(self._board_required, self._labels)
        self._refresh()

    def _on_sort_cards_by_date(self) -> None:
        self._db.sort_cards_by_date(self._board_required)
        self._refresh()

    def _on_export(self) -> None:
        def on_export(completed_only: bool, fmt: str) -> str | None:  # noqa: FBT001
            fresh = self._db.get_board_by_key(self._key)
            if fresh:
                return _export(
                    fresh,
                    self._labels,
                    completed_only=completed_only,
                    fmt=fmt,
                )
            return None

        dialogs.export_scope_dialog(on_export)

    def _on_delete_cards(self) -> None:
        def on_repeat(card_id: int) -> None:
            self._db.update_card_repeat(card_id, is_repeat=True)
            # Reload board data so the preview reflects the change
            self._reload_data()

        def on_delete(mode: str) -> None:
            if mode == "all":
                self._db.delete_all_non_repeat_cards(self._board_id_required)
            elif mode == "2w":
                self._db.delete_completed_non_repeat_cards_older_than(
                    self._board_id_required, days=COMPLETED_CUTOFF_DAYS
                )
            else:
                self._db.delete_completed_non_repeat_cards(self._board_id_required)
            self._refresh()

        dialogs.delete_cards_dialog(lambda: self._board_required, on_repeat, on_delete)

    def _on_manage_labels(self) -> None:
        """Open label management dialog."""

        def on_create(name: str, color: str) -> None:
            result = self._db.create_label(name, color)
            if isinstance(result, str):
                ui.notify(result, type="warning")
            else:
                self._refresh()

        def on_update(lid: int, name: str, color: str) -> None:
            error = self._db.update_label(lid, name, color)
            if error:
                ui.notify(error, type="warning")
            else:
                self._refresh()

        with ui.dialog() as dlg, ui.card().classes("p-4 min-w-[350px]"):
            ui.label("Manage Labels").classes("text-h6")
            for lbl in self._labels:
                if lbl.id is None:
                    continue
                with ui.row().classes("items-center w-full gap-2"):
                    ui.html(
                        '<span style="display:inline-block;width:16px;height:16px;'
                        f'border-radius:50%;background:{lbl.color};"></span>'
                    )
                    ui.label(lbl.name).classes("flex-grow")
                    ui.button(
                        icon="edit",
                        on_click=lambda _, lid=lbl.id, lb=lbl: (
                            dlg.close(),
                            dialogs.label_editor_dialog(
                                lb,
                                lambda n, c, _lid=lid: on_update(_lid, n, c),
                            ),
                        ),
                    ).props("flat dense round")
                    ui.button(
                        icon="delete",
                        on_click=lambda _, lid=lbl.id: (
                            self._db.delete_label(lid),
                            dlg.close(),
                            self._refresh(),
                        ),
                    ).props("flat dense round text-negative")
            ui.separator()
            ui.button(
                "Create New Label",
                icon="add",
                on_click=lambda: (
                    dlg.close(),
                    dialogs.label_editor_dialog(None, on_create),
                ),
            ).classes("w-full")
            ui.button("Close", on_click=dlg.close).props("flat").classes(
                "w-full",
            )
        dlg.open()

    def _on_rename_board(self) -> None:
        def on_save(new_name: str, new_key: str) -> None:
            name = self._validate_board_name(new_name)
            if name is None:
                return
            key_error = self._db.update_board_key(self._board_id_required, new_key)
            if key_error:
                ui.notify(key_error, type="warning")
                return
            self._db.update_board_name(self._board_id_required, name)
            ui.navigate.to(f"/?key={new_key}")

        def validate_key(key: str) -> str | None:
            return self._db.validate_board_key(key, exclude_id=self._board_id_required)

        dialogs.rename_board_dialog(
            self._board_required.name,
            self._board_required.key,
            on_save,
            validate_key,
        )

    @staticmethod
    def _validate_board_name(raw: str) -> str | None:
        name = raw.strip()
        if not name:
            ui.notify("Board name is required", type="warning")
            return None
        return name

    def _on_new_board(self) -> None:
        def on_save(name: str, new_key: str) -> None:
            clean_name = self._validate_board_name(name)
            if clean_name is None:
                return
            board = self._db.add_board(new_key, clean_name)
            if isinstance(board, str):
                ui.notify(board, type="warning")
                return
            ui.navigate.to(f"/?key={board.key}")

        dialogs.rename_board_dialog(
            "",
            "",
            on_save,
            self._db.validate_board_key,
        )


def _render_board_selector(db: Database) -> None:
    """Show a list of all boards when no key is provided."""
    all_boards = db.get_all_boards()

    # if no boards in DB
    if not all_boards:
        ui.label("No boards yet").classes("text-h5 text-white q-pa-lg")
        return
    ui.label("Select Board").classes("text-h5").style(
        "font-weight:700;color:white;letter-spacing:-0.5px;"
    )
    with ui.column().classes("gap-2 q-mt-md"):
        for b in all_boards:
            ui.button(
                b.name,
                on_click=lambda _, bk=b.key: ui.navigate.to(f"/?key={bk}"),
            ).props("flat align=left").classes("text-white").style(
                "text-transform:none;font-size:1.1rem;"
            )


def create_board_page(
    db: Database,
    apple_icon_url: str,
) -> None:
    """Register the NiceGUI board page route."""

    @ui.page("/")
    async def board_page(key: str = "") -> None:
        ui.colors(primary="#37474f", secondary="#546e7a", negative="#c62828")
        ui.add_head_html(_init_polyfill())
        ui.add_head_html(_PAGE_STYLE)
        ui.add_head_html(f'<link rel="apple-touch-icon" href="{apple_icon_url}">')

        # no key parameter -> board selection
        if not key:
            _render_board_selector(db)
            return

        board = db.get_board_by_key(key)

        # no board of that key
        if board is None:
            _render_board_selector(db)
            return

        ctrl = BoardPageController(key, db)
        await ui.context.client.connected()
        ctrl.load_and_render()

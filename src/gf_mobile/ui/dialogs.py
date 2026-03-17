"""
Reusable dialog helpers for mobile screens.
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional

from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem


def dismiss_dialog(dialog: Optional[MDDialog]) -> None:
    if dialog:
        dialog.dismiss()


def build_message_dialog(
    current_dialog: Optional[MDDialog],
    *,
    title: str,
    message: str,
    button_color,
) -> MDDialog:
    dismiss_dialog(current_dialog)
    dialog = MDDialog(
        title=title,
        text=message,
        buttons=[
            MDRaisedButton(
                text="Aceptar",
                md_bg_color=button_color,
                on_release=lambda *_: dialog.dismiss(),
            )
        ],
    )
    return dialog


def build_selection_dialog(
    current_dialog: Optional[MDDialog],
    *,
    title: str,
    options: Iterable[str],
    on_select: Callable[[str], None],
) -> MDDialog:
    dismiss_dialog(current_dialog)
    option_list = [str(option) for option in options if str(option).strip()]

    if not option_list:
        dialog = MDDialog(
            title=title,
            text="No hay opciones disponibles ahora mismo.",
            buttons=[
                MDRaisedButton(
                    text="Aceptar",
                    on_release=lambda *_: dialog.dismiss(),
                )
            ],
        )
        return dialog

    def _handle_select(value: str, dialog: MDDialog) -> None:
        dialog.dismiss()
        on_select(value)

    items = []
    for option in option_list:
        items.append(
            OneLineListItem(
                text=option,
                on_release=lambda _item, value=option: _handle_select(value, dialog),
            )
        )
    dialog = MDDialog(title=title, type="simple", items=items)
    return dialog

"""
Shared helpers for Kivy screens in the mobile shell.
"""

from __future__ import annotations

from typing import Any

from kivy.app import App

from gf_mobile.ui.theme import get_kivy_palette


def resolve_palette() -> dict[str, Any]:
    app = App.get_running_app()
    palette = getattr(app, "kivy_palette", None) if app else None
    if palette:
        return palette
    return get_kivy_palette()


def apply_palette_attrs(target: Any, mapping: dict[str, str]) -> dict[str, Any]:
    palette = resolve_palette()
    for attr_name, palette_key in mapping.items():
        current = getattr(target, attr_name, None)
        setattr(target, attr_name, palette.get(palette_key, current))
    return palette


def metric_columns_for_device(*, is_phone: bool, orientation: str) -> int:
    return 1 if is_phone and orientation == "portrait" else 2


def category_grid_cols_for_device(*, is_phone: bool, is_tablet: bool, orientation: str) -> int:
    if is_phone:
        return 3 if orientation == "portrait" else 4
    if is_tablet:
        return 4
    return 5


def list_panel_height_for_device(*, is_phone: bool, is_tablet: bool, orientation: str) -> int:
    if is_phone:
        return 260 if orientation == "portrait" else 220
    if is_tablet:
        return 320
    return 360

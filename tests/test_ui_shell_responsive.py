from gf_mobile.ui.screen_utils import (
    category_grid_cols_for_device,
    list_panel_height_for_device,
    metric_columns_for_device,
)


def test_metric_columns_phone_portrait_is_single_column() -> None:
    assert metric_columns_for_device(is_phone=True, orientation="portrait") == 1
    assert metric_columns_for_device(is_phone=True, orientation="landscape") == 2


def test_category_grid_cols_change_by_device() -> None:
    assert category_grid_cols_for_device(is_phone=True, is_tablet=False, orientation="portrait") == 3
    assert category_grid_cols_for_device(is_phone=True, is_tablet=False, orientation="landscape") == 4
    assert category_grid_cols_for_device(is_phone=False, is_tablet=True, orientation="portrait") == 4
    assert category_grid_cols_for_device(is_phone=False, is_tablet=False, orientation="landscape") == 5


def test_list_panel_height_changes_by_device() -> None:
    assert list_panel_height_for_device(is_phone=True, is_tablet=False, orientation="portrait") == 260
    assert list_panel_height_for_device(is_phone=True, is_tablet=False, orientation="landscape") == 220
    assert list_panel_height_for_device(is_phone=False, is_tablet=True, orientation="portrait") == 320
    assert list_panel_height_for_device(is_phone=False, is_tablet=False, orientation="landscape") == 360

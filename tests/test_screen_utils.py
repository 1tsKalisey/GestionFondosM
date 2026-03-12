from gf_mobile.ui.screen_utils import apply_palette_attrs


class _DummyScreen:
    primary = None
    surface = None
    missing = "keep"


def test_apply_palette_attrs_assigns_requested_colors() -> None:
    target = _DummyScreen()
    mapping = {
        "primary": "primary",
        "surface": "surface",
        "missing": "not_present",
    }

    palette = apply_palette_attrs(target, mapping)

    assert target.primary == palette["primary"]
    assert target.surface == palette["surface"]
    assert target.missing == "keep"

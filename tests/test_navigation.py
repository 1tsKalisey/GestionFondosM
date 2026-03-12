from gf_mobile.ui.navigation import PRIMARY_ROUTES, route_for_screen


def test_primary_routes_cover_core_shell_screens() -> None:
    screens = [route.screen for route in PRIMARY_ROUTES]
    assert screens == [
        "dashboard",
        "transactions",
        "categories",
        "budgets",
        "reports",
        "profile",
    ]


def test_route_for_screen_returns_expected_metadata() -> None:
    route = route_for_screen("reports")
    assert route is not None
    assert route.label == "Reportes"
    assert route.icon == "chart-bar"


def test_budget_route_uses_short_label_for_bottom_nav() -> None:
    route = route_for_screen("budgets")
    assert route is not None
    assert route.label == "Presup.."

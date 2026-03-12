"""
Shared route registry and primary navigation for the mobile shell.
"""

from dataclasses import dataclass

from kivy.lang import Builder
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.boxlayout import MDBoxLayout


@dataclass(frozen=True)
class MobileRoute:
    screen: str
    label: str
    icon: str
    subtitle: str


PRIMARY_ROUTES = (
    MobileRoute("dashboard", "Resumen", "view-dashboard", "Estado financiero y acciones"),
    MobileRoute("transactions", "Movs", "swap-horizontal", "Filtros y captura"),
    MobileRoute("categories", "Categorias", "shape", "Clasificacion y grupos"),
    MobileRoute("budgets", "Presup..", "wallet", "Limites mensuales"),
    MobileRoute("reports", "Reportes", "chart-bar", "Lectura de tendencias"),
    MobileRoute("profile", "Perfil", "account-circle", "Cuenta y preferencias"),
)

ROUTE_BY_SCREEN = {route.screen: route for route in PRIMARY_ROUTES}


Builder.load_string(
    """
#:import dp kivy.metrics.dp

<NavigationBar>:
    orientation: "horizontal"
    spacing: "4dp"
    padding: "6dp", "6dp", "6dp", "6dp"
    size_hint_y: None
    height: "76dp"

    canvas.before:
        Color:
            rgba: app.kivy_palette["surface"]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [22, 22, 0, 0]

    NavItem:
        icon: "view-dashboard"
        label: "Resumen"
        selected: root.current_screen == "dashboard"
        on_release: root.navigate_to("dashboard")
    NavItem:
        icon: "swap-horizontal"
        label: "Movs"
        selected: root.current_screen == "transactions"
        on_release: root.navigate_to("transactions")
    NavItem:
        icon: "shape"
        label: "Categorias"
        selected: root.current_screen == "categories"
        on_release: root.navigate_to("categories")
    NavItem:
        icon: "wallet"
        label: "Presup.."
        selected: root.current_screen == "budgets"
        on_release: root.navigate_to("budgets")
    NavItem:
        icon: "chart-bar"
        label: "Reportes"
        selected: root.current_screen == "reports"
        on_release: root.navigate_to("reports")
    NavItem:
        icon: "account-circle"
        label: "Perfil"
        selected: root.current_screen == "profile"
        on_release: root.navigate_to("profile")

<NavItem>:
    orientation: "vertical"
    spacing: "1dp"
    padding: "0dp", "6dp"
    size_hint_x: 1

    canvas.before:
        Color:
            rgba: app.kivy_palette["background"] if self.selected else (0, 0, 0, 0)
        RoundedRectangle:
            pos: self.x + dp(2), self.y + dp(2)
            size: self.width - dp(4), self.height - dp(4)
            radius: [18, 18, 18, 18]

    MDIconButton:
        icon: root.icon
        pos_hint: {"center_x": .5}
        icon_size: "20sp"
        theme_text_color: "Custom"
        text_color: app.kivy_palette["primary"] if root.selected else app.kivy_palette["text_secondary"]
        on_release: root.dispatch("on_release")

    MDLabel:
        text: root.label
        adaptive_height: True
        halign: "center"
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: app.kivy_palette["primary"] if root.selected else app.kivy_palette["text_secondary"]
"""
)


class NavigationBar(MDBoxLayout):
    """Primary shell navigation."""

    screen_manager = ObjectProperty(None)
    current_screen = StringProperty("")

    def navigate_to(self, screen_name: str) -> None:
        if self.screen_manager:
            self.screen_manager.current = screen_name
            self.current_screen = screen_name


def route_for_screen(screen_name: str) -> MobileRoute | None:
    return ROUTE_BY_SCREEN.get(screen_name)


class NavItem(ButtonBehavior, MDBoxLayout):
    icon = StringProperty("")
    label = StringProperty("")
    selected = BooleanProperty(False)

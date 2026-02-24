"""
Bottom navigation shared across screens.
"""

from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivymd.uix.boxlayout import MDBoxLayout


Builder.load_string(
    """
<NavigationBar>:
    orientation: "horizontal"
    spacing: "0dp"
    padding: "2dp", "2dp"
    size_hint_y: None
    height: "56dp"

    MDIconButton:
        icon: "view-dashboard"
        icon_size: "21sp"
        theme_text_color: "Custom"
        text_color: (0.09, 0.52, 0.66, 1) if root.current_screen == "dashboard" else (0.45, 0.47, 0.52, 1)
        on_release: root.navigate_to("dashboard")

    MDIconButton:
        icon: "swap-horizontal"
        icon_size: "21sp"
        theme_text_color: "Custom"
        text_color: (0.09, 0.52, 0.66, 1) if root.current_screen == "transactions" else (0.45, 0.47, 0.52, 1)
        on_release: root.navigate_to("transactions")

    MDIconButton:
        icon: "shape"
        icon_size: "21sp"
        theme_text_color: "Custom"
        text_color: (0.09, 0.52, 0.66, 1) if root.current_screen == "categories" else (0.45, 0.47, 0.52, 1)
        on_release: root.navigate_to("categories")

    MDIconButton:
        icon: "wallet"
        icon_size: "21sp"
        theme_text_color: "Custom"
        text_color: (0.09, 0.52, 0.66, 1) if root.current_screen == "budgets" else (0.45, 0.47, 0.52, 1)
        on_release: root.navigate_to("budgets")

    MDIconButton:
        icon: "chart-bar"
        icon_size: "21sp"
        theme_text_color: "Custom"
        text_color: (0.09, 0.52, 0.66, 1) if root.current_screen == "reports" else (0.45, 0.47, 0.52, 1)
        on_release: root.navigate_to("reports")

    MDIconButton:
        icon: "account-circle"
        icon_size: "21sp"
        theme_text_color: "Custom"
        text_color: (0.09, 0.52, 0.66, 1) if root.current_screen == "profile" else (0.45, 0.47, 0.52, 1)
        on_release: root.navigate_to("profile")
    """
)


class NavigationBar(MDBoxLayout):
    """Bottom app navigation."""

    screen_manager = ObjectProperty(None)
    current_screen = StringProperty("")

    def navigate_to(self, screen_name: str) -> None:
        if self.screen_manager:
            self.screen_manager.current = screen_name
            self.current_screen = screen_name

"""
Navigation bar compartida para todas las pantallas
"""

from kivy.lang import Builder
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton


Builder.load_string(
    """
<NavigationBar>:
    orientation: "horizontal"
    spacing: "4dp"
    padding: "4dp"
    size_hint_y: None
    height: "52dp"

    MDFlatButton:
        text: "📊"
        on_release: root.navigate_to('dashboard')

    MDFlatButton:
        text: "💳"
        on_release: root.navigate_to('transactions')

    MDFlatButton:
        text: "🏷️"
        on_release: root.navigate_to('categories')

    MDFlatButton:
        text: "💰"
        on_release: root.navigate_to('budgets')

    MDFlatButton:
        text: "📈"
        on_release: root.navigate_to('reports')

    MDFlatButton:
        text: "⚙️"
        on_release: root.navigate_to('sync_status')
    """
)


class NavigationBar(MDBoxLayout):
    """Barra de navegación inferior para la app"""

    def __init__(self, screen_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = screen_manager

    def navigate_to(self, screen_name: str) -> None:
        """Navega a la pantalla especificada"""
        if self.screen_manager:
            self.screen_manager.current = screen_name

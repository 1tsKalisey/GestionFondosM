"""
TransactionsScreen - Gestion de movimientos.
"""

from typing import Any, Dict, List, Optional

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.spinner import Spinner
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField

from gf_mobile.ui.navigation import NavigationBar


Builder.load_string(
    """
<TransactionsScreen>:
    name: "transactions"

    MDBoxLayout:
        orientation: "vertical"
        padding: "12dp"
        spacing: "8dp"

        MDBoxLayout:
            size_hint_y: None
            height: "42dp"

            MDLabel:
                text: "Movimientos"
                font_style: "H6"
                bold: True

            MDRaisedButton:
                text: "+ Nuevo"
                size_hint_x: None
                width: "96dp"
                md_bg_color: root.accent_color
                on_release: root.manager.current = 'add_transaction'

        MDCard:
            orientation: "vertical"
            padding: "10dp"
            spacing: "10dp"
            adaptive_height: True
            md_bg_color: root.card_bg_color

            MDTextField:
                id: filter_date_from
                hint_text: "Desde YYYY-MM-DD"
                mode: "rectangle"

            MDTextField:
                id: filter_date_to
                hint_text: "Hasta YYYY-MM-DD"
                mode: "rectangle"

            MDBoxLayout:
                size_hint_y: None
                height: "44dp"
                spacing: "8dp"

                MDLabel:
                    text: "Tipo"
                    size_hint_x: None
                    width: "56dp"
                    theme_text_color: "Hint"

                Spinner:
                    id: type_spinner
                    text: root.type_display
                    values: ("Todos", "ingreso", "gasto", "transferencia")
                    size_hint_y: None
                    height: "40dp"
                    background_normal: ""
                    background_color: root.accent_color
                    color: (1, 1, 1, 1)
                    on_text: root.on_type_selected(self.text)

            MDBoxLayout:
                size_hint_y: None
                height: "40dp"
                spacing: "8dp"

                MDFlatButton:
                    text: root.categories_button_text
                    theme_text_color: "Custom"
                    text_color: root.accent_color
                    on_release: root.toggle_categories()

                MDFlatButton:
                    text: "Ocultar" if root.categories_expanded else "Mostrar"
                    on_release: root.toggle_categories()

            ScrollView:
                size_hint_y: None
                height: "124dp" if root.categories_expanded else "0dp"
                opacity: 1 if root.categories_expanded else 0
                do_scroll_x: False

                GridLayout:
                    id: categories_selector
                    cols: 5
                    col_force_default: True
                    col_default_width: (self.width - self.padding[0] - self.padding[2] - self.spacing[0] * 4) / 5
                    spacing: "4dp"
                    padding: "4dp", "2dp", "4dp", "2dp"
                    size_hint_x: 1
                    size_hint_y: None
                    height: self.minimum_height

            MDBoxLayout:
                size_hint_y: None
                height: "46dp"
                spacing: "8dp"

                MDTextField:
                    id: filter_amount_min
                    hint_text: "Precio min"
                    input_filter: "float"
                    mode: "rectangle"

                MDTextField:
                    id: filter_amount_max
                    hint_text: "Precio max"
                    input_filter: "float"
                    mode: "rectangle"

            MDBoxLayout:
                size_hint_y: None
                height: "40dp"
                spacing: "8dp"

                MDRaisedButton:
                    text: "Aplicar"
                    md_bg_color: root.accent_color
                    on_release: root.apply_filters()

                MDFlatButton:
                    text: "Limpiar"
                    on_release: root.clear_filters()

        MDLabel:
            text: root.status_message
            halign: "center"
            theme_text_color: "Hint"
            font_style: "Caption"
            text_size: self.width, None
            max_lines: 2
            shorten: True
            shorten_from: "right"

        NavigationBar:
            id: nav_bar
    """
)


class TransactionsScreen(Screen):
    status_message = StringProperty("")
    type_display = StringProperty("Todos")
    categories_button_text = StringProperty("Categorias: todas")
    categories_expanded = BooleanProperty(False)
    accent_color = ListProperty([0.09, 0.52, 0.66, 1])
    card_bg_color = ListProperty([0.97, 0.99, 1, 1])
    chip_active_bg = ListProperty([0.09, 0.52, 0.66, 1])
    chip_active_text = ListProperty([1, 1, 1, 1])
    chip_inactive_bg = ListProperty([0.88, 0.93, 0.97, 1])
    chip_inactive_text = ListProperty([0.2, 0.3, 0.38, 1])

    def __init__(self, transaction_service=None, category_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service
        self.category_service = category_service
        self.current_filter: Dict[str, Any] = {}
        self.selected_categories: List[str] = []
        self.category_buttons: Dict[str, MDRaisedButton] = {}
        self.selected_type: Optional[str] = None

    def on_enter(self):
        self._apply_theme_colors()
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "transactions"
        self._load_categories()
        self.status_message = "Define filtros y pulsa Aplicar"

    def on_type_selected(self, label: str) -> None:
        self.type_display = label
        value = label.strip().lower()
        self.selected_type = None if value == "todos" else value

    def toggle_categories(self) -> None:
        self.categories_expanded = not self.categories_expanded

    def apply_filters(self) -> None:
        amount_min_text = self.ids.filter_amount_min.text.strip()
        amount_max_text = self.ids.filter_amount_max.text.strip()
        try:
            amount_min = float(amount_min_text) if amount_min_text else None
        except ValueError:
            amount_min = None
        try:
            amount_max = float(amount_max_text) if amount_max_text else None
        except ValueError:
            amount_max = None

        self.current_filter = {
            "date_from": self.ids.filter_date_from.text.strip(),
            "date_to": self.ids.filter_date_to.text.strip(),
            "type": self.selected_type,
            "categories": list(self.selected_categories),
            "amount_min": amount_min,
            "amount_max": amount_max,
        }
        try:
            results_screen = self.manager.get_screen("transactions_results")
            results_screen.set_filters(self.current_filter)
            self.manager.current = "transactions_results"
            self.status_message = "Filtros aplicados"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def clear_filters(self) -> None:
        self.ids.filter_date_from.text = ""
        self.ids.filter_date_to.text = ""
        self.ids.filter_amount_min.text = ""
        self.ids.filter_amount_max.text = ""
        self.type_display = "Todos"
        self.ids.type_spinner.text = "Todos"
        self.selected_type = None
        for name, button in self.category_buttons.items():
            self._set_category_button_style(button, active=False)
        self.selected_categories = []
        self._refresh_selected_categories_label()
        self.current_filter = {}
        self.status_message = "Filtros limpiados"

    def _load_categories(self) -> None:
        container = self.ids.categories_selector
        container.clear_widgets()
        self.category_buttons.clear()
        try:
            if not self.category_service:
                self.selected_categories = []
                self.categories_button_text = "Categorias: sin datos"
                return
            categories = self.category_service.list_all()
            names = sorted({c.name for c in categories if getattr(c, "name", None)})
            for name in names:
                button = MDRaisedButton(
                    text=name,
                    size_hint_y=None,
                    size_hint_x=1,
                    font_size="12sp",
                    on_release=lambda _btn, cat=name: self._toggle_category(cat),
                )
                button.bind(
                    width=lambda inst, value: setattr(inst, "height", max(dp(34), value * 0.42))
                )
                is_active = name in self.selected_categories
                self._set_category_button_style(button, active=is_active)
                container.add_widget(button)
                self.category_buttons[name] = button
            self._refresh_selected_categories_label()
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def _toggle_category(self, category: str) -> None:
        if category in self.selected_categories:
            self.selected_categories = [c for c in self.selected_categories if c != category]
            active = False
        else:
            self.selected_categories.append(category)
            active = True
        button = self.category_buttons.get(category)
        if button:
            self._set_category_button_style(button, active=active)
        self._refresh_selected_categories_label()

    def _refresh_selected_categories_label(self) -> None:
        selected = sorted(self.selected_categories)
        if not selected:
            self.categories_button_text = "Categorias: todas"
        elif len(selected) <= 2:
            self.categories_button_text = "Categorias: " + ", ".join(selected)
        else:
            self.categories_button_text = f"Categorias: {len(selected)} seleccionadas"

    def _set_category_button_style(self, button: MDRaisedButton, active: bool) -> None:
        if active:
            button.md_bg_color = self.chip_active_bg
            button.text_color = self.chip_active_text
        else:
            button.md_bg_color = self.chip_inactive_bg
            button.text_color = self.chip_inactive_text

    def _apply_theme_colors(self) -> None:
        app = App.get_running_app()
        is_dark = bool(app and getattr(app.theme_cls, "theme_style", "Light") == "Dark")
        self.accent_color = [0.09, 0.52, 0.66, 1]
        if is_dark:
            self.card_bg_color = [0.14, 0.16, 0.20, 1]
            self.chip_active_bg = [0.09, 0.52, 0.66, 1]
            self.chip_active_text = [1, 1, 1, 1]
            self.chip_inactive_bg = [0.24, 0.27, 0.32, 1]
            self.chip_inactive_text = [0.88, 0.9, 0.94, 1]
        else:
            self.card_bg_color = [0.97, 0.99, 1, 1]
            self.chip_active_bg = [0.09, 0.52, 0.66, 1]
            self.chip_active_text = [1, 1, 1, 1]
            self.chip_inactive_bg = [0.88, 0.93, 0.97, 1]
            self.chip_inactive_text = [0.2, 0.3, 0.38, 1]

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 120:
            message = f"{message[:117]}..."
        return f"Error: {message}"

    def set_transactions(self, items: List[Dict[str, Any]]) -> None:
        self.status_message = f"{len(items)} movimientos"

"""
TransactionsScreen - Gestion de movimientos.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField

from gf_mobile.ui.dialogs import build_selection_dialog
from gf_mobile.ui.navigation import NavigationBar
from gf_mobile.ui.responsive import ResponsiveManager
from gf_mobile.ui.screen_utils import apply_palette_attrs, category_grid_cols_for_device
from gf_mobile.ui.widgets.shell import HeroCard, ScreenHeader, SectionCard


Builder.load_string(
    """
<TransactionsScreen>:
    name: "transactions"

    MDBoxLayout:
        orientation: "vertical"
        spacing: "0dp"
        md_bg_color: app.kivy_palette["background"]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: "16dp"
                spacing: "12dp"
                size_hint_y: None
                height: self.minimum_height

                ScreenHeader:
                    eyebrow: "OPERATIVA"
                    title: "Movimientos"
                    subtitle: "Filtra, revisa y salta a captura rapida"
                    muted_color: app.kivy_palette["text_secondary"]

                HeroCard:
                    eyebrow: "Acceso directo"
                    title: "Filtra antes de entrar"
                    supporting_text: root.status_message or "Combina fechas, tipo, categorias e importe."
                    card_color: app.kivy_palette["primary"]
                    title_color: 1, 1, 1, 1
                    eyebrow_color: 0.9, 0.95, 1, 1

                    MDBoxLayout:
                        adaptive_height: True
                        spacing: "10dp"

                        MDRaisedButton:
                            text: "+ Nuevo"
                            md_bg_color: app.kivy_palette["accent"]
                            on_release: root.open_new_transaction()

                        MDFlatButton:
                            text: "Ver ultimo listado"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            on_release: root.apply_filters()

                SectionCard:
                    title: "Filtros activos"
                    subtitle: root.categories_button_text
                    card_color: root.card_bg_color
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

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

                        MDRaisedButton:
                            id: type_button
                            text: root.type_display
                            size_hint_x: 1
                            md_bg_color: root.accent_color
                            on_release: root.open_type_picker()

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
                            cols: root.category_grid_cols
                            col_force_default: True
                            col_default_width: root.category_col_width
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
    accent_color = ListProperty([0, 0, 0, 0])
    card_bg_color = ListProperty([0, 0, 0, 0])
    chip_active_bg = ListProperty([0, 0, 0, 0])
    chip_active_text = ListProperty([1, 1, 1, 1])
    chip_inactive_bg = ListProperty([0, 0, 0, 0])
    chip_inactive_text = ListProperty([0, 0, 0, 1])
    category_grid_cols = NumericProperty(5)
    category_col_width = NumericProperty(72)

    def __init__(self, transaction_service=None, category_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service
        self.category_service = category_service
        self.current_filter: Dict[str, Any] = {}
        self.selected_categories: List[str] = []
        self.category_buttons: Dict[str, MDRaisedButton] = {}
        self.selected_type: Optional[str] = None
        self._dialog: Optional[MDDialog] = None
        self._categories_reload_requested = True

    def on_enter(self):
        self._apply_theme_colors()
        self._update_responsive_layout()
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "transactions"
        self.request_categories_reload()
        self.status_message = "Define filtros y pulsa Aplicar"

    def request_categories_reload(self) -> None:
        self._categories_reload_requested = True
        Clock.unschedule(self._run_deferred_category_reload)
        Clock.schedule_once(self._run_deferred_category_reload, 0)

    def _run_deferred_category_reload(self, *_args) -> None:
        if not self._categories_reload_requested:
            return
        self._categories_reload_requested = False
        self._load_categories()

    def _update_responsive_layout(self) -> None:
        self.category_grid_cols = category_grid_cols_for_device(
            is_phone=ResponsiveManager.is_phone(),
            is_tablet=ResponsiveManager.is_tablet(),
            orientation=ResponsiveManager.get_orientation(),
        )
        self.category_col_width = 72 if self.category_grid_cols >= 5 else 92 if self.category_grid_cols == 4 else 112

    def on_type_selected(self, label: str) -> None:
        self.type_display = label
        value = label.strip().lower()
        self.selected_type = None if value == "todos" else value

    def open_type_picker(self) -> None:
        self._open_selection_dialog(
            "Tipo de movimiento",
            ["Todos", "ingreso", "gasto", "transferencia"],
            self.on_type_selected,
        )

    def toggle_categories(self) -> None:
        self.categories_expanded = not self.categories_expanded

    def open_new_transaction(self) -> None:
        try:
            add_screen = self.manager.get_screen("add_transaction")
            if hasattr(add_screen, "prepare_for_entry"):
                add_screen.prepare_for_entry(tx_type="gasto", origin_screen="transactions")
            self.manager.current = "add_transaction"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def apply_filters(self) -> None:
        date_from_text = self.ids.filter_date_from.text.strip()
        date_to_text = self.ids.filter_date_to.text.strip()
        amount_min_text = self.ids.filter_amount_min.text.strip()
        amount_max_text = self.ids.filter_amount_max.text.strip()
        try:
            amount_min = float(amount_min_text) if amount_min_text else None
        except ValueError:
            self.status_message = "Importe minimo invalido"
            return
        try:
            amount_max = float(amount_max_text) if amount_max_text else None
        except ValueError:
            self.status_message = "Importe maximo invalido"
            return

        if amount_min is not None and amount_max is not None and amount_min > amount_max:
            self.status_message = "El importe minimo no puede ser mayor que el maximo"
            return

        try:
            if date_from_text:
                datetime.strptime(date_from_text, "%Y-%m-%d")
            if date_to_text:
                datetime.strptime(date_to_text, "%Y-%m-%d")
            if date_from_text and date_to_text and date_from_text > date_to_text:
                self.status_message = "La fecha inicial no puede ser posterior a la final"
                return
        except ValueError:
            self.status_message = "Usa fechas con formato YYYY-MM-DD"
            return

        self.current_filter = {
            "date_from": date_from_text,
            "date_to": date_to_text,
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
            app = App.get_running_app()
            if not app or not hasattr(app, "list_categories_snapshot"):
                self.selected_categories = []
                self.categories_button_text = "Categorias: sin datos"
                return
            categories = app.list_categories_snapshot()
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
        apply_palette_attrs(
            self,
            {
                "accent_color": "primary",
                "card_bg_color": "surface",
                "chip_active_bg": "primary",
                "chip_inactive_bg": "background",
                "chip_inactive_text": "text_secondary",
            },
        )
        self.chip_active_text = [1, 1, 1, 1]

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 120:
            message = f"{message[:117]}..."
        return f"Error: {message}"

    def set_transactions(self, items: List[Dict[str, Any]]) -> None:
        self.status_message = f"{len(items)} movimientos"

    def _open_selection_dialog(self, title: str, options: List[str], callback) -> None:
        self._dialog = build_selection_dialog(
            self._dialog,
            title=title,
            options=options,
            on_select=callback,
        )
        self._dialog.open()

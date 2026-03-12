"""
Budgets screen.
"""

from datetime import datetime
from typing import Dict, Optional

from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem

from gf_mobile.ui.dialogs import build_message_dialog, build_selection_dialog
from gf_mobile.ui.navigation import NavigationBar
from gf_mobile.ui.responsive import ResponsiveManager
from gf_mobile.ui.screen_utils import list_panel_height_for_device, resolve_palette
from gf_mobile.ui.widgets.shell import HeroCard, ScreenHeader, SectionCard


Builder.load_string(
    """
<BudgetsScreen>:
    name: "budgets"

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
                    eyebrow: "CONTROL"
                    title: "Presupuestos"
                    subtitle: "Define limites mensuales por categoria"
                    muted_color: app.kivy_palette["text_secondary"]

                HeroCard:
                    eyebrow: "Mes activo"
                    title: root.month_display or root.default_month
                    supporting_text: root.status_message or "Mantén limites claros para leer mejor el dashboard."
                    card_color: app.kivy_palette["primary"]
                    title_color: 1, 1, 1, 1
                    eyebrow_color: 0.9, 0.95, 1, 1

                SectionCard:
                    title: "Editar presupuesto"
                    subtitle: "Selecciona categoria, importe y mes"
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDRaisedButton:
                        id: budget_category
                        text: root.category_display
                        md_bg_color: app.kivy_palette["primary"]
                        on_release: root.open_category_picker()

                    MDTextField:
                        id: budget_limit
                        hint_text: "Limite"
                        input_filter: "float"
                        mode: "rectangle"

                    MDRaisedButton:
                        id: budget_month
                        text: root.month_display
                        md_bg_color: app.kivy_palette["primary"]
                        on_release: root.open_month_picker()

                    MDBoxLayout:
                        size_hint_y: None
                        height: "42dp"
                        spacing: "8dp"

                        MDRaisedButton:
                            text: "Guardar"
                            md_bg_color: app.kivy_palette["primary"]
                            on_release: root.on_save()

                        MDFlatButton:
                            text: "Limpiar"
                            on_release: root.on_clear()

                SectionCard:
                    title: "Vista mensual"
                    subtitle: root.status_message
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    ScrollView:
                        do_scroll_x: False
                        size_hint_y: None
                        height: root.list_height_dp

                        MDList:
                            id: budgets_list

        NavigationBar:
            id: nav_bar
    """
)


class BudgetsScreen(Screen):
    status_message = StringProperty("")
    default_month = StringProperty("")
    list_height_dp = NumericProperty(320)
    category_display = StringProperty("Seleccionar categoria")
    month_display = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.budget_service = None
        self.category_service = None
        self.selected_budget_id = None
        self.default_month = datetime.now().strftime("%Y-%m")
        self.month_display = self.default_month
        self._dialog: Optional[MDDialog] = None
        self.category_id_by_name: Dict[str, str] = {}

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "budgets"
        self._update_responsive_layout()
        self._load_categories()
        self.refresh()

    def _update_responsive_layout(self) -> None:
        self.list_height_dp = list_panel_height_for_device(
            is_phone=ResponsiveManager.is_phone(),
            is_tablet=ResponsiveManager.is_tablet(),
            orientation=ResponsiveManager.get_orientation(),
        )

    def refresh(self) -> None:
        try:
            self.ids.budgets_list.clear_widgets()
            if not self.budget_service:
                self.status_message = "BudgetService no configurado"
                return

            current_month = self._active_month()
            budgets = self.budget_service.list_all()
            month_budgets = [b for b in budgets if str(b.month).startswith(current_month)]

            if not month_budgets:
                self._add_placeholder_item("Sin presupuestos para el mes seleccionado")
                self.status_message = "Sin presupuestos"
                return

            for budget in month_budgets:
                category_name = budget.category.name if hasattr(budget, "category") and budget.category else "N/A"
                self.ids.budgets_list.add_widget(
                    OneLineListItem(
                        text=f"{category_name}: EUR {budget.amount:.2f}",
                        on_release=lambda _x, b=budget: self.on_select_budget(b),
                    )
                )

            self.status_message = f"{len(month_budgets)} presupuestos"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def on_new_budget(self) -> None:
        self.category_display = "Seleccionar categoria"
        self.ids.budget_limit.text = ""
        self.month_display = self.default_month
        self.selected_budget_id = None

    def on_select_budget(self, budget) -> None:
        category_name = budget.category.name if hasattr(budget, "category") and budget.category else ""
        self.category_display = category_name or "Seleccionar categoria"
        self.ids.budget_limit.text = str(budget.amount)
        self.month_display = str(budget.month)
        self.selected_budget_id = budget.id

    def on_save(self) -> None:
        try:
            if not self.budget_service or not self.category_service:
                self.status_message = "Servicios no configurados"
                self._show_dialog("Error", self.status_message, is_error=True)
                return

            category_name = self.category_display.strip()
            limit_text = self.ids.budget_limit.text.strip()
            month = self.month_display.strip()

            if not limit_text:
                self.status_message = "Ingrese el limite"
                self._show_dialog("Error", self.status_message, is_error=True)
                return
            if not category_name:
                self.status_message = "Ingrese categoria"
                self._show_dialog("Error", self.status_message, is_error=True)
                return
            if not month:
                self.status_message = "Ingrese el mes"
                self._show_dialog("Error", self.status_message, is_error=True)
                return

            categories = self.category_service.list_all()
            category = next((c for c in categories if c.name == category_name), None)
            if not category:
                self.status_message = "Categoria no encontrada"
                self._show_dialog("Error", self.status_message, is_error=True)
                return

            amount = float(limit_text)
            if self.selected_budget_id:
                from gf_mobile.persistence.models import Budget

                session = self.budget_service.session
                budget = session.query(Budget).filter(Budget.id == self.selected_budget_id).first()
                if budget:
                    budget.category_id = category.id
                    budget.amount = amount
                    budget.month = month
                    session.commit()
                    self.status_message = "Presupuesto actualizado"
                    self._show_dialog("Exito", self.status_message, is_error=False)
            else:
                from gf_mobile.services.budget_service import BudgetInput

                self.budget_service.create(BudgetInput(category_id=category.id, limit=amount, month=month))
                self.status_message = "Presupuesto creado"
                self._show_dialog("Exito", self.status_message, is_error=False)

            self.on_clear()
            self.refresh()
        except ValueError:
            self.status_message = "Ingrese un limite valido"
            self._show_dialog("Error", self.status_message, is_error=True)
        except Exception as exc:
            self.status_message = self._short_error(exc)
            self._show_dialog("Error", self.status_message, is_error=True)

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 120:
            message = f"{message[:117]}..."
        return f"Error: {message}"

    def on_clear(self) -> None:
        self.category_display = "Seleccionar categoria"
        self.ids.budget_limit.text = ""
        self.month_display = self.default_month
        self.selected_budget_id = None

    def _load_categories(self) -> None:
        if not self.category_service:
            self.category_id_by_name = {}
            return
        categories = self.category_service.list_all()
        self.category_id_by_name = {c.name: c.id for c in categories if getattr(c, "name", None)}

    def open_category_picker(self) -> None:
        self._open_selection_dialog(
            "Categoria",
            list(self.category_id_by_name.keys()),
            self._select_category,
        )

    def open_month_picker(self) -> None:
        current = datetime.now()
        options = []
        for offset in range(-2, 4):
            year = current.year + ((current.month - 1 + offset) // 12)
            month = ((current.month - 1 + offset) % 12) + 1
            options.append(f"{year:04d}-{month:02d}")
        self._open_selection_dialog("Mes", options, self._select_month)

    def _select_category(self, name: str) -> None:
        self.category_display = name

    def _select_month(self, value: str) -> None:
        self.month_display = value
        self.refresh()

    def _active_month(self) -> str:
        month = self.month_display.strip()
        if len(month) == 7 and month[4] == "-":
            return month
        return self.default_month

    def _add_placeholder_item(self, text: str) -> None:
        self.ids.budgets_list.add_widget(
            OneLineListItem(
                text=text,
                disabled=True,
            )
        )

    def _show_dialog(self, title: str, message: str, is_error: bool) -> None:
        palette = resolve_palette()
        button_color = palette["error"] if is_error else palette["primary"]
        self._dialog = build_message_dialog(
            self._dialog,
            title=title,
            message=message,
            button_color=button_color,
        )
        self._dialog.open()

    def _open_selection_dialog(self, title: str, options, callback) -> None:
        self._dialog = build_selection_dialog(
            self._dialog,
            title=title,
            options=options,
            on_select=callback,
        )
        self._dialog.open()

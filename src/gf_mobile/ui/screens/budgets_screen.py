"""
Budgets screen.
"""

from datetime import datetime
from typing import Optional

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem

from gf_mobile.ui.navigation import NavigationBar


Builder.load_string(
    """
<BudgetsScreen>:
    name: "budgets"

    MDBoxLayout:
        orientation: "vertical"
        padding: "12dp"
        spacing: "8dp"

        MDLabel:
            text: "Presupuestos"
            font_style: "H6"
            bold: True
            size_hint_y: None
            height: "36dp"

        MDCard:
            orientation: "vertical"
            padding: "12dp"
            spacing: "8dp"
            adaptive_height: True

            MDTextField:
                id: budget_category
                hint_text: "Categoria"
                mode: "rectangle"

            MDTextField:
                id: budget_limit
                hint_text: "Limite"
                input_filter: "float"
                mode: "rectangle"

            MDTextField:
                id: budget_month
                hint_text: "Mes YYYY-MM"
                mode: "rectangle"
                text: root.default_month

            MDBoxLayout:
                size_hint_y: None
                height: "42dp"
                spacing: "8dp"

                MDRaisedButton:
                    text: "Guardar"
                    on_release: root.on_save()

                MDFlatButton:
                    text: "Limpiar"
                    on_release: root.on_clear()

        ScrollView:
            MDList:
                id: budgets_list

        MDLabel:
            text: root.status_message
            theme_text_color: "Hint"
            halign: "center"
            font_style: "Caption"
            text_size: self.width, None
            max_lines: 2
            shorten: True
            shorten_from: "right"
            size_hint_y: None
            height: "30dp"

        NavigationBar:
            id: nav_bar
    """
)


class BudgetsScreen(Screen):
    status_message = StringProperty("")
    default_month = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.budget_service = None
        self.category_service = None
        self.selected_budget_id = None
        self.default_month = datetime.now().strftime("%Y-%m")
        self._dialog: Optional[MDDialog] = None

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "budgets"
        self.refresh()

    def refresh(self) -> None:
        try:
            self.ids.budgets_list.clear_widgets()
            if not self.budget_service:
                self.status_message = "BudgetService no configurado"
                return

            current_month = datetime.now().strftime("%Y-%m")
            budgets = self.budget_service.list_all()
            month_budgets = [b for b in budgets if str(b.month).startswith(current_month)]

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
        self.ids.budget_category.text = ""
        self.ids.budget_limit.text = ""
        self.ids.budget_month.text = self.default_month
        self.selected_budget_id = None

    def on_select_budget(self, budget) -> None:
        category_name = budget.category.name if hasattr(budget, "category") and budget.category else ""
        self.ids.budget_category.text = category_name
        self.ids.budget_limit.text = str(budget.amount)
        self.ids.budget_month.text = str(budget.month)
        self.selected_budget_id = budget.id

    def on_save(self) -> None:
        try:
            if not self.budget_service or not self.category_service:
                self.status_message = "Servicios no configurados"
                self._show_dialog("Error", self.status_message, is_error=True)
                return

            category_name = self.ids.budget_category.text.strip()
            limit_text = self.ids.budget_limit.text.strip()
            month = self.ids.budget_month.text.strip()

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
        self.ids.budget_category.text = ""
        self.ids.budget_limit.text = ""
        self.ids.budget_month.text = self.default_month
        self.selected_budget_id = None

    def _show_dialog(self, title: str, message: str, is_error: bool) -> None:
        if self._dialog:
            self._dialog.dismiss()
        button_color = (0.84, 0.25, 0.22, 1) if is_error else (0.09, 0.52, 0.66, 1)
        self._dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDRaisedButton(
                    text="Aceptar",
                    md_bg_color=button_color,
                    on_release=lambda *_: self._dialog.dismiss(),
                )
            ],
        )
        self._dialog.open()

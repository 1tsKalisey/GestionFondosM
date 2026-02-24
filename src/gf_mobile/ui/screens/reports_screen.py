"""
Reports screen.
"""

from datetime import datetime, timedelta

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import OneLineListItem

from gf_mobile.ui.navigation import NavigationBar


Builder.load_string(
    """
<ReportsScreen>:
    name: "reports"

    MDBoxLayout:
        orientation: "vertical"
        padding: "12dp"
        spacing: "8dp"

        MDBoxLayout:
            size_hint_y: None
            height: "42dp"

            MDLabel:
                text: "Reportes"
                font_style: "H6"
                bold: True

            MDRaisedButton:
                text: "Actualizar"
                size_hint_x: None
                width: "110dp"
                on_release: root.refresh()

        MDCard:
            orientation: "vertical"
            padding: "10dp"
            spacing: "8dp"
            adaptive_height: True

            MDTextField:
                id: report_start
                hint_text: "Desde YYYY-MM-DD"
                mode: "rectangle"

            MDTextField:
                id: report_end
                hint_text: "Hasta YYYY-MM-DD"
                mode: "rectangle"

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                spacing: "10dp"
                size_hint_y: None
                height: self.minimum_height

                MDCard:
                    orientation: "vertical"
                    padding: "10dp"
                    adaptive_height: True

                    MDLabel:
                        text: "Por categoria"
                        bold: True
                        font_style: "Body2"
                        size_hint_y: None
                        height: "24dp"

                    MDList:
                        id: category_summary

                MDCard:
                    orientation: "vertical"
                    padding: "10dp"
                    adaptive_height: True

                    MDLabel:
                        text: "Por grupo presupuestario"
                        bold: True
                        font_style: "Body2"
                        size_hint_y: None
                        height: "24dp"

                    MDList:
                        id: budget_summary

        MDLabel:
            text: root.status_message
            theme_text_color: "Hint"
            halign: "center"
            text_size: self.width, None
            max_lines: 2
            shorten: True
            shorten_from: "right"

        NavigationBar:
            id: nav_bar
    """
)


class ReportsScreen(Screen):
    status_message = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = None
        self.category_service = None
        self.budget_service = None
        self.report_service = None

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "reports"
        today = datetime.now()
        last_month = today - timedelta(days=30)
        self.ids.report_start.text = last_month.strftime("%Y-%m-%d")
        self.ids.report_end.text = today.strftime("%Y-%m-%d")
        self.refresh()

    def refresh(self) -> None:
        try:
            if not self.transaction_service or not self.category_service:
                self.status_message = "Servicios no configurados"
                return

            start_text = self.ids.report_start.text.strip()
            end_text = self.ids.report_end.text.strip()
            if not start_text or not end_text:
                self.status_message = "Ingrese rango de fechas"
                return

            start_date = datetime.fromisoformat(start_text)
            end_date = datetime.fromisoformat(end_text)
            transactions = self.transaction_service.list_all(limit=500)
            range_tx = [tx for tx in transactions if start_date <= tx.occurred_at <= end_date]

            self._generate_category_summary(range_tx)
            self._generate_budget_summary(range_tx)
            self.status_message = f"{len(range_tx)} movimientos en rango"
        except ValueError:
            self.status_message = "Fechas invalidas"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 120:
            message = f"{message[:117]}..."
        return f"Error: {message}"

    def _generate_category_summary(self, transactions) -> None:
        try:
            self.ids.category_summary.clear_widgets()
            category_totals = {}
            for tx in transactions:
                if tx.type != "gasto":
                    continue
                cat_name = "Sin categoria"
                if hasattr(tx, "category") and tx.category:
                    cat_name = tx.category.name
                category_totals.setdefault(cat_name, 0)
                category_totals[cat_name] += tx.amount

            total_expenses = sum(category_totals.values())
            for cat_name in sorted(category_totals.keys()):
                amount = category_totals[cat_name]
                pct = (amount / total_expenses * 100) if total_expenses > 0 else 0
                self.ids.category_summary.add_widget(
                    OneLineListItem(text=f"{cat_name}: EUR {amount:.2f} ({pct:.1f}%)")
                )
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def _generate_budget_summary(self, transactions) -> None:
        try:
            self.ids.budget_summary.clear_widgets()
            budget_groups = {"Necesidades": 0, "Ocio/Deseos": 0, "Ahorro/Deuda": 0, "Otros": 0}

            for tx in transactions:
                if tx.type != "gasto":
                    continue
                group = "Otros"
                if hasattr(tx, "category") and tx.category:
                    group = tx.category.budget_group or "Otros"
                if group in budget_groups:
                    budget_groups[group] += tx.amount

            total = sum(budget_groups.values())
            for group_name, amount in budget_groups.items():
                pct = (amount / total * 100) if total > 0 else 0
                self.ids.budget_summary.add_widget(
                    OneLineListItem(text=f"{group_name}: EUR {amount:.2f} ({pct:.1f}%)")
                )
        except Exception as exc:
            self.status_message = self._short_error(exc)

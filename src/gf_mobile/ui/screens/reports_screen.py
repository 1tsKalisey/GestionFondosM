"""
ReportsScreen - Reportes e informes financieros
"""

from datetime import datetime

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.card import MDCard


Builder.load_string(
    """
<ReportsScreen>:
    name: "reports"

    MDBoxLayout:
        orientation: "vertical"
        padding: "16dp"
        spacing: "12dp"

        # Header
        MDBoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: "48dp"

            MDLabel:
                text: "Reportes"
                font_style: "H6"
                halign: "left"

            MDRaisedButton:
                text: "Actualizar"
                size_hint_x: None
                width: "100dp"
                on_release: root.refresh()

        # Rango de fechas
        MDCard:
            orientation: "horizontal"
            padding: "12dp"
            spacing: "8dp"
            size_hint_y: None
            height: "60dp"
            elevation: 1

            MDTextField:
                id: report_start
                hint_text: "Desde (YYYY-MM-DD)"
                mode: "rectangle"
                size_hint_x: 0.5

            MDTextField:
                id: report_end
                hint_text: "Hasta (YYYY-MM-DD)"
                mode: "rectangle"
                size_hint_x: 0.5

        # Resumen gasto por categoría
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                spacing: "12dp"
                size_hint_y: None
                height: self.minimum_height
                padding: "0dp", "12dp"

                MDCard:
                    orientation: "vertical"
                    padding: "12dp"
                    spacing: "8dp"
                    size_hint_y: None
                    adaptive_height: True
                    elevation: 2

                    MDLabel:
                        text: "Resumen por categoría"
                        font_style: "Body2"
                        bold: True
                        size_hint_y: None
                        height: "24dp"

                    MDList:
                        id: category_summary

                MDCard:
                    orientation: "vertical"
                    padding: "12dp"
                    spacing: "8dp"
                    size_hint_y: None
                    adaptive_height: True
                    elevation: 2

                    MDLabel:
                        text: "Resumen presupuestario"
                        font_style: "Body2"
                        bold: True
                        size_hint_y: None
                        height: "24dp"

                    MDList:
                        id: budget_summary

        MDLabel:
            text: root.status_message
            theme_text_color: "Hint"
            halign: "center"

        # Barra de navegación
        MDBoxLayout:
            orientation: "horizontal"
            spacing: "4dp"
            padding: "4dp"
            size_hint_y: None
            height: "52dp"

            MDFlatButton:
                text: "📊 Dashboard"
                on_release: root.manager.current = 'dashboard'

            MDFlatButton:
                text: "💳 Transacciones"
                on_release: root.manager.current = 'transactions'

            MDFlatButton:
                text: "🏷️ Categorías"
                on_release: root.manager.current = 'categories'

            MDFlatButton:
                text: "💰 Presupuestos"
                on_release: root.manager.current = 'budgets'
    """
)


class ReportsScreen(Screen):
    """Pantalla de reportes e informes."""

    status_message = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = None
        self.category_service = None
        self.budget_service = None
        self.report_service = None

    def on_enter(self):
        """Se llama cuando la pantalla se muestra"""
        # Establecer fechas por defecto (último mes)
        today = datetime.now()
        from datetime import timedelta
        last_month = today - timedelta(days=30)

        self.ids.report_start.text = last_month.strftime("%Y-%m-%d")
        self.ids.report_end.text = today.strftime("%Y-%m-%d")

        self.refresh()

    def refresh(self) -> None:
        """Recarga los reportes"""
        try:
            if not self.transaction_service or not self.category_service:
                self.status_message = "Servicios no configurados"
                return

            # Obtener fechas
            start_text = self.ids.report_start.text.strip()
            end_text = self.ids.report_end.text.strip()

            if not start_text or not end_text:
                self.status_message = "Ingrese el rango de fechas"
                return

            start_date = datetime.fromisoformat(start_text)
            end_date = datetime.fromisoformat(end_text)

            # Obtener transacciones
            transactions = self.transaction_service.list_all(limit=500)
            range_tx = [
                tx for tx in transactions
                if start_date <= tx.occurred_at <= end_date
            ]

            # Generar resumen por categoría
            self._generate_category_summary(range_tx)

            # Generar resumen presupuestario
            self._generate_budget_summary(range_tx)

            self.status_message = f"{len(range_tx)} transacciones en el rango"

        except ValueError:
            self.status_message = "Fechas inválidas (use YYYY-MM-DD)"
        except Exception as exc:
            self.status_message = f"Error: {str(exc)}"

    def _generate_category_summary(self, transactions) -> None:
        """Genera resumen de gastos por categoría"""
        try:
            self.ids.category_summary.clear_widgets()

            # Agrupar por categoría
            category_totals = {}
            for tx in transactions:
                if tx.type != "gasto":
                    continue

                cat_name = "Sin categoría"
                if hasattr(tx, 'category') and tx.category:
                    cat_name = tx.category.name

                if cat_name not in category_totals:
                    category_totals[cat_name] = 0
                category_totals[cat_name] += tx.amount

            # Crear items
            total_expenses = sum(category_totals.values())
            for cat_name in sorted(category_totals.keys()):
                amount = category_totals[cat_name]
                pct = (amount / total_expenses * 100) if total_expenses > 0 else 0

                item_text = f"{cat_name}: € {amount:.2f} ({pct:.1f}%)"
                self.ids.category_summary.add_widget(OneLineListItem(text=item_text))

        except Exception as exc:
            self.status_message = f"Error en resumen categorías: {str(exc)}"

    def _generate_budget_summary(self, transactions) -> None:
        """Genera resumen presupuestario (Necesidades, Ocio, Ahorro)"""
        try:
            self.ids.budget_summary.clear_widgets()

            # Agrupar por grupo presupuestario
            budget_groups = {
                "Necesidades": 0,
                "Ocio/Deseos": 0,
                "Ahorro/Deuda": 0,
                "Otros": 0,
            }

            for tx in transactions:
                if tx.type != "gasto":
                    continue

                group = "Otros"
                if hasattr(tx, 'category') and tx.category:
                    group = tx.category.budget_group or "Otros"

                if group in budget_groups:
                    budget_groups[group] += tx.amount

            # Crear items
            total = sum(budget_groups.values())
            for group_name in budget_groups.keys():
                amount = budget_groups[group_name]
                pct = (amount / total * 100) if total > 0 else 0

                item_text = f"{group_name}: € {amount:.2f} ({pct:.1f}%)"
                self.ids.budget_summary.add_widget(OneLineListItem(text=item_text))

        except Exception as exc:
            self.status_message = f"Error en resumen presupuestario: {str(exc)}"

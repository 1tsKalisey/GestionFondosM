"""
TransactionsScreen - Gestión completa de transacciones con filtros
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.card import MDCard


Builder.load_string(
    """
<TransactionsScreen>:
    name: "transactions"

    MDBoxLayout:
        orientation: "vertical"
        padding: "16dp"
        spacing: "12dp"

        # Header
        MDBoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: "48dp"
            spacing: "8dp"

            MDLabel:
                text: "Transacciones"
                font_style: "H6"
                halign: "left"

            MDRaisedButton:
                text: "+ Nueva"
                size_hint_x: None
                width: "100dp"
                on_release: root.manager.current = 'add_transaction'

        # Formulario de filtros
        MDCard:
            orientation: "vertical"
            padding: "12dp"
            spacing: "8dp"
            size_hint_y: None
            height: "180dp"
            elevation: 1

            MDBoxLayout:
                orientation: "horizontal"
                spacing: "8dp"
                size_hint_y: None
                height: "48dp"

                MDTextField:
                    id: filter_date_from
                    hint_text: "Desde (YYYY-MM-DD)"
                    mode: "rectangle"
                    size_hint_x: 0.4

                MDTextField:
                    id: filter_date_to
                    hint_text: "Hasta (YYYY-MM-DD)"
                    mode: "rectangle"
                    size_hint_x: 0.4

                MDFlatButton:
                    text: "Aplicar"
                    on_release: root.apply_filters()

            MDBoxLayout:
                orientation: "horizontal"
                spacing: "8dp"
                size_hint_y: None
                height: "48dp"

                MDSpinner:
                    id: filter_type
                    text: "Tipo"
                    values: ("Todas", "gasto", "ingreso", "transferencia")
                    size_hint_x: 0.3

                MDSpinner:
                    id: filter_category
                    text: "Categoría"
                    values: ("Todas",)
                    size_hint_x: 0.3

                MDFlatButton:
                    text: "Limpiar"
                    on_release: root.clear_filters()

        # Lista de transacciones
        ScrollView:
            MDList:
                id: tx_list

        MDLabel:
            text: root.status_message
            halign: "center"
            theme_text_color: "Hint"
            font_style: "Caption"

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
                text: "🏷️ Categorías"
                on_release: root.manager.current = 'categories'

            MDFlatButton:
                text: "💰 Presupuestos"
                on_release: root.manager.current = 'budgets'

            MDFlatButton:
                text: "📈 Reportes"
                on_release: root.manager.current = 'reports'

            MDFlatButton:
                text: "🚪 Salir"
                on_release: root.on_logout()
    """
)


class TransactionsScreen(Screen):
    """Pantalla de listado y gestión de transacciones con filtros."""

    status_message = StringProperty("")

    def __init__(self, transaction_service=None, category_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service
        self.category_service = category_service
        self.current_filter = {}

    def on_enter(self):
        """Se llama cuando la pantalla se muestra"""
        self.refresh()
        self._load_categories()

    def _load_categories(self) -> None:
        """Carga las categorías en el spinner de filtro"""
        try:
            if self.category_service:
                categories = self.category_service.list_all()
                spinner_values = ["Todas"] + [cat.name for cat in categories]
                self.ids.filter_category.values = tuple(spinner_values)
        except Exception as e:
            self.status_message = f"Error cargando categorías: {str(e)}"

    def refresh(self) -> None:
        """Recarga la lista de transacciones con filtros actuales"""
        self.ids.tx_list.clear_widgets()
        if not self.transaction_service:
            self.status_message = "TransactionService no configurado"
            return

        try:
            transactions = self.transaction_service.list_all(limit=100)
            
            # Aplicar filtros
            filtered_txs = self._apply_filters_to_list(transactions)
            
            # Mostrar transacciones
            for tx in filtered_txs:
                category_name = tx.category.name if hasattr(tx, 'category') and tx.category else "N/A"
                merchant = tx.merchant or "N/A"
                label = f"{tx.occurred_at.date()} · {tx.type} · €{tx.amount:.2f} · {category_name}"
                item = OneLineListItem(text=label)
                self.ids.tx_list.add_widget(item)

            self.status_message = f"{len(filtered_txs)} transacciones"
        except Exception as e:
            self.status_message = f"Error: {str(e)}"

    def apply_filters(self) -> None:
        """Aplica los filtros y recarga la lista"""
        date_from = self.ids.filter_date_from.text
        date_to = self.ids.filter_date_to.text
        tx_type = self.ids.filter_type.text
        category = self.ids.filter_category.text

        self.current_filter = {
            "date_from": date_from,
            "date_to": date_to,
            "type": tx_type if tx_type != "Todas" else None,
            "category": category if category != "Todas" else None,
        }
        self.refresh()

    def clear_filters(self) -> None:
        """Limpia todos los filtros"""
        self.ids.filter_date_from.text = ""
        self.ids.filter_date_to.text = ""
        self.ids.filter_type.text = "Tipo"
        self.ids.filter_category.text = "Categoría"
        self.current_filter = {}
        self.refresh()

    def _apply_filters_to_list(self, transactions: List[Any]) -> List[Any]:
        """Aplica los filtros actuales a una lista de transacciones"""
        result = transactions

        # Filtro por tipo
        if self.current_filter.get("type"):
            result = [tx for tx in result if tx.type == self.current_filter["type"]]

        # Filtro por categoría
        if self.current_filter.get("category"):
            result = [tx for tx in result if hasattr(tx, 'category') and tx.category and tx.category.name == self.current_filter["category"]]

        # Filtro por fecha
        if self.current_filter.get("date_from"):
            try:
                date_from = datetime.strptime(self.current_filter["date_from"], "%Y-%m-%d").date()
                result = [tx for tx in result if tx.occurred_at.date() >= date_from]
            except:
                pass

        if self.current_filter.get("date_to"):
            try:
                date_to = datetime.strptime(self.current_filter["date_to"], "%Y-%m-%d").date()
                result = [tx for tx in result if tx.occurred_at.date() <= date_to]
            except:
                pass

        return result

    def on_logout(self) -> None:
        """Cerrar sesión y volver al login."""
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, 'auth_service'):
            # Limpiar sesión
            app.auth_service.sign_out()
            # Volver a login
            self.manager.current = 'login'
            self.status_message = "Sesion cerrada"

    def set_transactions(self, items: List[Dict[str, Any]]) -> None:
        """Permite inyectar lista de transacciones ya procesada."""
        self.ids.tx_list.clear_widgets()
        for item in items:
            self.ids.tx_list.add_widget(OneLineListItem(text=item.get("label", "")))
        self.status_message = f"{len(items)} transacciones"

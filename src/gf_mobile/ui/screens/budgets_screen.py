"""
BudgetsScreen - Gestión de presupuestos
"""

from datetime import datetime

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.card import MDCard


Builder.load_string(
    """
<BudgetsScreen>:
    name: "budgets"

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
                text: "Presupuestos"
                font_style: "H6"
                halign: "left"

            MDRaisedButton:
                text: "+ Nuevo"
                size_hint_x: None
                width: "100dp"
                on_release: root.on_new_budget()

        # Formulario de presupuesto
        MDCard:
            orientation: "vertical"
            padding: "16dp"
            spacing: "12dp"
            size_hint_y: None
            height: "280dp"
            elevation: 2

            MDLabel:
                text: "Crear presupuesto"
                font_style: "Body2"
                bold: True
                size_hint_y: None
                height: "20dp"

            MDLabel:
                text: "Categoría"
                font_style: "Caption"
                theme_text_color: "Hint"
                size_hint_y: None
                height: "16dp"

            MDSpinner:
                id: budget_category
                text: "Seleccionar..."
                values: ("Sin datos",)
                size_hint_y: None
                height: "48dp"

            MDLabel:
                text: "Límite (€)"
                font_style: "Caption"
                theme_text_color: "Hint"
                size_hint_y: None
                height: "16dp"

            MDTextField:
                id: budget_limit
                hint_text: "100.00"
                input_filter: "float"
                mode: "rectangle"
                size_hint_y: None
                height: "48dp"

            MDLabel:
                text: "Mes (YYYY-MM)"
                font_style: "Caption"
                theme_text_color: "Hint"
                size_hint_y: None
                height: "16dp"

            MDTextField:
                id: budget_month
                hint_text: "2026-02"
                mode: "rectangle"
                text: root.default_month
                size_hint_y: None
                height: "48dp"

            MDBoxLayout:
                spacing: "8dp"
                size_hint_y: None
                height: "48dp"

                MDRaisedButton:
                    text: "Crear"
                    on_release: root.on_save()

                MDFlatButton:
                    text: "Limpiar"
                    on_release: root.on_clear()


        # Presupuestos activos
        MDLabel:
            text: "Presupuestos activos"
            font_style: "Body2"
            bold: True
            size_hint_y: None
            height: "24dp"

        # Lista de presupuestos
        ScrollView:
            MDList:
                id: budgets_list

        MDLabel:
            text: root.status_message
            theme_text_color: "Hint"
            halign: "center"
            font_style: "Caption"
            size_hint_y: None
            height: "24dp"

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
                text: "📈 Reportes"
                on_release: root.manager.current = 'reports'
    """
)


class BudgetsScreen(Screen):
    """Pantalla de gestión de presupuestos."""

    status_message = StringProperty("")
    default_month = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.budget_service = None
        self.category_service = None
        self.selected_budget_id = None
        # Establecer mes por defecto
        today = datetime.now()
        self.default_month = today.strftime("%Y-%m")

    def on_enter(self):
        """Se llama cuando la pantalla se muestra"""
        self.refresh()

    def refresh(self) -> None:
        """Recarga la lista de presupuestos"""
        try:
            self.ids.budgets_list.clear_widgets()

            if not self.budget_service:
                self.status_message = "BudgetService no configurado"
                return

            # Obtener presupuestos del mes actual
            today = datetime.now()
            current_month = today.strftime("%Y-%m")

            budgets = self.budget_service.list_all()
            # Filtrar por mes actual
            month_budgets = [b for b in budgets if str(b.month).startswith(current_month)]

            for budget in month_budgets:
                category_name = "N/A"
                if hasattr(budget, 'category') and budget.category:
                    category_name = budget.category.name

                item = OneLineListItem(
                    text=f"{category_name}: € {budget.limit:.2f}",
                    on_release=lambda x=budget: self.on_select_budget(x)
                )
                self.ids.budgets_list.add_widget(item)

            # Cargar opciones de categorías
            if self.category_service:
                categories = self.category_service.list_all()
                category_names = [cat.name for cat in categories]
                self.ids.budget_category.values = category_names

            self.status_message = f"{len(month_budgets)} presupuestos"

        except Exception as exc:
            self.status_message = f"Error: {str(exc)}"

    def on_new_budget(self) -> None:
        """Abre el formulario para nuevo presupuesto"""
        self.ids.budget_category.text = "Seleccionar..."
        self.ids.budget_limit.text = ""
        self.ids.budget_month.text = self.default_month
        self.selected_budget_id = None

    def on_select_budget(self, budget) -> None:
        """Selecciona un presupuesto para editar"""
        category_name = "N/A"
        if hasattr(budget, 'category') and budget.category:
            category_name = budget.category.name

        self.ids.budget_category.text = category_name
        self.ids.budget_limit.text = str(budget.limit)
        self.ids.budget_month.text = str(budget.month)
        self.selected_budget_id = budget.id

    def on_save(self) -> None:
        """Guarda el presupuesto"""
        try:
            if not self.budget_service or not self.category_service:
                self.status_message = "Servicios no configurados"
                return

            category_name = self.ids.budget_category.text
            limit_text = self.ids.budget_limit.text.strip()
            month = self.ids.budget_month.text.strip()

            if not limit_text:
                self.status_message = "Ingrese el límite"
                return

            if category_name == "Seleccionar...":
                self.status_message = "Seleccione una categoría"
                return

            if not month:
                self.status_message = "Ingrese el mes (YYYY-MM)"
                return

            # Obtener ID de categoría
            categories = self.category_service.list_all()
            category = next((c for c in categories if c.name == category_name), None)

            if not category:
                self.status_message = "Categoría no encontrada"
                return

            limit = float(limit_text)

            if self.selected_budget_id:
                # Editar existente
                from gf_mobile.persistence.models import Budget
                session = self.budget_service.session
                budget = session.query(Budget).filter(
                    Budget.id == self.selected_budget_id
                ).first()
                if budget:
                    budget.category_id = category.id
                    budget.limit = limit
                    budget.month = month
                    session.commit()
                    self.status_message = "Presupuesto actualizado"
            else:
                # Crear nuevo
                from gf_mobile.services.budget_service import BudgetInput
                self.budget_service.create(BudgetInput(
                    category_id=category.id,
                    limit=limit,
                    month=month,
                ))
                self.status_message = "Presupuesto creado"

            self.on_clear()
            self.refresh()

        except ValueError:
            self.status_message = "Ingrese un límite válido"
        except Exception as exc:
            self.status_message = f"Error: {str(exc)}"

    def on_clear(self) -> None:
        """Limpia el formulario"""
        self.ids.budget_category.text = "Seleccionar..."
        self.ids.budget_limit.text = ""
        self.ids.budget_month.text = self.default_month
        self.selected_budget_id = None

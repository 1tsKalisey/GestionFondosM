"""
DashboardScreen - Resumen completo de la situación financiera
Muestra KPIs, presupuestos, salud financiera y acciones rápidas
"""

from datetime import datetime, timedelta
from typing import Optional

from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import ScrollView
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.progressbar import MDProgressBar


Builder.load_string(
    """
<DashboardScreen>:
    name: "dashboard"

    ScrollView:
        MDBoxLayout:
            orientation: "vertical"
            padding: "16dp"
            spacing: "12dp"
            size_hint_y: None
            height: self.minimum_height

            # Header
            MDBoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: "48dp"
                spacing: "8dp"

                MDLabel:
                    text: "Dashboard"
                    font_style: "H6"
                    halign: "left"
                    size_hint_x: 0.6

                MDLabel:
                    text: root.date_range
                    theme_text_color: "Hint"
                    halign: "right"
                    size_hint_x: 0.4

            # ==================== KPIs PRINCIPALES ====================
            MDLabel:
                text: "Resumen mes actual"
                font_style: "Body2"
                bold: True
                size_hint_y: None
                height: "24dp"

            MDGridLayout:
                cols: 2
                spacing: "12dp"
                size_hint_y: None
                height: "220dp"

                # Saldo actual
                MDCard:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "8dp"
                    elevation: 2

                    MDLabel:
                        text: "Saldo Actual"
                        font_style: "Caption"
                        theme_text_color: "Hint"
                        size_hint_y: None
                        height: "20dp"

                    MDLabel:
                        text: root.balance_text
                        font_style: "H5"
                        halign: "center"
                        bold: True

                    MDLabel:
                        text: root.balance_status
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        halign: "center"
                        size_hint_y: None
                        height: "16dp"

                # Ingresos
                MDCard:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "8dp"
                    elevation: 2

                    MDLabel:
                        text: "Ingresos"
                        font_style: "Caption"
                        theme_text_color: "Hint"
                        size_hint_y: None
                        height: "20dp"

                    MDLabel:
                        text: root.income_text
                        font_style: "H5"
                        halign: "center"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: (0.15, 0.64, 0.80, 1)

                    MDLabel:
                        text: root.income_status
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        halign: "center"
                        size_hint_y: None
                        height: "16dp"

                # Gastos
                MDCard:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "8dp"
                    elevation: 2

                    MDLabel:
                        text: "Gastos"
                        font_style: "Caption"
                        theme_text_color: "Hint"
                        size_hint_y: None
                        height: "20dp"

                    MDLabel:
                        text: root.expenses_text
                        font_style: "H5"
                        halign: "center"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: (0.86, 0.16, 0.15, 1)

                    MDLabel:
                        text: root.expense_status
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        halign: "center"
                        size_hint_y: None
                        height: "16dp"

                # % Ahorro
                MDCard:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "8dp"
                    elevation: 2

                    MDLabel:
                        text: "Tasa de Ahorro"
                        font_style: "Caption"
                        theme_text_color: "Hint"
                        size_hint_y: None
                        height: "20dp"

                    MDLabel:
                        text: root.savings_percentage_text
                        font_style: "H5"
                        halign: "center"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: (0.49, 0.23, 0.93, 1)

                    MDLabel:
                        text: root.savings_status
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        halign: "center"
                        size_hint_y: None
                        height: "16dp"

            # ==================== DISTRIBUCIÓN DE GASTOS ====================
            MDLabel:
                text: "Distribución de gastos"
                font_style: "Body2"
                bold: True
                size_hint_y: None
                height: "24dp"

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "12dp"
                size_hint_y: None
                height: "220dp"
                elevation: 2

                # Necesidades
                MDBoxLayout:
                    orientation: "vertical"
                    spacing: "6dp"
                    size_hint_y: None
                    height: "56dp"

                    MDBoxLayout:
                        size_hint_y: None
                        height: "20dp"
                        spacing: "8dp"

                        MDLabel:
                            text: "Necesidades"
                            font_style: "Body2"
                            bold: True
                            size_hint_x: 0.5

                        MDLabel:
                            text: root.needs_percentage_text
                            font_style: "Body2"
                            halign: "right"
                            size_hint_x: 0.5

                    MDProgressBar:
                        value: root.needs_progress

                    MDLabel:
                        text: root.needs_detail_text
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        size_hint_y: None
                        height: "16dp"

                # Ocio/Deseos
                MDBoxLayout:
                    orientation: "vertical"
                    spacing: "6dp"
                    size_hint_y: None
                    height: "56dp"

                    MDBoxLayout:
                        size_hint_y: None
                        height: "20dp"
                        spacing: "8dp"

                        MDLabel:
                            text: "Ocio/Deseos"
                            font_style: "Body2"
                            bold: True
                            size_hint_x: 0.5

                        MDLabel:
                            text: root.wants_percentage_text
                            font_style: "Body2"
                            halign: "right"
                            size_hint_x: 0.5

                    MDProgressBar:
                        value: root.wants_progress

                    MDLabel:
                        text: root.wants_detail_text
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        size_hint_y: None
                        height: "16dp"

                # Ahorro/Deuda
                MDBoxLayout:
                    orientation: "vertical"
                    spacing: "6dp"
                    size_hint_y: None
                    height: "56dp"

                    MDBoxLayout:
                        size_hint_y: None
                        height: "20dp"
                        spacing: "8dp"

                        MDLabel:
                            text: "Ahorro/Deuda"
                            font_style: "Body2"
                            bold: True
                            size_hint_x: 0.5

                        MDLabel:
                            text: root.savings_budget_text
                            font_style: "Body2"
                            halign: "right"
                            size_hint_x: 0.5

                    MDProgressBar:
                        value: root.savings_budget_progress

                    MDLabel:
                        text: root.savings_budget_detail_text
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        size_hint_y: None
                        height: "16dp"

            # ==================== SALUD FINANCIERA ====================
            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "8dp"
                size_hint_y: None
                height: "120dp"
                elevation: 2

                MDBoxLayout:
                    orientation: "horizontal"
                    spacing: "8dp"
                    size_hint_y: None
                    height: "20dp"

                    MDLabel:
                        text: "Salud Financiera"
                        font_style: "Body2"
                        bold: True
                        size_hint_x: 0.6

                    MDLabel:
                        text: root.health_score_text
                        font_style: "Body2"
                        halign: "right"
                        bold: True
                        size_hint_x: 0.4

                MDProgressBar:
                    value: root.health_score_progress
                    size_hint_y: None
                    height: "4dp"

                MDLabel:
                    text: root.health_status
                    theme_text_color: "Hint"
                    font_style: "Caption"
                    size_hint_y: None
                    height: "16dp"

            # ==================== ACCIONES RÁPIDAS ====================
            MDBoxLayout:
                orientation: "horizontal"
                spacing: "8dp"
                size_hint_y: None
                height: "48dp"

                MDRaisedButton:
                    text: "+ Gasto"
                    on_release: root.on_new_transaction('gasto')

                MDRaisedButton:
                    text: "+ Ingreso"
                    on_release: root.on_new_transaction('ingreso')

                MDRaisedButton:
                    text: "📈 Reportes"
                    on_release: root.on_view_reports()

            # Información
            MDLabel:
                text: root.status_message
                theme_text_color: "Hint"
                halign: "center"
                font_style: "Caption"
                size_hint_y: None
                height: "24dp"

            # ==================== NAVEGACIÓN ====================
            MDBoxLayout:
                orientation: "horizontal"
                spacing: "4dp"
                padding: "4dp"
                size_hint_y: None
                height: "52dp"

                MDFlatButton:
                    text: "💳 Transacciones"
                    on_release: root.manager.current = 'transactions'

                MDFlatButton:
                    text: "🏷️ Categorías"
                    on_release: root.manager.current = 'categories'

                MDFlatButton:
                    text: "💰 Presupuestos"
                    on_release: root.manager.current = 'budgets'

                MDFlatButton:
                    text: "📈 Reportes"
                    on_release: root.manager.current = 'reports'
    """
)


class DashboardScreen(Screen):
    """Pantalla de dashboard con resumen financiero completo."""

    # Propiedades de KPIs
    date_range = StringProperty("Este mes")
    balance_text = StringProperty("€ 0.00")
    balance_status = StringProperty("")
    income_text = StringProperty("€ 0.00")
    income_status = StringProperty("")
    expenses_text = StringProperty("€ 0.00")
    expense_status = StringProperty("")
    savings_percentage_text = StringProperty("0.0%")
    savings_status = StringProperty("")
    
    # Propiedades de presu puestos
    needs_percentage_text = StringProperty("0%")
    needs_progress = NumericProperty(0)
    needs_detail_text = StringProperty("€ 0.00")
    
    wants_percentage_text = StringProperty("0%")
    wants_progress = NumericProperty(0)
    wants_detail_text = StringProperty("€ 0.00")
    
    savings_budget_text = StringProperty("0%")
    savings_budget_progress = NumericProperty(0)
    savings_budget_detail_text = StringProperty("€ 0.00")
    
    # Propiedades de salud
    health_score_text = StringProperty("0 / 900")
    health_score_progress = NumericProperty(0)
    health_status = StringProperty("Sin datos")
    
    # Información
    status_message = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = None
        self.budget_service = None
        self.report_service = None
        self.category_service = None

    def on_enter(self):
        """Se llama cuando la pantalla se muestra"""
        self.refresh()

    def refresh(self) -> None:
        """Recarga el dashboard con datos actuales"""
        try:
            if not self.transaction_service:
                self.status_message = "TransactionService no configurado"
                return

            # Calcular rango del mes actual
            today = datetime.now()
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

            # Obtener transacciones del mes
            transactions = self.transaction_service.list_all(limit=500)
            month_transactions = [
                tx for tx in transactions
                if start_date.date() <= tx.occurred_at.date() <= end_date.date()
            ]

            # Calcular KPIs principales
            total_income = sum(tx.amount for tx in month_transactions if tx.type == "ingreso")
            total_expenses = sum(tx.amount for tx in month_transactions if tx.type == "gasto")
            balance = total_income - total_expenses
            savings_pct = (balance / total_income * 100) if total_income > 0 else 0

            # Actualizar textos de KPI
            self.balance_text = f"€ {balance:.2f}"
            self.balance_status = "Positivo ✓" if balance >= 0 else "Negativo ✗"
            
            self.income_text = f"€ {total_income:.2f}"
            self.income_status = f"{len([tx for tx in month_transactions if tx.type == 'ingreso'])} ingresos"
            
            self.expenses_text = f"€ {total_expenses:.2f}"
            self.expense_status = f"{len([tx for tx in month_transactions if tx.type == 'gasto'])} gastos"
            
            self.savings_percentage_text = f"{savings_pct:.1f}%"
            self.savings_status = "Bueno ✓" if savings_pct >= 20 else "Mejorable"

            # Actualizar presupuesto por categoría
            self._update_budget_distribution(month_transactions)

            # Actualizar salud financiera
            self._update_health_score(balance, total_income, total_expenses)

            # Actualizar información
            self.date_range = f"{start_date.strftime('%d %b')} - {end_date.strftime('%d %b, %Y')}"
            self.status_message = f"{len(month_transactions)} transacciones este mes"

        except Exception as exc:
            self.status_message = f"Error: {str(exc)}"
            import traceback
            traceback.print_exc()

    def _update_budget_distribution(self, transactions) -> None:
        """Actualiza la distribución de gastos por categoría"""
        try:
            needs_amount = 0.0
            wants_amount = 0.0
            savings_amount = 0.0

            for tx in transactions:
                if tx.type != "gasto":
                    continue
                    
                amount = float(tx.amount) if tx.amount else 0.0
                if hasattr(tx, 'category') and tx.category:
                    group = tx.category.budget_group
                    if group == "Necesidades":
                        needs_amount += amount
                    elif group == "Ocio/Deseos":
                        wants_amount += amount
                    elif group == "Ahorro/Deuda":
                        savings_amount += amount

            total = needs_amount + wants_amount + savings_amount
            
            if total > 0:
                needs_pct = (needs_amount / total) * 100
                wants_pct = (wants_amount / total) * 100
                savings_pct = (savings_amount / total) * 100
                
                self.needs_progress = min(100, needs_pct)
                self.wants_progress = min(100, wants_pct)
                self.savings_budget_progress = min(100, savings_pct)
                
                self.needs_percentage_text = f"{needs_pct:.0f}%"
                self.wants_percentage_text = f"{wants_pct:.0f}%"
                self.savings_budget_text = f"{savings_pct:.0f}%"
                
                self.needs_detail_text = f"€ {needs_amount:.2f}"
                self.wants_detail_text = f"€ {wants_amount:.2f}"
                self.savings_budget_detail_text = f"€ {savings_amount:.2f}"
            else:
                self.needs_progress = 0
                self.wants_progress = 0
                self.savings_budget_progress = 0
                self.needs_percentage_text = "0%"
                self.wants_percentage_text = "0%"
                self.savings_budget_text = "0%"
                self.needs_detail_text = "€ 0.00"
                self.wants_detail_text = "€ 0.00"
                self.savings_budget_detail_text = "€ 0.00"
                
        except Exception as exc:
            self.status_message = f"Error en presupuesto: {str(exc)}"

    def _update_health_score(self, balance: float, income: float, expenses: float) -> None:
        """Calcula y actualiza el score de salud financiera"""
        try:
            score = 0
            max_score = 900
            
            # Factor 1: Saldo positivo (max 300 puntos)
            if balance > 0:
                score += min(300, int(balance / 10))
            
            # Factor 2: Relación ingreso/gasto (max 300 puntos)
            if income > 0:
                ratio = income / expenses if expenses > 0 else income
                if ratio > 1.2:  # Al menos 20% de ahorro
                    score += 300
                elif ratio > 1.0:
                    score += 200
                else:
                    score += 100
            
            # Factor 3: Número de transacciones (max 300 puntos)
            # (Representado implícitamente en la presencia de datos)
            score += 150  # Base
            
            # Asegurar que no exceda max_score
            score = min(max_score, score)
            
            # Actualizar propiedades
            self.health_score_text = f"{score} / {max_score}"
            self.health_score_progress = (score / max_score) * 100
            
            if score >= 700:
                self.health_status = "Excelente ★★★★★"
            elif score >= 550:
                self.health_status = "Buena ★★★★"
            elif score >= 400:
                self.health_status = "Correcta ★★★"
            elif score >= 250:
                self.health_status = "Por mejorar ★★"
            else:
                self.health_status = "Crítica ★"
                
        except Exception as exc:
            self.health_status = f"Error: {str(exc)}"

    def on_new_transaction(self, tx_type: str = "gasto") -> None:
        """Navega a agregar transacción"""
        # Pasar el tipo de transacción a la siguiente pantalla si es posible
        try:
            self.manager.current = "add_transaction"
            # Aquí podrías pasar tx_type al siguiente screen si lo necesitas
        except Exception as e:
            self.status_message = f"Error: {str(e)}"

    def on_view_reports(self) -> None:
        """Navega a reportes"""
        try:
            self.manager.current = "reports"
        except Exception as e:
            self.status_message = f"Error: {str(e)}"

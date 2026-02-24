"""
Dashboard screen.
"""

from datetime import datetime, timedelta

from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from gf_mobile.ui.navigation import NavigationBar


Builder.load_string(
    """
<DashboardScreen>:
    name: "dashboard"

    MDBoxLayout:
        orientation: "vertical"
        padding: "12dp"
        spacing: "8dp"

        MDBoxLayout:
            size_hint_y: None
            height: "42dp"

            MDLabel:
                text: "Resumen"
                font_style: "H6"
                bold: True

            MDLabel:
                text: root.date_range
                halign: "right"
                theme_text_color: "Hint"
                text_size: self.width, None
                shorten: True
                shorten_from: "right"

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                spacing: "10dp"
                size_hint_y: None
                height: self.minimum_height

                MDGridLayout:
                    cols: 2
                    spacing: "10dp"
                    size_hint_y: None
                    height: self.minimum_height

                    MDCard:
                        orientation: "vertical"
                        padding: "12dp"
                        size_hint_y: None
                        height: "120dp"
                        MDLabel:
                            text: "Saldo"
                            theme_text_color: "Hint"
                            font_style: "Caption"
                        MDLabel:
                            text: root.balance_text
                            font_style: "H6"
                            bold: True
                        MDLabel:
                            text: root.balance_status
                            theme_text_color: "Hint"
                            font_style: "Caption"

                    MDCard:
                        orientation: "vertical"
                        padding: "12dp"
                        size_hint_y: None
                        height: "120dp"
                        MDLabel:
                            text: "Ingresos"
                            theme_text_color: "Hint"
                            font_style: "Caption"
                        MDLabel:
                            text: root.income_text
                            font_style: "H6"
                            bold: True
                        MDLabel:
                            text: root.income_status
                            theme_text_color: "Hint"
                            font_style: "Caption"

                    MDCard:
                        orientation: "vertical"
                        padding: "12dp"
                        size_hint_y: None
                        height: "120dp"
                        MDLabel:
                            text: "Gastos"
                            theme_text_color: "Hint"
                            font_style: "Caption"
                        MDLabel:
                            text: root.expenses_text
                            font_style: "H6"
                            bold: True
                        MDLabel:
                            text: root.expense_status
                            theme_text_color: "Hint"
                            font_style: "Caption"

                    MDCard:
                        orientation: "vertical"
                        padding: "12dp"
                        size_hint_y: None
                        height: "120dp"
                        MDLabel:
                            text: "Ahorro"
                            theme_text_color: "Hint"
                            font_style: "Caption"
                        MDLabel:
                            text: root.savings_percentage_text
                            font_style: "H6"
                            bold: True
                        MDLabel:
                            text: root.savings_status
                            theme_text_color: "Hint"
                            font_style: "Caption"

                MDCard:
                    orientation: "vertical"
                    padding: "12dp"
                    spacing: "8dp"
                    adaptive_height: True

                    MDLabel:
                        text: "Distribucion"
                        bold: True
                        font_style: "Body2"
                        size_hint_y: None
                        height: self.texture_size[1]

                    MDLabel:
                        text: "Necesidades: " + root.needs_percentage_text + " | " + root.needs_detail_text
                        font_style: "Caption"
                        text_size: self.width, None
                        size_hint_y: None
                        height: self.texture_size[1]
                    MDProgressBar:
                        value: root.needs_progress
                        size_hint_y: None
                        height: "6dp"

                    MDLabel:
                        text: "Ocio: " + root.wants_percentage_text + " | " + root.wants_detail_text
                        font_style: "Caption"
                        text_size: self.width, None
                        size_hint_y: None
                        height: self.texture_size[1]
                    MDProgressBar:
                        value: root.wants_progress
                        size_hint_y: None
                        height: "6dp"

                    MDLabel:
                        text: "Ahorro/Deuda: " + root.savings_budget_text + " | " + root.savings_budget_detail_text
                        font_style: "Caption"
                        text_size: self.width, None
                        size_hint_y: None
                        height: self.texture_size[1]
                    MDProgressBar:
                        value: root.savings_budget_progress
                        size_hint_y: None
                        height: "6dp"

                MDCard:
                    orientation: "vertical"
                    padding: "12dp"
                    spacing: "8dp"
                    adaptive_height: True

                    MDLabel:
                        text: "Salud financiera"
                        bold: True
                        font_style: "Body2"
                        size_hint_y: None
                        height: self.texture_size[1]
                    MDLabel:
                        text: root.health_score_text
                        size_hint_y: None
                        height: self.texture_size[1]
                    MDProgressBar:
                        value: root.health_score_progress
                        size_hint_y: None
                        height: "6dp"
                    MDLabel:
                        text: root.health_status
                        theme_text_color: "Hint"
                        size_hint_y: None
                        height: self.texture_size[1]

                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "8dp"

                    MDBoxLayout:
                        size_hint_y: None
                        height: "44dp"
                        spacing: "8dp"

                        MDRaisedButton:
                            text: "+ Gasto"
                            on_release: root.on_new_transaction("gasto")

                        MDRaisedButton:
                            text: "+ Ingreso"
                            on_release: root.on_new_transaction("ingreso")

                    MDFlatButton:
                        text: "Ver movimientos"
                        size_hint_y: None
                        height: "42dp"
                        on_release: root.on_view_transactions()

                MDLabel:
                    text: root.status_message
                    theme_text_color: "Hint"
                    text_size: self.width, None
                    max_lines: 2
                    shorten: True
                    shorten_from: "right"
                    size_hint_y: None
                    height: "22dp"

        NavigationBar:
            id: nav_bar
    """
)


class DashboardScreen(Screen):
    date_range = StringProperty("Este mes")
    balance_text = StringProperty("EUR 0.00")
    balance_status = StringProperty("")
    income_text = StringProperty("EUR 0.00")
    income_status = StringProperty("")
    expenses_text = StringProperty("EUR 0.00")
    expense_status = StringProperty("")
    savings_percentage_text = StringProperty("0.0%")
    savings_status = StringProperty("")

    needs_percentage_text = StringProperty("0%")
    needs_progress = NumericProperty(0)
    needs_detail_text = StringProperty("EUR 0.00")

    wants_percentage_text = StringProperty("0%")
    wants_progress = NumericProperty(0)
    wants_detail_text = StringProperty("EUR 0.00")

    savings_budget_text = StringProperty("0%")
    savings_budget_progress = NumericProperty(0)
    savings_budget_detail_text = StringProperty("EUR 0.00")

    health_score_text = StringProperty("0 / 900")
    health_score_progress = NumericProperty(0)
    health_status = StringProperty("Sin datos")

    status_message = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = None
        self.budget_service = None
        self.report_service = None
        self.category_service = None

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "dashboard"
        self.refresh()

    def refresh(self) -> None:
        try:
            if not self.transaction_service:
                self.status_message = "TransactionService no configurado"
                return

            today = datetime.now()
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

            transactions = self.transaction_service.list_all(limit=500)
            month_transactions = [
                tx for tx in transactions if start_date.date() <= tx.occurred_at.date() <= end_date.date()
            ]

            total_income = sum(tx.amount for tx in month_transactions if tx.type == "ingreso")
            total_expenses = sum(tx.amount for tx in month_transactions if tx.type == "gasto")
            balance = total_income - total_expenses
            savings_pct = (balance / total_income * 100) if total_income > 0 else 0

            self.balance_text = f"EUR {balance:.2f}"
            self.balance_status = "Positivo" if balance >= 0 else "Negativo"
            self.income_text = f"EUR {total_income:.2f}"
            self.income_status = f"{len([tx for tx in month_transactions if tx.type == 'ingreso'])} ingresos"
            self.expenses_text = f"EUR {total_expenses:.2f}"
            self.expense_status = f"{len([tx for tx in month_transactions if tx.type == 'gasto'])} gastos"
            self.savings_percentage_text = f"{savings_pct:.1f}%"
            self.savings_status = "Bueno" if savings_pct >= 20 else "Mejorable"

            self._update_budget_distribution(month_transactions)
            self._update_health_score(balance, total_income, total_expenses)

            self.date_range = f"{start_date.strftime('%d %b')} - {end_date.strftime('%d %b, %Y')}"
            self.status_message = f"{len(month_transactions)} movimientos este mes"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def _update_budget_distribution(self, transactions) -> None:
        try:
            needs_amount = 0.0
            wants_amount = 0.0
            savings_amount = 0.0

            for tx in transactions:
                if tx.type != "gasto":
                    continue
                amount = float(tx.amount) if tx.amount else 0.0
                if hasattr(tx, "category") and tx.category:
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
                self.needs_detail_text = f"EUR {needs_amount:.2f}"
                self.wants_detail_text = f"EUR {wants_amount:.2f}"
                self.savings_budget_detail_text = f"EUR {savings_amount:.2f}"
            else:
                self.needs_progress = 0
                self.wants_progress = 0
                self.savings_budget_progress = 0
                self.needs_percentage_text = "0%"
                self.wants_percentage_text = "0%"
                self.savings_budget_text = "0%"
                self.needs_detail_text = "EUR 0.00"
                self.wants_detail_text = "EUR 0.00"
                self.savings_budget_detail_text = "EUR 0.00"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def _update_health_score(self, balance: float, income: float, expenses: float) -> None:
        try:
            score = 0
            max_score = 900
            if balance > 0:
                score += min(300, int(balance / 10))
            if income > 0:
                ratio = income / expenses if expenses > 0 else income
                if ratio > 1.2:
                    score += 300
                elif ratio > 1.0:
                    score += 200
                else:
                    score += 100
            score += 150
            score = min(max_score, score)

            self.health_score_text = f"{score} / {max_score}"
            self.health_score_progress = (score / max_score) * 100
            if score >= 700:
                self.health_status = "Excelente"
            elif score >= 550:
                self.health_status = "Buena"
            elif score >= 400:
                self.health_status = "Correcta"
            elif score >= 250:
                self.health_status = "Por mejorar"
            else:
                self.health_status = "Critica"
        except Exception:
            self.health_status = "Error calculando salud"

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 120:
            message = f"{message[:117]}..."
        return f"Error: {message}"

    def on_new_transaction(self, tx_type: str = "gasto") -> None:
        try:
            self.manager.current = "add_transaction"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def on_view_reports(self) -> None:
        try:
            self.manager.current = "reports"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def on_view_transactions(self) -> None:
        try:
            self.manager.current = "transactions"
        except Exception as exc:
            self.status_message = self._short_error(exc)

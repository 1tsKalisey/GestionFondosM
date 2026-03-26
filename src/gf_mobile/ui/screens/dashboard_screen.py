"""
Dashboard screen.
"""

from datetime import datetime, timedelta

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from gf_mobile.core.transaction_types import normalize_transaction_type
from gf_mobile.ui.navigation import NavigationBar
from gf_mobile.ui.responsive import ResponsiveManager
from gf_mobile.ui.screen_utils import metric_columns_for_device
from gf_mobile.ui.widgets.shell import HeroCard, MetricCard, ScreenHeader, SectionCard


Builder.load_string(
    """
<DashboardScreen>:
    name: "dashboard"

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
                    eyebrow: "SHELL"
                    title: "Resumen"
                    subtitle: root.date_range
                    muted_color: app.kivy_palette["text_secondary"]

                HeroCard:
                    eyebrow: "Estado actual"
                    title: root.balance_text
                    supporting_text: root.hero_supporting_text
                    card_color: app.kivy_palette["primary"]
                    title_color: 1, 1, 1, 1
                    eyebrow_color: 0.9, 0.95, 1, 1

                    MDBoxLayout:
                        adaptive_height: True
                        spacing: "10dp"

                        MDRaisedButton:
                            text: "+ Gasto"
                            md_bg_color: app.kivy_palette["accent"]
                            on_release: root.on_new_transaction("gasto")

                        MDFlatButton:
                            text: "Ver movimientos"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            on_release: root.on_view_transactions()

                MDGridLayout:
                    cols: root.metric_columns
                    spacing: "10dp"
                    size_hint_y: None
                    height: self.minimum_height

                    MetricCard:
                        label: "Saldo total"
                        value: root.balance_text
                        helper: root.balance_status
                        card_color: app.kivy_palette["surface"]
                        value_color: app.kivy_palette["text_primary"]
                        muted_color: app.kivy_palette["text_secondary"]

                    MetricCard:
                        label: "Ingresos"
                        value: root.income_text
                        helper: root.income_status
                        card_color: app.kivy_palette["surface"]
                        value_color: app.kivy_palette["success"]
                        muted_color: app.kivy_palette["text_secondary"]

                    MetricCard:
                        label: "Gastos"
                        value: root.expenses_text
                        helper: root.expense_status
                        card_color: app.kivy_palette["surface"]
                        value_color: app.kivy_palette["error"]
                        muted_color: app.kivy_palette["text_secondary"]

                    MetricCard:
                        label: "Ahorro"
                        value: root.savings_percentage_text
                        helper: root.savings_status
                        card_color: app.kivy_palette["surface"]
                        value_color: app.kivy_palette["accent"]
                        muted_color: app.kivy_palette["text_secondary"]

                SectionCard:
                    title: "Distribucion del gasto"
                    subtitle: "Lectura rapida por grupo presupuestario"
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

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

                SectionCard:
                    title: "Salud financiera"
                    subtitle: "Score y lectura operativa del periodo"
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

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

                SectionCard:
                    title: "Siguiente paso"
                    subtitle: "Acciones recomendadas desde la shell principal"
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDBoxLayout:
                        adaptive_height: True
                        spacing: "8dp"

                        MDRaisedButton:
                            text: "+ Ingreso"
                            md_bg_color: app.kivy_palette["primary"]
                            on_release: root.on_new_transaction("ingreso")

                        MDFlatButton:
                            text: "Categorias"
                            theme_text_color: "Custom"
                            text_color: app.kivy_palette["primary"]
                            on_release: root.manager.current = "categories"

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
    hero_supporting_text = StringProperty("Sin movimientos recientes")
    metric_columns = NumericProperty(2)

    status_message = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = None
        self.budget_service = None
        self.report_service = None
        self.category_service = None
        self._refresh_requested = True

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "dashboard"
        self._update_responsive_layout()
        self.request_refresh()

    def request_refresh(self) -> None:
        self._refresh_requested = True
        Clock.unschedule(self._run_deferred_refresh)
        Clock.schedule_once(self._run_deferred_refresh, 0)

    def _run_deferred_refresh(self, *_args) -> None:
        if not self._refresh_requested:
            return
        self._refresh_requested = False
        self.refresh()

    def _update_responsive_layout(self) -> None:
        self.metric_columns = metric_columns_for_device(
            is_phone=ResponsiveManager.is_phone(),
            orientation=ResponsiveManager.get_orientation(),
        )

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
            period_transactions = month_transactions
            period_label = f"{start_date.strftime('%d %b')} - {end_date.strftime('%d %b, %Y')}"
            using_fallback_period = False
            if not month_transactions and transactions:
                fallback_start = today - timedelta(days=30)
                period_transactions = [
                    tx for tx in transactions if fallback_start.date() <= tx.occurred_at.date() <= today.date()
                ]
                period_label = f"Ultimos 30 dias ({fallback_start.strftime('%d %b')} - {today.strftime('%d %b, %Y')})"
                using_fallback_period = True

            total_income = sum(
                tx.amount for tx in period_transactions if normalize_transaction_type(tx.type) == "ingreso"
            )
            total_expenses = sum(
                tx.amount for tx in period_transactions if normalize_transaction_type(tx.type) == "gasto"
            )
            period_balance = total_income - total_expenses
            total_balance = self._calculate_total_balance(transactions)
            savings_pct = (period_balance / total_income * 100) if total_income > 0 else 0

            self.balance_text = f"EUR {total_balance:.2f}"
            self.balance_status = "Positivo" if total_balance >= 0 else "Negativo"
            self.income_text = f"EUR {total_income:.2f}"
            self.income_status = (
                f"{len([tx for tx in period_transactions if normalize_transaction_type(tx.type) == 'ingreso'])} ingresos"
            )
            self.expenses_text = f"EUR {total_expenses:.2f}"
            self.expense_status = (
                f"{len([tx for tx in period_transactions if normalize_transaction_type(tx.type) == 'gasto'])} gastos"
            )
            self.savings_percentage_text = f"{savings_pct:.1f}%"
            self.savings_status = "Bueno" if savings_pct >= 20 else "Mejorable"
            self.hero_supporting_text = (
                f"{self.income_status} · {self.expense_status}"
                if period_transactions
                else "Empieza registrando movimientos para activar el resumen"
            )

            self._update_budget_distribution(period_transactions)
            self._update_health_score(period_balance, total_income, total_expenses)

            self.date_range = period_label
            if using_fallback_period:
                self.status_message = (
                    f"{len(period_transactions)} movimientos en ultimos 30 dias "
                    "(sin movimientos en este mes)"
                )
            else:
                self.status_message = f"{len(month_transactions)} movimientos este mes"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def _calculate_total_balance(self, transactions) -> float:
        service = self.transaction_service
        if service is None:
            return 0.0
        try:
            return float(service.total_balance())
        except Exception:
            return 0.0

    def _update_budget_distribution(self, transactions) -> None:
        try:
            needs_amount = 0.0
            wants_amount = 0.0
            savings_amount = 0.0

            for tx in transactions:
                if normalize_transaction_type(tx.type) != "gasto":
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
            add_screen = self.manager.get_screen("add_transaction")
            if hasattr(add_screen, "prepare_for_entry"):
                add_screen.prepare_for_entry(tx_type=tx_type, origin_screen="dashboard")
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

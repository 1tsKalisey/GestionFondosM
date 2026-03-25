"""
Reports screen.
"""

from datetime import datetime, timedelta

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem

from gf_mobile.core.transaction_types import normalize_transaction_type
from gf_mobile.ui.dialogs import build_selection_dialog
from gf_mobile.ui.navigation import NavigationBar
from gf_mobile.ui.widgets.shell import HeroCard, ScreenHeader, SectionCard


Builder.load_string(
    """
<ReportsScreen>:
    name: "reports"

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
                    eyebrow: "LECTURA"
                    title: "Reportes"
                    subtitle: "Comparativas por categoria y grupo"
                    muted_color: app.kivy_palette["text_secondary"]

                HeroCard:
                    eyebrow: "Rango activo"
                    title: root.report_range_text
                    supporting_text: root.status_message or "Actualiza el rango para recalcular el periodo."
                    card_color: app.kivy_palette["primary"]
                    title_color: 1, 1, 1, 1
                    eyebrow_color: 0.9, 0.95, 1, 1

                    MDRaisedButton:
                        text: "Actualizar"
                        md_bg_color: app.kivy_palette["accent"]
                        on_release: root.refresh()

                SectionCard:
                    title: "Periodo"
                    subtitle: "Define la ventana de analisis"
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDRaisedButton:
                        id: report_start
                        text: root.start_display
                        md_bg_color: app.kivy_palette["primary"]
                        on_release: root.open_range_picker()

                    MDRaisedButton:
                        id: report_end
                        text: root.end_display
                        md_bg_color: app.kivy_palette["primary"]
                        on_release: root.open_range_picker()

                    MDFlatButton:
                        text: "Ultimos 30 dias"
                        theme_text_color: "Custom"
                        text_color: app.kivy_palette["primary"]
                        on_release: root.apply_range_preset("30d")

                    MDFlatButton:
                        text: "Este mes"
                        theme_text_color: "Custom"
                        text_color: app.kivy_palette["primary"]
                        on_release: root.apply_range_preset("month")

                SectionCard:
                    title: "Por categoria"
                    subtitle: "Peso relativo del gasto"
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDList:
                        id: category_summary

                SectionCard:
                    title: "Por grupo presupuestario"
                    subtitle: "Necesidades, ocio y ahorro"
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDList:
                        id: budget_summary

        NavigationBar:
            id: nav_bar
    """
)


class ReportsScreen(Screen):
    status_message = StringProperty("")
    report_range_text = StringProperty("Sin rango")
    start_display = StringProperty("")
    end_display = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = None
        self.category_service = None
        self.budget_service = None
        self.report_service = None
        self._dialog = None

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "reports"
        self.apply_range_preset("30d")
        self.refresh()

    def refresh(self) -> None:
        try:
            if not self.transaction_service or not self.category_service:
                self.status_message = "Servicios no configurados"
                return

            start_text = self.start_display.strip()
            end_text = self.end_display.strip()
            if not start_text or not end_text:
                self.status_message = "Ingrese rango de fechas"
                return

            start_day = datetime.fromisoformat(start_text).date()
            end_day = datetime.fromisoformat(end_text).date()
            if start_day > end_day:
                self.status_message = "El inicio no puede ser posterior al fin"
                self._generate_category_summary([])
                self._generate_budget_summary([])
                return
            self.report_range_text = f"{start_text} -> {end_text}"
            transactions = self.transaction_service.list_all(limit=500)
            range_tx = [
                tx
                for tx in transactions
                if start_day <= tx.occurred_at.date() <= end_day
            ]

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
                if normalize_transaction_type(tx.type) != "gasto":
                    continue
                cat_name = "Sin categoria"
                if hasattr(tx, "category") and tx.category:
                    cat_name = tx.category.name
                category_totals.setdefault(cat_name, 0)
                category_totals[cat_name] += tx.amount

            total_expenses = sum(category_totals.values())
            if total_expenses <= 0:
                self._add_empty_summary(self.ids.category_summary, "Sin gastos en el rango activo")
                return
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
                if normalize_transaction_type(tx.type) != "gasto":
                    continue
                group = "Otros"
                if hasattr(tx, "category") and tx.category:
                    group = tx.category.budget_group or "Otros"
                if group in budget_groups:
                    budget_groups[group] += tx.amount

            total = sum(budget_groups.values())
            if total <= 0:
                self._add_empty_summary(self.ids.budget_summary, "Sin distribucion presupuestaria para mostrar")
                return
            for group_name, amount in budget_groups.items():
                pct = (amount / total * 100) if total > 0 else 0
                self.ids.budget_summary.add_widget(
                    OneLineListItem(text=f"{group_name}: EUR {amount:.2f} ({pct:.1f}%)")
                )
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def apply_range_preset(self, preset: str) -> None:
        today = datetime.now()
        if preset == "month":
            start = today.replace(day=1)
        else:
            start = today - timedelta(days=30)
        self.start_display = start.strftime("%Y-%m-%d")
        self.end_display = today.strftime("%Y-%m-%d")
        self.report_range_text = f"{self.start_display} -> {self.end_display}"

    def open_range_picker(self) -> None:
        self._open_selection_dialog(
            "Rango",
            ["Ultimos 7 dias", "Ultimos 30 dias", "Este mes", "Ultimos 90 dias"],
            self._select_range_option,
        )

    def _select_range_option(self, label: str) -> None:
        today = datetime.now()
        if label == "Ultimos 7 dias":
            start = today - timedelta(days=7)
        elif label == "Este mes":
            start = today.replace(day=1)
        elif label == "Ultimos 90 dias":
            start = today - timedelta(days=90)
        else:
            start = today - timedelta(days=30)
        self.start_display = start.strftime("%Y-%m-%d")
        self.end_display = today.strftime("%Y-%m-%d")
        self.report_range_text = f"{self.start_display} -> {self.end_display}"
        self.refresh()

    @staticmethod
    def _add_empty_summary(target, text: str) -> None:
        target.add_widget(
            OneLineListItem(
                text=text,
                disabled=True,
            )
        )

    def _open_selection_dialog(self, title: str, options, callback) -> None:
        self._dialog = build_selection_dialog(
            self._dialog,
            title=title,
            options=options,
            on_select=callback,
        )
        self._dialog.open()

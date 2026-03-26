"""
Transactions results screen.
"""

from datetime import datetime
from typing import Any, Dict, List

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import DictProperty, ListProperty, StringProperty
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from gf_mobile.core.transaction_types import normalize_transaction_type
from gf_mobile.ui.screen_utils import apply_palette_attrs, resolve_palette
from gf_mobile.ui.widgets.shell import EmptyStateCard, HeroCard, ScreenHeader

Builder.load_string(
    """
<TransactionsResultsScreen>:
    name: "transactions_results"

    MDBoxLayout:
        orientation: "vertical"
        padding: "16dp"
        spacing: "12dp"
        md_bg_color: root.page_bg_color

        ScreenHeader:
            eyebrow: "RESULTADOS"
            title: "Movimientos"
            subtitle: root.filters_summary
            muted_color: app.kivy_palette["text_secondary"]

        HeroCard:
            eyebrow: "Consulta activa"
            title: root.results_headline
            supporting_text: root.status_message or "Refina los filtros o crea una nueva transaccion."
            card_color: root.accent_color
            title_color: 1, 1, 1, 1
            eyebrow_color: 1, 1, 1, 0.82

            MDBoxLayout:
                adaptive_height: True
                spacing: "10dp"

                MDFlatButton:
                    text: "Filtros"
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 1
                    on_release: root.manager.current = "transactions"

                MDRaisedButton:
                    text: "+ Nuevo"
                    md_bg_color: app.kivy_palette["primary"]
                    on_release: root.open_new_transaction()

        ScrollView:
            MDBoxLayout:
                id: results_container
                orientation: "vertical"
                spacing: "8dp"
                size_hint_y: None
                height: self.minimum_height

        MDLabel:
            text: root.status_message
            halign: "center"
            theme_text_color: "Hint"
            font_style: "Caption"
            text_size: self.width, None
            max_lines: 2
            shorten: True
            shorten_from: "right"
            size_hint_y: None
            height: "22dp"
    """
)


class TransactionsResultsScreen(Screen):
    status_message = StringProperty("")
    active_filters = DictProperty({})
    filters_summary = StringProperty("Sin filtros")
    results_headline = StringProperty("0 movimientos")
    page_bg_color = ListProperty([0, 0, 0, 0])
    accent_color = ListProperty([0, 0, 0, 0])
    card_even_bg = ListProperty([0, 0, 0, 0])
    card_odd_bg = ListProperty([0, 0, 0, 0])
    empty_bg = ListProperty([0, 0, 0, 0])

    def __init__(self, transaction_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service
        self._refresh_requested = True

    def on_pre_enter(self, *args):
        self._apply_theme_colors()
        return super().on_pre_enter(*args)

    def on_enter(self, *args):
        self.request_refresh()
        return super().on_enter(*args)

    def request_refresh(self) -> None:
        self._refresh_requested = True
        Clock.unschedule(self._run_deferred_refresh)
        Clock.schedule_once(self._run_deferred_refresh, 0)

    def _run_deferred_refresh(self, *_args) -> None:
        if not self._refresh_requested:
            return
        self._refresh_requested = False
        self.refresh()

    def set_filters(self, filters: Dict[str, Any]) -> None:
        self.active_filters = dict(filters or {})
        self.filters_summary = self._build_filters_summary()

    def refresh(self) -> None:
        self.ids.results_container.clear_widgets()
        app = App.get_running_app()
        if not app or not hasattr(app, "list_transactions_snapshot"):
            self.status_message = "TransactionService no configurado"
            return

        try:
            transactions = app.list_transactions_snapshot(limit=500)
            filtered_txs = self._apply_filters_to_list(transactions)
            filtered_txs.sort(key=lambda tx: tx.occurred_at, reverse=True)
            if not filtered_txs:
                self.ids.results_container.add_widget(self._build_empty_card())
            for idx, tx in enumerate(filtered_txs):
                self.ids.results_container.add_widget(self._build_transaction_card(tx, idx))
            self.status_message = f"{len(filtered_txs)} movimientos"
            self.results_headline = self.status_message
        except Exception as exc:
            self.status_message = self._short_error(exc)
            self.results_headline = "Consulta no disponible"

    def open_new_transaction(self) -> None:
        try:
            add_screen = self.manager.get_screen("add_transaction")
            if hasattr(add_screen, "prepare_for_entry"):
                add_screen.prepare_for_entry(
                    tx_type="gasto",
                    origin_screen="transactions_results",
                )
            self.manager.current = "add_transaction"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def _build_empty_card(self) -> MDCard:
        card = EmptyStateCard(
            title="No hay movimientos",
            message="Prueba otro rango, otro tipo o elimina filtros.",
            card_color=self.empty_bg,
        )
        return card

    def _build_transaction_card(self, tx: Any, index: int = 0) -> MDCard:
        category_name = tx.category.name if hasattr(tx, "category") and tx.category else "Sin categoria"
        tx_type = normalize_transaction_type(tx.type)
        amount = float(tx.amount) if tx.amount is not None else 0.0
        palette = resolve_palette()
        if palette:
            amount_color = palette["success"] if tx_type == "ingreso" else palette["error"]
        else:
            amount_color = [0, 0.6, 0.3, 1] if tx_type == "ingreso" else [0.8, 0.2, 0.2, 1]
        badge_text = "INGRESO" if tx_type == "ingreso" else "GASTO" if tx_type == "gasto" else "MOV"
        date_text = tx.occurred_at.strftime("%d/%m/%Y")

        row_bg = self.card_even_bg if index % 2 == 0 else self.card_odd_bg
        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(96),
            padding=dp(10),
            spacing=dp(6),
            radius=[14, 14, 14, 14],
            md_bg_color=row_bg,
        )

        top_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(26), spacing=dp(8))
        badge = MDLabel(
            text=badge_text,
            size_hint_x=None,
            width=dp(70),
            halign="center",
            valign="middle",
            bold=True,
            theme_text_color="Custom",
            text_color=amount_color,
        )
        badge.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        top_row.add_widget(badge)
        top_row.add_widget(
            MDLabel(
                text=date_text,
                theme_text_color="Secondary",
                halign="right",
            )
        )
        card.add_widget(top_row)

        middle_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(8))
        middle_row.add_widget(
            MDLabel(
                text=category_name,
                bold=True,
                theme_text_color="Primary",
                size_hint_x=0.62,
                text_size=(None, None),
                shorten=True,
                shorten_from="right",
            )
        )
        middle_row.add_widget(
            MDLabel(
                text=f"EUR {amount:.2f}",
                bold=True,
                size_hint_x=0.38,
                halign="right",
                theme_text_color="Custom",
                text_color=amount_color,
            )
        )
        card.add_widget(middle_row)

        note_text = (getattr(tx, "note", None) or "").strip()
        card.add_widget(
            MDLabel(
                text=note_text if note_text else "Sin nota",
                theme_text_color="Secondary",
                font_style="Caption",
                text_size=(None, None),
                shorten=True,
                shorten_from="right",
            )
        )

        return card

    def _apply_filters_to_list(self, transactions: List[Any]) -> List[Any]:
        result = transactions

        if self.active_filters.get("type"):
            wanted_type = normalize_transaction_type(self.active_filters["type"])
            result = [tx for tx in result if normalize_transaction_type(tx.type) == wanted_type]

        if self.active_filters.get("categories"):
            selected_categories = set(self.active_filters["categories"])
            result = [
                tx
                for tx in result
                if hasattr(tx, "category") and tx.category and tx.category.name in selected_categories
            ]

        if self.active_filters.get("category"):
            wanted = self.active_filters["category"]
            result = [
                tx
                for tx in result
                if hasattr(tx, "category") and tx.category and tx.category.name == wanted
            ]

        if self.active_filters.get("date_from"):
            try:
                date_from = datetime.strptime(self.active_filters["date_from"], "%Y-%m-%d").date()
                result = [tx for tx in result if tx.occurred_at.date() >= date_from]
            except Exception:
                pass

        if self.active_filters.get("date_to"):
            try:
                date_to = datetime.strptime(self.active_filters["date_to"], "%Y-%m-%d").date()
                result = [tx for tx in result if tx.occurred_at.date() <= date_to]
            except Exception:
                pass

        if self.active_filters.get("amount_min") is not None:
            min_amount = self.active_filters["amount_min"]
            result = [tx for tx in result if float(tx.amount) >= min_amount]

        if self.active_filters.get("amount_max") is not None:
            max_amount = self.active_filters["amount_max"]
            result = [tx for tx in result if float(tx.amount) <= max_amount]

        return result

    def _build_filters_summary(self) -> str:
        parts: list[str] = []
        if self.active_filters.get("type"):
            parts.append(str(self.active_filters["type"]))
        if self.active_filters.get("categories"):
            parts.append(f"{len(self.active_filters['categories'])} categorias")
        if self.active_filters.get("date_from") or self.active_filters.get("date_to"):
            start = self.active_filters.get("date_from") or "..."
            end = self.active_filters.get("date_to") or "..."
            parts.append(f"{start} -> {end}")
        if self.active_filters.get("amount_min") is not None or self.active_filters.get("amount_max") is not None:
            min_amount = self.active_filters.get("amount_min")
            max_amount = self.active_filters.get("amount_max")
            parts.append(f"EUR {min_amount if min_amount is not None else 0} - {max_amount if max_amount is not None else '...'}")
        return " | ".join(parts) if parts else "Sin filtros"

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 120:
            message = f"{message[:117]}..."
        return f"Error: {message}"

    def _apply_theme_colors(self) -> None:
        apply_palette_attrs(
            self,
            {
                "accent_color": "primary",
                "page_bg_color": "background",
                "card_even_bg": "surface",
                "card_odd_bg": "background",
                "empty_bg": "surface",
            },
        )

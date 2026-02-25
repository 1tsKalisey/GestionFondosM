"""
Transactions results screen.
"""

from datetime import datetime
from typing import Any, Dict, List

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import DictProperty, ListProperty, StringProperty
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel


Builder.load_string(
    """
<TransactionsResultsScreen>:
    name: "transactions_results"

    MDBoxLayout:
        orientation: "vertical"
        padding: "12dp"
        spacing: "8dp"
        md_bg_color: root.page_bg_color

        MDBoxLayout:
            size_hint_y: None
            height: "44dp"
            spacing: "8dp"

            MDFlatButton:
                text: "Filtros"
                size_hint_x: None
                width: "84dp"
                on_release: root.manager.current = "transactions"

            MDLabel:
                text: "Movimientos"
                font_style: "H6"
                bold: True

            MDRaisedButton:
                text: "+ Nuevo"
                size_hint_x: None
                width: "96dp"
                md_bg_color: root.accent_color
                on_release: root.manager.current = "add_transaction"

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
    page_bg_color = ListProperty([0, 0, 0, 0])
    accent_color = ListProperty([0, 0, 0, 0])
    card_even_bg = ListProperty([0, 0, 0, 0])
    card_odd_bg = ListProperty([0, 0, 0, 0])
    empty_bg = ListProperty([0, 0, 0, 0])

    def __init__(self, transaction_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service

    def on_pre_enter(self, *args):
        self._apply_theme_colors()
        self.refresh()
        return super().on_pre_enter(*args)

    def set_filters(self, filters: Dict[str, Any]) -> None:
        self.active_filters = dict(filters or {})

    def refresh(self) -> None:
        self.ids.results_container.clear_widgets()
        if not self.transaction_service:
            self.status_message = "TransactionService no configurado"
            return

        try:
            transactions = self.transaction_service.list_all(limit=500)
            filtered_txs = self._apply_filters_to_list(transactions)
            filtered_txs.sort(key=lambda tx: tx.occurred_at, reverse=True)
            if not filtered_txs:
                self.ids.results_container.add_widget(self._build_empty_card())
            for idx, tx in enumerate(filtered_txs):
                self.ids.results_container.add_widget(self._build_transaction_card(tx, idx))
            self.status_message = f"{len(filtered_txs)} movimientos"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def _build_empty_card(self) -> MDCard:
        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(76),
            padding=dp(12),
            radius=[14, 14, 14, 14],
            md_bg_color=self.empty_bg,
        )
        card.add_widget(
            MDLabel(
                text="No hay movimientos con esos filtros",
                theme_text_color="Secondary",
                halign="center",
            )
        )
        return card

    def _build_transaction_card(self, tx: Any, index: int = 0) -> MDCard:
        category_name = tx.category.name if hasattr(tx, "category") and tx.category else "Sin categoria"
        tx_type = (tx.type or "").lower()
        amount = float(tx.amount) if tx.amount is not None else 0.0
        app = App.get_running_app()
        palette = getattr(app, "kivy_palette", None) if app else None
        if palette:
            amount_color = palette["success"] if tx_type == "ingreso" else palette["error"]
        else:
            from gf_mobile.ui.theme import get_kivy_palette

            fallback = get_kivy_palette()
            amount_color = fallback["success"] if tx_type == "ingreso" else fallback["error"]
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
            result = [tx for tx in result if tx.type == self.active_filters["type"]]

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

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 120:
            message = f"{message[:117]}..."
        return f"Error: {message}"

    def _apply_theme_colors(self) -> None:
        app = App.get_running_app()
        palette = getattr(app, "kivy_palette", None) if app else None
        if palette:
            self.accent_color = palette["primary"]
            self.page_bg_color = palette["background"]
            self.card_even_bg = palette["surface"]
            self.card_odd_bg = palette["background"]
            self.empty_bg = palette["surface"]
        else:
            from gf_mobile.ui.theme import get_kivy_palette

            fallback = get_kivy_palette()
            self.accent_color = fallback["primary"]
            self.page_bg_color = fallback["background"]
            self.card_even_bg = fallback["surface"]
            self.card_odd_bg = fallback["background"]
            self.empty_bg = fallback["surface"]

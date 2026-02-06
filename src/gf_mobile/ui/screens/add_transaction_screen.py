"""
AddTransactionScreen
"""

from datetime import datetime

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel


Builder.load_string(
    """
<AddTransactionScreen>:
    name: "add_transaction"

    MDBoxLayout:
        orientation: "vertical"
        padding: "16dp"
        spacing: "12dp"

        MDBoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: "48dp"

            MDLabel:
                text: root.title
                font_style: "H6"
                halign: "left"

            MDRaisedButton:
                text: "← Volver"
                size_hint_x: None
                width: "100dp"
                on_release: root.manager.current = 'transactions'

        MDTextField:
            id: amount
            hint_text: "Monto"
            input_filter: "float"
            mode: "rectangle"

        MDTextField:
            id: type
            hint_text: "Tipo (ingreso/gasto/transferencia)"
            mode: "rectangle"

        MDTextField:
            id: category
            hint_text: "Categoría (ID)"
            input_filter: "int"
            mode: "rectangle"

        MDTextField:
            id: account
            hint_text: "Cuenta (UUID)"
            mode: "rectangle"

        MDTextField:
            id: note
            hint_text: "Nota"
            mode: "rectangle"

        MDRaisedButton:
            text: "Guardar"
            pos_hint: {"center_x": 0.5}
            on_release: root.on_save()

        MDLabel:
            text: root.status_message
            halign: "center"
            theme_text_color: "Hint"
    """
)


class AddTransactionScreen(Screen):
    """Pantalla de alta de transacciones."""

    title = StringProperty("Nueva transacción")
    status_message = StringProperty("")

    def __init__(self, transaction_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service

    def on_save(self) -> None:
        if not self.transaction_service:
            self.status_message = "TransactionService no configurado"
            return

        try:
            amount = float(self.ids.amount.text)
            type_ = self.ids.type.text.strip()
            category_text = self.ids.category.text.strip()
            account_text = self.ids.account.text.strip()
            session = self.transaction_service.session
            if category_text:
                category_id = int(category_text)
            else:
                from gf_mobile.persistence.models import Category
                category = session.query(Category).first()
                if not category:
                    raise ValueError("No hay categorias disponibles")
                category_id = category.id
            if account_text:
                account_id = account_text
            else:
                from gf_mobile.persistence.models import Account
                account = session.query(Account).first()
                if not account:
                    raise ValueError("No hay cuentas disponibles")
                account_id = account.id
            note = self.ids.note.text.strip() or None

            self.transaction_service.create(
                account_id=account_id,
                type_=type_,
                amount=amount,
                category_id=category_id,
                note=note,
                occurred_at=datetime.utcnow(),
            )
            self.status_message = "Transacción guardada"
        except Exception as e:
            self.status_message = f"Error: {e}"

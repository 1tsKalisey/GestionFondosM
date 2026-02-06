"""
CategoriesScreen - Gestión completa de categorías de gastos
Permite crear, editar y organizar categorías por grupo presupuestario
"""

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
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard


Builder.load_string(
    """
<CategoriesScreen>:
    name: "categories"

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
                text: "Categorías"
                font_style: "H6"
                halign: "left"

            MDRaisedButton:
                text: "+ Nueva"
                size_hint_x: None
                width: "100dp"
                on_release: root.on_new_category()

        # Formulario de ingreso
        MDCard:
            orientation: "vertical"
            padding: "16dp"
            spacing: "12dp"
            size_hint_y: None
            height: "240dp"
            elevation: 2

            MDLabel:
                text: "Nueva categoría"
                font_style: "Body2"
                bold: True
                size_hint_y: None
                height: "20dp"

            MDTextField:
                id: cat_name
                hint_text: "Nombre (ej: Comida, Transporte)"
                mode: "rectangle"
                size_hint_y: None
                height: "48dp"

            MDLabel:
                text: "Grupo presupuestario"
                font_style: "Caption"
                theme_text_color: "Hint"
                size_hint_y: None
                height: "16dp"

            MDSpinner:
                id: cat_group
                text: "Seleccionar..."
                values: ("Necesidades", "Ocio/Deseos", "Ahorro/Deuda")
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

        # Categorías por grupo
        MDLabel:
            text: "Categorías por grupo"
            font_style: "Body2"
            bold: True
            size_hint_y: None
            height: "24dp"

        # Lista de categorías
        ScrollView:
            MDList:
                id: categories_list

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
                text: "💰 Presupuestos"
                on_release: root.manager.current = 'budgets'

            MDFlatButton:
                text: "📈 Reportes"
                on_release: root.manager.current = 'reports'
    """
)


class CategoriesScreen(Screen):
    """Pantalla de gestión de categorías."""

    status_message = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.category_service = None
        self.selected_category_id = None

    def on_enter(self):
        """Se llama cuando la pantalla se muestra"""
        self.refresh()

    def refresh(self) -> None:
        """Recarga la lista de categorías"""
        try:
            self.ids.categories_list.clear_widgets()

            if not self.category_service:
                self.status_message = "CategoryService no configurado"
                return

            categories = self.category_service.list_all()
            
            # Organizar por grupo
            groups_order = ["Necesidades", "Ocio/Deseos", "Ahorro/Deuda"]
            categories_by_group = {g: [] for g in groups_order}
            
            for cat in categories:
                group = cat.budget_group
                if group in categories_by_group:
                    categories_by_group[group].append(cat)

            # Mostrar por grupo
            for group in groups_order:
                if categories_by_group[group]:
                    # Etiqueta del grupo
                    group_label = OneLineListItem(
                        text=f"📌 {group}",
                    )
                    self.ids.categories_list.add_widget(group_label)
                    
                    # Categorías del grupo
                    for cat in categories_by_group[group]:
                        item = OneLineListItem(
                            text=f"  • {cat.name}",
                            on_release=lambda x=cat: self.on_select_category(x)
                        )
                        self.ids.categories_list.add_widget(item)

            self.status_message = f"{len(categories)} categorías"

        except Exception as exc:
            self.status_message = f"Error: {str(exc)}"

    def on_new_category(self) -> None:
        """Abre el formulario para nueva categoría"""
        self.ids.cat_name.text = ""
        self.ids.cat_group.text = "Seleccionar..."
        self.selected_category_id = None

    def on_select_category(self, category) -> None:
        """Selecciona una categoría para editar"""
        self.ids.cat_name.text = category.name
        self.ids.cat_group.text = category.budget_group
        self.selected_category_id = category.id

    def on_save(self) -> None:
        """Guarda la categoría (crear o editar)"""
        try:
            if not self.category_service:
                self.status_message = "CategoryService no configurado"
                return

            name = self.ids.cat_name.text.strip()
            group = self.ids.cat_group.text

            if not name:
                self.status_message = "Ingrese el nombre de la categoría"
                return

            if group == "Seleccionar...":
                self.status_message = "Seleccione un grupo presupuestario"
                return

            if self.selected_category_id:
                # Editar categoría existente
                self.category_service.update(
                    self.selected_category_id,
                    name=name,
                    budget_group=group
                )
                self.status_message = f"✓ Categoría '{name}' actualizada"
            else:
                # Crear nueva categoría
                self.category_service.create(
                    name=name,
                    budget_group=group
                )
                self.status_message = f"✓ Categoría '{name}' creada"

            self.on_clear()
            self.refresh()

        except Exception as exc:
            self.status_message = f"Error: {str(exc)}"

    def on_clear(self) -> None:
        """Limpia el formulario"""
        self.ids.cat_name.text = ""
        self.ids.cat_group.text = "Seleccionar..."
        self.selected_category_id = None

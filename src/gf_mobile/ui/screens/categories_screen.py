"""
Categories screen.
"""

from typing import Optional

from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem
from kivymd.uix.textfield import MDTextField

from gf_mobile.services.category_service import CategoryInput
from gf_mobile.ui.dialogs import build_message_dialog, build_selection_dialog
from gf_mobile.ui.navigation import NavigationBar
from gf_mobile.ui.responsive import ResponsiveManager
from gf_mobile.ui.screen_utils import list_panel_height_for_device, resolve_palette
from gf_mobile.ui.widgets.shell import HeroCard, ScreenHeader, SectionCard


Builder.load_string(
    """
<CategoriesScreen>:
    name: "categories"

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
                    eyebrow: "CLASIFICACION"
                    title: "Categorias"
                    subtitle: "Organiza el lenguaje financiero de toda la app"
                    muted_color: app.kivy_palette["text_secondary"]

                HeroCard:
                    eyebrow: "Modelo base"
                    title: "Necesidades, ocio, ahorro"
                    supporting_text: "Usa grupos coherentes para que dashboard, presupuestos y reportes lean bien tus datos."
                    card_color: app.kivy_palette["primary"]
                    title_color: 1, 1, 1, 1
                    eyebrow_color: 0.9, 0.95, 1, 1

                SectionCard:
                    title: "Editar categoria"
                    subtitle: "Crea o actualiza una categoria y su grupo"
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDTextField:
                        id: cat_name
                        hint_text: "Nombre"
                        mode: "rectangle"

                    MDLabel:
                        text: "Grupo"
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        size_hint_y: None
                        height: "18dp"

                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: "8dp" if root.show_custom_group else "0dp"

                        MDRaisedButton:
                            id: cat_group
                            text: "Necesidades"
                            size_hint_y: None
                            height: "40dp"
                            md_bg_color: app.kivy_palette["primary"]
                            on_release: root.open_group_picker()

                        MDBoxLayout:
                            id: custom_group_slot
                            orientation: "vertical"
                            adaptive_height: True

                        MDBoxLayout:
                            size_hint_y: None
                            height: "42dp"
                            spacing: "8dp"

                            MDRaisedButton:
                                text: "Guardar"
                                md_bg_color: app.kivy_palette["primary"]
                                on_release: root.on_save()

                            MDFlatButton:
                                text: "Limpiar"
                                on_release: root.on_clear()

                SectionCard:
                    title: "Catalogo"
                    subtitle: root.status_message
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    ScrollView:
                        do_scroll_x: False
                        size_hint_y: None
                        height: root.catalog_height_dp

                        MDBoxLayout:
                            id: categories_list
                            orientation: "vertical"
                            spacing: "4dp"
                            size_hint_y: None
                            height: self.minimum_height

        NavigationBar:
            id: nav_bar
    """
)


class CategoriesScreen(Screen):
    status_message = StringProperty("")
    show_custom_group = BooleanProperty(False)
    catalog_height_dp = NumericProperty(320)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.category_service = None
        self.selected_category_id = None
        self.custom_group_field = None
        self._dialog: Optional[MDDialog] = None
        self._group_values = ("Necesidades", "Ocio/Deseos", "Ahorro/Deuda", "Otros", "Añadir...")

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "categories"
        self._update_responsive_layout()
        self._sync_group_options()
        self.refresh()

    def _update_responsive_layout(self) -> None:
        self.catalog_height_dp = list_panel_height_for_device(
            is_phone=ResponsiveManager.is_phone(),
            is_tablet=ResponsiveManager.is_tablet(),
            orientation=ResponsiveManager.get_orientation(),
        )

    def refresh(self) -> None:
        try:
            self.ids.categories_list.clear_widgets()
            if not self.category_service:
                self.status_message = "CategoryService no configurado"
                self._show_dialog("Error", self.status_message, is_error=True)
                return

            categories = self.category_service.list_all()
            self._sync_group_options(categories)
            groups_order = ["Necesidades", "Ocio/Deseos", "Ahorro/Deuda"]
            categories_by_group = {g: [] for g in groups_order}

            for cat in categories:
                categories_by_group.setdefault(cat.budget_group, []).append(cat)

            ordered_groups = groups_order + [g for g in categories_by_group.keys() if g not in groups_order]
            for group in ordered_groups:
                if not categories_by_group.get(group):
                    continue
                self.ids.categories_list.add_widget(
                    MDLabel(
                        text=group,
                        bold=True,
                        theme_text_color="Secondary",
                        size_hint_y=None,
                        height=24,
                    )
                )
                for cat in categories_by_group[group]:
                    self.ids.categories_list.add_widget(
                        OneLineListItem(
                            text=cat.name,
                            on_release=lambda _x, c=cat: self.on_select_category(c),
                        )
                    )

            if not categories:
                self._add_placeholder_row("No hay categorias todavia")

            self.status_message = f"{len(categories)} categorias"
        except Exception as exc:
            self.status_message = self._short_error(exc)

    def on_new_category(self) -> None:
        self.ids.cat_name.text = ""
        self.ids.cat_group.text = "Necesidades"
        self._remove_custom_group_field()
        self.show_custom_group = False
        self.selected_category_id = None

    def on_select_category(self, category) -> None:
        self.ids.cat_name.text = category.name
        self._add_group_to_spinner(category.budget_group)
        self.ids.cat_group.text = category.budget_group
        self.show_custom_group = False
        self._remove_custom_group_field()
        self.selected_category_id = category.id

    def on_save(self) -> None:
        try:
            if not self.category_service:
                self.status_message = "CategoryService no configurado"
                self._show_dialog("Error", self.status_message, is_error=True)
                return

            name = self.ids.cat_name.text.strip()
            selected_group = self.ids.cat_group.text.strip()
            custom_group = self._get_custom_group_text()
            group = custom_group if selected_group == "Añadir..." else selected_group

            if not name:
                self.status_message = "Ingrese nombre de categoria"
                self._show_dialog("Error", self.status_message, is_error=True)
                return
            if not group:
                self.status_message = "Ingrese grupo"
                self._show_dialog("Error", self.status_message, is_error=True)
                return

            payload = CategoryInput(name=name, budget_group=group)
            if self.selected_category_id:
                self.category_service.update(self.selected_category_id, payload)
                self.status_message = f"Categoria '{name}' actualizada"
                self._show_dialog("Exito", self.status_message, is_error=False)
            else:
                self.category_service.create(payload)
                self.status_message = f"Categoria '{name}' creada"
                self._show_dialog("Exito", self.status_message, is_error=False)

            self._add_group_to_spinner(group)

            self.on_clear()
            self.refresh()
        except Exception as exc:
            self.status_message = self._short_error(exc)
            self._show_dialog("Error", self.status_message, is_error=True)

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 120:
            message = f"{message[:117]}..."
        return f"Error: {message}"

    def on_clear(self) -> None:
        self.ids.cat_name.text = ""
        self.ids.cat_group.text = "Necesidades"
        self._remove_custom_group_field()
        self.show_custom_group = False
        self.selected_category_id = None

    def on_group_selected(self, value: str) -> None:
        self.ids.cat_group.text = value
        self.show_custom_group = value == "Añadir..."
        if self.show_custom_group:
            self._ensure_custom_group_field()
        else:
            self._remove_custom_group_field()

    def open_group_picker(self) -> None:
        self._open_selection_dialog(
            "Grupo presupuestario",
            list(getattr(self, "_group_values", [])),
            self.on_group_selected,
        )

    def _add_group_to_spinner(self, group: str) -> None:
        if not group:
            return
        values = list(getattr(self, "_group_values", []))
        if group not in values:
            if "Añadir..." in values:
                insert_at = values.index("Añadir...")
                values.insert(insert_at, group)
            else:
                values.append(group)
            self._group_values = tuple(values)

    def _sync_group_options(self, categories=None) -> None:
        base = ["Necesidades", "Ocio/Deseos", "Ahorro/Deuda", "Otros"]
        groups = []
        if categories is None and self.category_service:
            try:
                categories = self.category_service.list_all()
            except Exception:
                categories = []
        if categories:
            groups = sorted(
                {
                    str(c.budget_group).strip()
                    for c in categories
                    if getattr(c, "budget_group", None) and str(c.budget_group).strip()
                }
            )
        merged = []
        for item in base + groups:
            if item not in merged:
                merged.append(item)
        merged.append("Añadir...")
        self._group_values = tuple(merged)

    def _ensure_custom_group_field(self) -> None:
        if self.custom_group_field is not None:
            return
        field = MDTextField(
            hint_text="Nuevo grupo",
            mode="rectangle",
            size_hint_y=None,
            height="46dp",
        )
        self.ids.custom_group_slot.add_widget(field)
        self.custom_group_field = field

    def _remove_custom_group_field(self) -> None:
        if self.custom_group_field is None:
            return
        try:
            self.ids.custom_group_slot.remove_widget(self.custom_group_field)
        except Exception:
            pass
        self.custom_group_field = None

    def _get_custom_group_text(self) -> str:
        if self.custom_group_field is None:
            return ""
        return self.custom_group_field.text.strip()

    def _add_placeholder_row(self, text: str) -> None:
        self.ids.categories_list.add_widget(
            MDLabel(
                text=text,
                theme_text_color="Hint",
                size_hint_y=None,
                height=24,
            )
        )

    def _show_dialog(self, title: str, message: str, is_error: bool) -> None:
        palette = resolve_palette()
        button_color = palette["error"] if is_error else palette["primary"]
        self._dialog = build_message_dialog(
            self._dialog,
            title=title,
            message=message,
            button_color=button_color,
        )
        self._dialog.open()

    def _open_selection_dialog(self, title: str, options, callback) -> None:
        self._dialog = build_selection_dialog(
            self._dialog,
            title=title,
            options=options,
            on_select=callback,
        )
        self._dialog.open()

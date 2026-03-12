"""
Reusable shell and content widgets for the mobile UI.
"""

from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard


Builder.load_string(
    """
<ScreenHeader>:
    orientation: "vertical"
    adaptive_height: True
    spacing: "4dp"
    padding: "0dp", "4dp", "0dp", "2dp"

    MDLabel:
        text: root.eyebrow
        adaptive_height: True
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: root.muted_color
        opacity: 1 if root.eyebrow else 0

    MDBoxLayout:
        adaptive_height: True
        spacing: "12dp"

        MDBoxLayout:
            orientation: "vertical"
            adaptive_height: True
            spacing: "2dp"

            MDLabel:
                text: root.title
                adaptive_height: True
                bold: True
                font_style: "H5"

            MDLabel:
                text: root.subtitle
                adaptive_height: True
                theme_text_color: "Custom"
                text_color: root.muted_color
                opacity: 1 if root.subtitle else 0

        Widget:

<HeroCard>:
    orientation: "vertical"
    adaptive_height: True
    padding: "18dp"
    spacing: "12dp"
    radius: [24, 24, 24, 24]
    elevation: 0
    md_bg_color: root.card_color

    MDLabel:
        text: root.eyebrow
        adaptive_height: True
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: root.eyebrow_color

    MDLabel:
        text: root.title
        adaptive_height: True
        bold: True
        font_style: "H5"
        theme_text_color: "Custom"
        text_color: root.title_color

    MDLabel:
        text: root.supporting_text
        adaptive_height: True
        theme_text_color: "Custom"
        text_color: root.title_color
        opacity: 0.88

<MetricCard>:
    orientation: "vertical"
    padding: "14dp"
    spacing: "6dp"
    size_hint_y: None
    height: "128dp"
    radius: [20, 20, 20, 20]
    elevation: 0
    md_bg_color: root.card_color

    MDLabel:
        text: root.label
        adaptive_height: True
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: root.muted_color

    MDLabel:
        text: root.value
        adaptive_height: True
        bold: True
        font_style: "H6"
        theme_text_color: "Custom"
        text_color: root.value_color

    Widget:

    MDLabel:
        text: root.helper
        adaptive_height: True
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: root.muted_color

<SectionCard>:
    orientation: "vertical"
    adaptive_height: True
    padding: "14dp"
    spacing: "10dp"
    radius: [22, 22, 22, 22]
    elevation: 0
    md_bg_color: root.card_color

    MDBoxLayout:
        adaptive_height: True
        spacing: "10dp"

        MDBoxLayout:
            orientation: "vertical"
            adaptive_height: True
            spacing: "2dp"

            MDLabel:
                text: root.title
                adaptive_height: True
                bold: True
                font_style: "Body1"
                theme_text_color: "Custom"
                text_color: root.title_color

            MDLabel:
                text: root.subtitle
                adaptive_height: True
                font_style: "Caption"
                theme_text_color: "Custom"
                text_color: root.muted_color
                opacity: 1 if root.subtitle else 0

        Widget:

<EmptyStateCard>:
    orientation: "vertical"
    adaptive_height: True
    padding: "18dp"
    spacing: "10dp"
    radius: [20, 20, 20, 20]
    elevation: 0
    md_bg_color: root.card_color

    MDLabel:
        text: root.title
        adaptive_height: True
        halign: "center"
        bold: True

    MDLabel:
        text: root.message
        adaptive_height: True
        halign: "center"
        theme_text_color: "Custom"
        text_color: root.muted_color
"""
)


class ScreenHeader(MDBoxLayout):
    title = StringProperty("")
    subtitle = StringProperty("")
    eyebrow = StringProperty("")
    muted_color = ListProperty([0.45, 0.45, 0.45, 1])


class HeroCard(MDCard):
    eyebrow = StringProperty("")
    title = StringProperty("")
    supporting_text = StringProperty("")
    card_color = ListProperty([0.12, 0.35, 0.65, 1])
    title_color = ListProperty([1, 1, 1, 1])
    eyebrow_color = ListProperty([0.85, 0.92, 1, 1])


class MetricCard(MDCard):
    label = StringProperty("")
    value = StringProperty("")
    helper = StringProperty("")
    card_color = ListProperty([1, 1, 1, 1])
    value_color = ListProperty([0.1, 0.1, 0.1, 1])
    muted_color = ListProperty([0.45, 0.45, 0.45, 1])


class SectionCard(MDCard):
    title = StringProperty("")
    subtitle = StringProperty("")
    card_color = ListProperty([1, 1, 1, 1])
    title_color = ListProperty([0.1, 0.1, 0.1, 1])
    muted_color = ListProperty([0.45, 0.45, 0.45, 1])


class EmptyStateCard(MDCard):
    title = StringProperty("")
    message = StringProperty("")
    card_color = ListProperty([1, 1, 1, 1])
    muted_color = ListProperty([0.45, 0.45, 0.45, 1])

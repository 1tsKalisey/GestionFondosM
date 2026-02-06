"""
Tests para Theme y Responsive managers - Slice 11
"""

import pytest
from gf_mobile.ui.theme import ThemeManager, ThemeName, ThemeColors, get_colors, is_dark_mode
from gf_mobile.ui.responsive import ResponsiveManager, DeviceType


class TestThemeManager:
    """Tests para ThemeManager"""
    
    def test_init_default_light_theme(self):
        """Inicialización con tema light por defecto"""
        manager = ThemeManager()
        assert manager.current_theme == ThemeName.LIGHT
        assert not manager.is_dark_mode()
    
    def test_set_theme_light(self):
        """Cambiar a tema light"""
        manager = ThemeManager()
        result = manager.set_theme("light")
        assert result is True
        assert manager.current_theme == ThemeName.LIGHT
    
    def test_set_theme_dark(self):
        """Cambiar a tema dark"""
        manager = ThemeManager()
        result = manager.set_theme("dark")
        assert result is True
        assert manager.current_theme == ThemeName.DARK
        assert manager.is_dark_mode()
    
    def test_set_theme_invalid(self):
        """Error al cambiar a tema inválido"""
        manager = ThemeManager()
        result = manager.set_theme("invalid_theme")
        assert result is False
    
    def test_toggle_dark_mode_light_to_dark(self):
        """Alternar de light a dark"""
        manager = ThemeManager()
        result = manager.toggle_dark_mode()
        assert result is True  # Ahora es dark
        assert manager.is_dark_mode()
    
    def test_toggle_dark_mode_dark_to_light(self):
        """Alternar de dark a light"""
        manager = ThemeManager()
        manager.set_theme("dark")
        result = manager.toggle_dark_mode()
        assert result is False  # Ahora es light
        assert not manager.is_dark_mode()
    
    def test_get_color_primary(self):
        """Obtener color primario"""
        manager = ThemeManager()
        color = manager.get_color("primary")
        assert color == "#2196F3"  # Light theme primary
    
    def test_get_color_dark_theme(self):
        """Obtener color con tema dark"""
        manager = ThemeManager()
        manager.set_theme("dark")
        primary = manager.get_color("primary")
        assert primary == "#1976D2"  # Dark theme primary
    
    def test_get_color_nonexistent(self):
        """Obtener color que no existe"""
        manager = ThemeManager()
        color = manager.get_color("nonexistent")
        assert color == ""
    
    def test_colors_property_light(self):
        """Verificar propiedad colors con light theme"""
        manager = ThemeManager()
        colors = manager.colors
        assert colors.primary == "#2196F3"
        assert colors.accent == "#FF5722"
        assert colors.background == "#FFFFFF"
    
    def test_colors_property_dark(self):
        """Verificar propiedad colors con dark theme"""
        manager = ThemeManager()
        manager.set_theme("dark")
        colors = manager.colors
        assert colors.background == "#121212"
        assert colors.text_primary == "#FFFFFF"
    
    def test_serialize_light_theme(self):
        """Serializar light theme"""
        manager = ThemeManager()
        serialized = manager.serialize()
        assert '"theme": "light"' in serialized
        assert '"primary": "#2196F3"' in serialized
    
    def test_serialize_dark_theme(self):
        """Serializar dark theme"""
        manager = ThemeManager()
        manager.set_theme("dark")
        serialized = manager.serialize()
        assert '"theme": "dark"' in serialized
    
    def test_deserialize_light_theme(self):
        """Deserializar light theme"""
        manager = ThemeManager()
        manager.set_theme("dark")
        
        # Serializar light
        light_manager = ThemeManager()
        json_str = light_manager.serialize()
        
        # Deserializar
        restored = ThemeManager.deserialize(json_str)
        assert restored.current_theme == ThemeName.LIGHT
    
    def test_deserialize_invalid_json(self):
        """Deserializar JSON inválido"""
        restored = ThemeManager.deserialize("invalid json")
        # Debería retornar manager con defaults
        assert restored.current_theme == ThemeName.LIGHT
    
    def test_to_dict(self):
        """Convertir a diccionario"""
        manager = ThemeManager()
        manager.set_theme("dark")
        data = manager.to_dict()
        
        assert data["theme"] == "dark"
        assert isinstance(data["colors"], dict)
        assert data["colors"]["primary"] == "#1976D2"


class TestResponsiveManager:
    """Tests para ResponsiveManager"""
    
    def test_spacing_phone(self):
        """Obtener espaciado para teléfono"""
        spacing = ResponsiveManager.SPACING[DeviceType.PHONE]
        assert spacing["xs"] == 4
        assert spacing["md"] == 16
        assert spacing["xl"] == 32
    
    def test_spacing_tablet(self):
        """Obtener espaciado para tablet"""
        spacing = ResponsiveManager.SPACING[DeviceType.TABLET]
        assert spacing["xs"] == 6
        assert spacing["md"] == 20
        assert spacing["xl"] == 36
    
    def test_font_sizes_phone(self):
        """Obtener tamaños de fuente para teléfono"""
        sizes = ResponsiveManager.FONT_SIZES[DeviceType.PHONE]
        assert sizes["body"] == "14sp"
        assert sizes["headline"] == "20sp"
        assert sizes["title"] == "24sp"
    
    def test_font_sizes_tablet(self):
        """Obtener tamaños de fuente para tablet"""
        sizes = ResponsiveManager.FONT_SIZES[DeviceType.TABLET]
        assert sizes["body"] == "16sp"
        assert sizes["headline"] == "22sp"
    
    def test_is_phone_method(self):
        """Método is_phone()"""
        # Depende del tamaño actual de ventana, pero debería retornar bool
        result = ResponsiveManager.is_phone()
        assert isinstance(result, bool)
    
    def test_is_tablet_method(self):
        """Método is_tablet()"""
        result = ResponsiveManager.is_tablet()
        assert isinstance(result, bool)
    
    def test_get_padding_returns_tuple(self):
        """get_padding retorna tupla"""
        padding = ResponsiveManager.get_padding()
        assert isinstance(padding, tuple)
        assert len(padding) == 2
        assert all(isinstance(x, int) for x in padding)
    
    def test_get_margin_returns_tuple(self):
        """get_margin retorna tupla"""
        margin = ResponsiveManager.get_margin()
        assert isinstance(margin, tuple)
        assert len(margin) == 2
    
    def test_get_grid_columns_positive(self):
        """get_grid_columns retorna valor positivo"""
        columns = ResponsiveManager.get_grid_columns()
        assert isinstance(columns, int)
        assert columns > 0
    
    def test_get_item_height_positive(self):
        """get_item_height retorna valor positivo"""
        height = ResponsiveManager.get_item_height()
        assert isinstance(height, int)
        assert height > 0
    
    def test_get_button_height_positive(self):
        """get_button_height retorna valor positivo"""
        height = ResponsiveManager.get_button_height()
        assert isinstance(height, int)
        assert height > 0
    
    def test_get_font_size_valid_styles(self):
        """get_font_size con estilos válidos"""
        for style in ["caption", "body", "subheading", "headline", "title"]:
            size = ResponsiveManager.get_font_size(style)
            assert isinstance(size, str)
            assert "sp" in size
    
    def test_get_font_size_invalid_style(self):
        """get_font_size con estilo inválido retorna default"""
        size = ResponsiveManager.get_font_size("invalid")
        assert size == "14sp"
    
    def test_should_show_sidebar_phone(self):
        """Sidebar debería ocultarse en teléfono"""
        # Simular tamaño de teléfono
        # Nota: Esto depende del tamaño actual de Window
        result = ResponsiveManager.should_show_sidebar()
        assert isinstance(result, bool)
    
    def test_get_orientation_returns_string(self):
        """get_orientation retorna string válido"""
        orientation = ResponsiveManager.get_orientation()
        assert orientation in ["landscape", "portrait"]
    
    def test_breakpoints_constants(self):
        """Verificar que breakpoints sean correctos"""
        assert ResponsiveManager.PHONE_MAX == 600
        assert ResponsiveManager.TABLET_MIN == 600
        assert ResponsiveManager.TABLET_MAX == 1200
        assert ResponsiveManager.DESKTOP_MIN == 1200


class TestHelperFunctions:
    """Tests para funciones helper"""
    
    def test_get_spacing_helper(self):
        """Helper get_spacing funciona"""
        from gf_mobile.ui.responsive import get_spacing
        spacing = get_spacing("md")
        assert isinstance(spacing, int)
        assert spacing > 0
    
    def test_get_padding_helper(self):
        """Helper get_padding funciona"""
        from gf_mobile.ui.responsive import get_padding
        padding = get_padding()
        assert isinstance(padding, tuple)
    
    def test_is_phone_helper(self):
        """Helper is_phone funciona"""
        from gf_mobile.ui.responsive import is_phone
        result = is_phone()
        assert isinstance(result, bool)
    
    def test_is_tablet_helper(self):
        """Helper is_tablet funciona"""
        from gf_mobile.ui.responsive import is_tablet
        result = is_tablet()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

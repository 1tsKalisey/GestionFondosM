"""
Theme Manager para GestionFondosM
Maneja temas claro/oscuro y personalización de colores
"""

from enum import Enum
from typing import Dict, Tuple
from dataclasses import dataclass
import json


class ThemeName(Enum):
    """Nombre de temas disponibles"""
    LIGHT = "light"
    DARK = "dark"


@dataclass
class ThemeColors:
    """Colores para un tema específico"""
    primary: str          # Color principal (botones, headers)
    accent: str          # Color de acento (highlights)
    background: str      # Fondo principal
    surface: str         # Fondo secundario (cards, surfaces)
    text_primary: str    # Texto principal
    text_secondary: str  # Texto secundario
    success: str         # Color de éxito (verde)
    warning: str         # Color de advertencia (amarillo)
    error: str           # Color de error (rojo)
    
    def to_dict(self) -> Dict[str, str]:
        """Convertir a diccionario"""
        return {
            "primary": self.primary,
            "accent": self.accent,
            "background": self.background,
            "surface": self.surface,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
        }

    def to_rgba_dict(self) -> Dict[str, Tuple[float, float, float, float]]:
        return {
            "primary": hex_to_rgba(self.primary),
            "accent": hex_to_rgba(self.accent),
            "background": hex_to_rgba(self.background),
            "surface": hex_to_rgba(self.surface),
            "text_primary": hex_to_rgba(self.text_primary),
            "text_secondary": hex_to_rgba(self.text_secondary),
            "success": hex_to_rgba(self.success),
            "warning": hex_to_rgba(self.warning),
            "error": hex_to_rgba(self.error),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ThemeColors":
        """Crear desde diccionario"""
        return cls(**data)


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> Tuple[float, float, float, float]:
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Color hex invalido: {hex_color}")
    r = int(value[0:2], 16) / 255.0
    g = int(value[2:4], 16) / 255.0
    b = int(value[4:6], 16) / 255.0
    return (r, g, b, alpha)


class ThemeManager:
    """
    Gestor central de temas para la aplicación
    Maneja aplicación y persistencia de temas
    """
    
    # Definiciones de temas
    LIGHT_THEME = ThemeColors(
        primary="#2196F3",
        accent="#FF5722",
        background="#FFFFFF",
        surface="#F5F5F5",
        text_primary="#212121",
        text_secondary="#757575",
        success="#4CAF50",
        warning="#FFC107",
        error="#F44336",
    )
    
    DARK_THEME = ThemeColors(
        primary="#1976D2",
        accent="#FFB74D",
        background="#121212",
        surface="#1E1E1E",
        text_primary="#FFFFFF",
        text_secondary="#B0B0B0",
        success="#66BB6A",
        warning="#FFD54F",
        error="#EF5350",
    )
    
    # Temas disponibles
    THEMES = {
        ThemeName.LIGHT.value: LIGHT_THEME,
        ThemeName.DARK.value: DARK_THEME,
    }
    
    def __init__(self):
        """Inicializar con tema por defecto (light)"""
        self._current_theme = ThemeName.LIGHT
        self._theme_colors = self.LIGHT_THEME
    
    @property
    def current_theme(self) -> ThemeName:
        """Retorna tema actual"""
        return self._current_theme
    
    @property
    def colors(self) -> ThemeColors:
        """Retorna colores del tema actual"""
        return self._theme_colors
    
    def set_theme(self, theme_name: str) -> bool:
        """
        Cambiar tema
        
        Args:
            theme_name: Nombre del tema ("light" o "dark")
        
        Returns:
            True si fue exitoso, False si tema no existe
        """
        if theme_name not in self.THEMES:
            return False
        
        self._current_theme = ThemeName(theme_name)
        self._theme_colors = self.THEMES[theme_name]
        return True

    def apply_overrides(self, overrides: Dict[str, str]) -> None:
        base = self.THEMES[self._current_theme.value]
        data = base.to_dict()
        for key, value in (overrides or {}).items():
            if key in data and value:
                data[key] = value
        self._theme_colors = ThemeColors.from_dict(data)
    
    def toggle_dark_mode(self) -> bool:
        """
        Alternar entre modo oscuro y claro
        
        Returns:
            True si ahora está en modo oscuro
        """
        new_theme = (
            ThemeName.DARK
            if self._current_theme == ThemeName.LIGHT
            else ThemeName.LIGHT
        )
        self.set_theme(new_theme.value)
        return self._current_theme == ThemeName.DARK
    
    def is_dark_mode(self) -> bool:
        """Retorna True si está en modo oscuro"""
        return self._current_theme == ThemeName.DARK
    
    def get_color(self, color_key: str) -> str:
        """
        Obtener color específico del tema actual
        
        Args:
            color_key: Clave del color (e.g., "primary", "error")
        
        Returns:
            Código hex del color, o "" si no existe
        """
        return getattr(self._theme_colors, color_key, "")
    
    def serialize(self) -> str:
        """Serializar tema actual para persistencia"""
        return json.dumps({
            "theme": self._current_theme.value,
            "colors": self._theme_colors.to_dict(),
        })
    
    @classmethod
    def deserialize(cls, json_str: str) -> "ThemeManager":
        """Deserializar tema desde JSON"""
        try:
            data = json.loads(json_str)
            manager = cls()
            manager.set_theme(data["theme"])
            return manager
        except (json.JSONDecodeError, KeyError, ValueError):
            # Si falla, retornar con tema por defecto
            return cls()
    
    def to_dict(self) -> Dict:
        """Convertir a diccionario para almacenar"""
        return {
            "theme": self._current_theme.value,
            "colors": self._theme_colors.to_dict(),
        }


# Instancia global del tema manager
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Obtener instancia global del tema manager"""
    return _theme_manager


def get_colors() -> ThemeColors:
    """Helper rápido para obtener colores actuales"""
    return _theme_manager.colors


def set_app_theme(theme_name: str) -> bool:
    """Helper rápido para cambiar tema"""
    return _theme_manager.set_theme(theme_name)


def is_dark_mode() -> bool:
    """Helper rápido para verificar modo oscuro"""
    return _theme_manager.is_dark_mode()


def get_kivy_palette() -> Dict[str, Tuple[float, float, float, float]]:
    """Helper rápido para obtener colores actuales en RGBA para Kivy."""
    return _theme_manager.colors.to_rgba_dict()

"""
Responsive Layout Manager para GestionFondosM
Maneja layouts adaptativos para diferentes tamaños de pantalla
"""

from enum import Enum
from typing import Tuple
from kivy.core.window import Window


class DeviceType(Enum):
    """Tipos de dispositivos"""
    PHONE = "phone"
    TABLET = "tablet"
    DESKTOP = "desktop"


class ResponsiveManager:
    """
    Gestor de layouts responsive
    Proporciona valores adaptativos basado en tamaño de pantalla
    """
    
    # Breakpoints (ancho de pantalla en dp)
    PHONE_MAX = 600
    TABLET_MIN = 600
    TABLET_MAX = 1200
    DESKTOP_MIN = 1200
    
    # Espaciados adaptativos
    SPACING = {
        DeviceType.PHONE: {
            "xs": 4,      # Extra small
            "sm": 8,      # Small
            "md": 16,     # Medium (default padding)
            "lg": 24,     # Large
            "xl": 32,     # Extra large
        },
        DeviceType.TABLET: {
            "xs": 6,
            "sm": 12,
            "md": 20,
            "lg": 28,
            "xl": 36,
        },
        DeviceType.DESKTOP: {
            "xs": 8,
            "sm": 16,
            "md": 24,
            "lg": 32,
            "xl": 40,
        },
    }
    
    # Tamaños de fuente adaptativos
    FONT_SIZES = {
        DeviceType.PHONE: {
            "caption": "10sp",      # Subtítulos muy pequeños
            "body": "14sp",         # Texto normal
            "subheading": "16sp",   # Subtítulo
            "headline": "20sp",     # Encabezado
            "title": "24sp",        # Título grande
        },
        DeviceType.TABLET: {
            "caption": "12sp",
            "body": "16sp",
            "subheading": "18sp",
            "headline": "22sp",
            "title": "26sp",
        },
        DeviceType.DESKTOP: {
            "caption": "12sp",
            "body": "16sp",
            "subheading": "18sp",
            "headline": "24sp",
            "title": "28sp",
        },
    }
    
    @classmethod
    def get_device_type(cls) -> DeviceType:
        """
        Determinar tipo de dispositivo basado en tamaño de pantalla
        
        Returns:
            DeviceType del dispositivo actual
        """
        if Window.size[0] < cls.PHONE_MAX:
            return DeviceType.PHONE
        elif Window.size[0] < cls.TABLET_MAX:
            return DeviceType.TABLET
        else:
            return DeviceType.DESKTOP
    
    @classmethod
    def is_phone(cls) -> bool:
        """Verificar si es dispositivo móvil"""
        return cls.get_device_type() == DeviceType.PHONE
    
    @classmethod
    def is_tablet(cls) -> bool:
        """Verificar si es tablet"""
        return cls.get_device_type() == DeviceType.TABLET
    
    @classmethod
    def is_desktop(cls) -> bool:
        """Verificar si es desktop"""
        return cls.get_device_type() == DeviceType.DESKTOP
    
    @classmethod
    def get_spacing(cls, size: str) -> int:
        """
        Obtener valor de espaciado adaptativo
        
        Args:
            size: Tamaño del espaciado ("xs", "sm", "md", "lg", "xl")
        
        Returns:
            Valor de espaciado en dp
        """
        device = cls.get_device_type()
        return cls.SPACING[device].get(size, 16)
    
    @classmethod
    def get_padding(cls) -> Tuple[int, int]:
        """
        Obtener padding adaptativo (horizontal, vertical)
        
        Returns:
            Tupla con padding (horizontal, vertical)
        """
        device = cls.get_device_type()
        md_spacing = cls.SPACING[device]["md"]
        
        if device == DeviceType.PHONE:
            return (md_spacing, md_spacing)
        elif device == DeviceType.TABLET:
            return (md_spacing + 4, md_spacing)
        else:
            return (md_spacing + 8, md_spacing)
    
    @classmethod
    def get_margin(cls) -> Tuple[int, int]:
        """
        Obtener margin adaptativo (horizontal, vertical)
        
        Returns:
            Tupla con margin (horizontal, vertical)
        """
        device = cls.get_device_type()
        lg_spacing = cls.SPACING[device]["lg"]
        md_spacing = cls.SPACING[device]["md"]
        return (lg_spacing, md_spacing)
    
    @classmethod
    def get_grid_columns(cls) -> int:
        """
        Obtener número de columnas para grillas
        
        Returns:
            Número de columnas recomendadas
        """
        device = cls.get_device_type()
        
        if device == DeviceType.PHONE:
            return 2
        elif device == DeviceType.TABLET:
            return 3
        else:
            return 4
    
    @classmethod
    def get_item_height(cls) -> int:
        """
        Obtener altura adaptativa para items de lista
        
        Returns:
            Altura en dp
        """
        device = cls.get_device_type()
        
        if device == DeviceType.PHONE:
            return 56
        elif device == DeviceType.TABLET:
            return 64
        else:
            return 72
    
    @classmethod
    def get_button_height(cls) -> int:
        """
        Obtener altura adaptativa para botones
        
        Returns:
            Altura en dp
        """
        device = cls.get_device_type()
        
        if device == DeviceType.PHONE:
            return 48
        elif device == DeviceType.TABLET:
            return 52
        else:
            return 56
    
    @classmethod
    def get_font_size(cls, style: str) -> str:
        """
        Obtener tamaño de fuente adaptativo
        
        Args:
            style: Estilo de fuente ("caption", "body", "subheading", "headline", "title")
        
        Returns:
            Tamaño de fuente en formato Kivy (e.g., "14sp")
        """
        device = cls.get_device_type()
        return cls.FONT_SIZES[device].get(style, "14sp")
    
    @classmethod
    def get_max_width(cls) -> int:
        """
        Obtener ancho máximo recomendado para contenido
        Útil para layouts en dispositivos grandes
        
        Returns:
            Ancho máximo en dp
        """
        device = cls.get_device_type()
        
        if device == DeviceType.PHONE:
            return int(Window.width)  # Usar ancho completo
        elif device == DeviceType.TABLET:
            return 800
        else:
            return 1200
    
    @classmethod
    def get_card_width(cls) -> int:
        """
        Obtener ancho adaptativo para cards
        
        Returns:
            Ancho en dp
        """
        device = cls.get_device_type()
        
        if device == DeviceType.PHONE:
            return int(Window.width) - 32
        elif device == DeviceType.TABLET:
            return 350
        else:
            return 400
    
    @classmethod
    def get_dialog_width(cls) -> float:
        """
        Obtener ancho adaptativo para diálogos
        Retorna como porcentaje del ancho de pantalla
        
        Returns:
            Ancho como fracción (0.0 a 1.0)
        """
        device = cls.get_device_type()
        
        if device == DeviceType.PHONE:
            return 0.9  # 90% del ancho
        elif device == DeviceType.TABLET:
            return 0.7  # 70% del ancho
        else:
            return 0.5  # 50% del ancho
    
    @classmethod
    def should_show_sidebar(cls) -> bool:
        """
        Determinar si mostrar sidebar/navigation drawer
        
        Returns:
            True si debe mostrarse (tablet o desktop)
        """
        device = cls.get_device_type()
        return device != DeviceType.PHONE
    
    @classmethod
    def get_orientation(cls) -> str:
        """
        Obtener orientación actual
        
        Returns:
            "landscape" o "portrait"
        """
        width, height = Window.size
        return "landscape" if width > height else "portrait"


# Helpers rápidos
def get_spacing(size: str = "md") -> int:
    """Helper rápido para obtener espaciado"""
    return ResponsiveManager.get_spacing(size)


def get_padding() -> Tuple[int, int]:
    """Helper rápido para obtener padding"""
    return ResponsiveManager.get_padding()


def is_phone() -> bool:
    """Helper rápido para verificar si es teléfono"""
    return ResponsiveManager.is_phone()


def is_tablet() -> bool:
    """Helper rápido para verificar si es tablet"""
    return ResponsiveManager.is_tablet()


def get_font_size(style: str = "body") -> str:
    """Helper rápido para obtener tamaño de fuente"""
    return ResponsiveManager.get_font_size(style)

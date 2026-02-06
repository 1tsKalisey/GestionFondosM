"""
Gesture handlers para interacciones táctiles - Slice 11
Soporte para swipe, long-press y otras gestures
"""

import time
from dataclasses import dataclass
from typing import Callable, Optional
from kivy.core.window import Window
from kivy.input.motionevent import MotionEvent


@dataclass
class SwipeGesture:
    """Información de gesto swipe"""
    direction: str  # "left", "right", "up", "down"
    velocity: float  # píxeles por segundo
    distance: float  # píxeles recorridos
    duration: float  # segundos


@dataclass
class LongPressGesture:
    """Información de long-press"""
    duration: float  # segundos de presión
    x: float  # Posición X
    y: float  # Posición Y


class SwipeDetector:
    """Detector de gestos swipe con umbrales configurable"""
    
    # Configuración por defecto
    DEFAULT_MIN_DISTANCE = 100  # píxeles mínimos
    DEFAULT_MIN_VELOCITY = 300  # píxeles/seg mínimos
    DEFAULT_MAX_TIME = 1000  # milisegundos máximos
    
    def __init__(self, 
                 on_swipe: Optional[Callable[[SwipeGesture], None]] = None,
                 min_distance: int = DEFAULT_MIN_DISTANCE,
                 min_velocity: int = DEFAULT_MIN_VELOCITY,
                 max_time: int = DEFAULT_MAX_TIME):
        """
        Inicializar detector de swipe
        
        Args:
            on_swipe: Callback cuando se detecta swipe
            min_distance: Distancia mínima en píxeles
            min_velocity: Velocidad mínima en píxeles/segundo
            max_time: Tiempo máximo en milisegundos
        """
        self.on_swipe = on_swipe
        self.min_distance = min_distance
        self.min_velocity = min_velocity
        self.max_time = max_time
        
        # Estado del toque actual
        self.touch_start_x = 0
        self.touch_start_y = 0
        self.touch_start_time = 0
        self.touching = False
        
    def on_touch_down(self, touch: MotionEvent) -> bool:
        """Maneja inicio de toque"""
        self.touch_start_x = touch.x
        self.touch_start_y = touch.y
        self.touch_start_time = time.time()
        self.touching = True
        return False  # Permitir que otros handlers lo procesen
    
    def on_touch_up(self, touch: MotionEvent) -> bool:
        """Maneja fin de toque y detecta swipe"""
        if not self.touching:
            return False
        
        self.touching = False
        
        # Calcular distancias y tiempo
        dx = touch.x - self.touch_start_x
        dy = touch.y - self.touch_start_y
        dt = time.time() - self.touch_start_time
        
        # Validar tiempo
        if dt > (self.max_time / 1000.0):
            return False
        
        # Determinar dirección dominante
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        
        if abs_dx > abs_dy:
            # Swipe horizontal
            distance = abs_dx
            direction = "right" if dx > 0 else "left"
        else:
            # Swipe vertical (en Kivy, Y=0 es abajo)
            distance = abs_dy
            direction = "up" if dy > 0 else "down"
        
        # Validar distancia mínima
        if distance < self.min_distance:
            return False
        
        # Calcular velocidad
        velocity = distance / dt if dt > 0 else 0
        
        # Validar velocidad mínima
        if velocity < self.min_velocity:
            return False
        
        # Crear gesture y llamar callback
        gesture = SwipeGesture(
            direction=direction,
            velocity=velocity,
            distance=distance,
            duration=dt
        )
        
        if self.on_swipe:
            self.on_swipe(gesture)
        
        return True


class LongPressDetector:
    """Detector de gestos long-press"""
    
    DEFAULT_DURATION = 0.5  # segundos
    
    def __init__(self,
                 on_long_press: Optional[Callable[[LongPressGesture], None]] = None,
                 duration: float = DEFAULT_DURATION):
        """
        Inicializar detector de long-press
        
        Args:
            on_long_press: Callback cuando se detecta long-press
            duration: Duración mínima en segundos
        """
        self.on_long_press = on_long_press
        self.duration = duration
        
        # Estado del toque actual
        self.touch_start_time = None
        self.touch_start_x = 0
        self.touch_start_y = 0
        self.touching = False
        self.long_press_detected = False
        
        # Para scheduler
        self.scheduled_event = None
    
    def on_touch_down(self, touch: MotionEvent) -> bool:
        """Maneja inicio de toque"""
        self.touch_start_x = touch.x
        self.touch_start_y = touch.y
        self.touch_start_time = time.time()
        self.touching = True
        self.long_press_detected = False
        
        # Programar verificación de long-press
        from kivy.clock import Clock
        self.scheduled_event = Clock.schedule_once(
            lambda dt: self._check_long_press(touch),
            self.duration
        )
        return False
    
    def on_touch_move(self, touch: MotionEvent) -> bool:
        """Maneja movimiento de toque"""
        if not self.touching:
            return False
        
        # Si se movió demasiado, cancelar long-press
        dx = abs(touch.x - self.touch_start_x)
        dy = abs(touch.y - self.touch_start_y)
        
        if dx > 10 or dy > 10:  # 10px de tolerancia
            self._cancel()
        
        return False
    
    def on_touch_up(self, touch: MotionEvent) -> bool:
        """Maneja fin de toque"""
        if not self.touching:
            return False
        
        self.touching = False
        self._cancel()
        return False
    
    def _check_long_press(self, touch: MotionEvent) -> None:
        """Verifica si se cumple long-press"""
        if not self.touching:
            return
        
        self.long_press_detected = True
        duration = time.time() - self.touch_start_time
        
        gesture = LongPressGesture(
            duration=duration,
            x=touch.x,
            y=touch.y
        )
        
        if self.on_long_press:
            self.on_long_press(gesture)
    
    def _cancel(self) -> None:
        """Cancela detección de long-press"""
        if self.scheduled_event:
            from kivy.clock import Clock
            Clock.unschedule(self.scheduled_event)
            self.scheduled_event = None


class GestureManager:
    """Gestor centralizado de gestos"""
    
    def __init__(self):
        """Inicializar gestor de gestos"""
        self.swipe_detector = SwipeDetector()
        self.long_press_detector = LongPressDetector()
        self.enabled = True
    
    def set_swipe_callback(self, callback: Callable[[SwipeGesture], None]) -> None:
        """Configurar callback para swipe"""
        self.swipe_detector.on_swipe = callback
    
    def set_long_press_callback(self, callback: Callable[[LongPressGesture], None]) -> None:
        """Configurar callback para long-press"""
        self.long_press_detector.on_long_press = callback
    
    def on_touch_down(self, touch: MotionEvent) -> bool:
        """Delegación de touch down"""
        if not self.enabled:
            return False
        
        self.swipe_detector.on_touch_down(touch)
        self.long_press_detector.on_touch_down(touch)
        return False
    
    def on_touch_move(self, touch: MotionEvent) -> bool:
        """Delegación de touch move"""
        if not self.enabled:
            return False
        
        self.long_press_detector.on_touch_move(touch)
        return False
    
    def on_touch_up(self, touch: MotionEvent) -> bool:
        """Delegación de touch up"""
        if not self.enabled:
            return False
        
        self.swipe_detector.on_touch_up(touch)
        self.long_press_detector.on_touch_up(touch)
        return False
    
    def enable(self) -> None:
        """Habilitar detección de gestos"""
        self.enabled = True
    
    def disable(self) -> None:
        """Deshabilitar detección de gestos"""
        self.enabled = False


# Instancia global
_gesture_manager: Optional[GestureManager] = None


def get_gesture_manager() -> GestureManager:
    """Obtener instancia global de GestureManager"""
    global _gesture_manager
    if _gesture_manager is None:
        _gesture_manager = GestureManager()
    return _gesture_manager


def setup_gesture_manager(widget) -> GestureManager:
    """
    Configurar GestureManager en un widget
    
    Args:
        widget: Widget de Kivy donde aplicar gestos
    
    Returns:
        GestureManager configurado
    """
    manager = get_gesture_manager()
    
    # Vincular eventos
    widget.bind(
        on_touch_down=manager.on_touch_down,
        on_touch_move=manager.on_touch_move,
        on_touch_up=manager.on_touch_up
    )
    
    return manager

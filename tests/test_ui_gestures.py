"""
Tests para gesture detection - Slice 11
"""

import pytest
import time
from unittest.mock import Mock, MagicMock
from gf_mobile.ui.gestures import (
    SwipeDetector, LongPressDetector, GestureManager,
    SwipeGesture, LongPressGesture, get_gesture_manager
)


class MockMotionEvent:
    """Mock de MotionEvent de Kivy"""
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y


class TestSwipeDetector:
    """Tests para SwipeDetector"""
    
    def test_init_default_values(self):
        """Inicialización con valores por defecto"""
        detector = SwipeDetector()
        assert detector.min_distance == SwipeDetector.DEFAULT_MIN_DISTANCE
        assert detector.min_velocity == SwipeDetector.DEFAULT_MIN_VELOCITY
        assert detector.max_time == SwipeDetector.DEFAULT_MAX_TIME
    
    def test_init_custom_values(self):
        """Inicialización con valores personalizados"""
        detector = SwipeDetector(min_distance=50, min_velocity=200)
        assert detector.min_distance == 50
        assert detector.min_velocity == 200
    
    def test_touch_down_state(self):
        """on_touch_down establece estado"""
        detector = SwipeDetector()
        touch = MockMotionEvent(x=100, y=100)
        
        result = detector.on_touch_down(touch)
        
        assert result is False  # Permitir que otros lo procesen
        assert detector.touching is True
        assert detector.touch_start_x == 100
        assert detector.touch_start_y == 100
    
    def test_swipe_right_detected(self):
        """Detectar swipe a la derecha"""
        callback = Mock()
        detector = SwipeDetector(on_swipe=callback, min_distance=50)
        
        # Simular swipe
        touch_down = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch_down)
        
        time.sleep(0.1)  # Pequeña espera
        touch_up = MockMotionEvent(x=200, y=100)  # 100px a la derecha
        detector.on_touch_up(touch_up)
        
        # Verificar que se llamó callback
        assert callback.called
        gesture = callback.call_args[0][0]
        assert gesture.direction == "right"
        assert gesture.distance >= 50
    
    def test_swipe_left_detected(self):
        """Detectar swipe a la izquierda"""
        callback = Mock()
        detector = SwipeDetector(on_swipe=callback, min_distance=50)
        
        touch_down = MockMotionEvent(x=200, y=100)
        detector.on_touch_down(touch_down)
        
        time.sleep(0.1)
        touch_up = MockMotionEvent(x=100, y=100)  # 100px a la izquierda
        detector.on_touch_up(touch_up)
        
        assert callback.called
        gesture = callback.call_args[0][0]
        assert gesture.direction == "left"
    
    def test_swipe_down_detected(self):
        """Detectar swipe hacia abajo"""
        callback = Mock()
        detector = SwipeDetector(on_swipe=callback, min_distance=50)
        
        touch_down = MockMotionEvent(x=100, y=200)
        detector.on_touch_down(touch_down)
        
        time.sleep(0.1)
        touch_up = MockMotionEvent(x=100, y=100)  # 100px hacia abajo
        detector.on_touch_up(touch_up)
        
        assert callback.called
        gesture = callback.call_args[0][0]
        assert gesture.direction == "down"
    
    def test_swipe_up_detected(self):
        """Detectar swipe hacia arriba"""
        callback = Mock()
        detector = SwipeDetector(on_swipe=callback, min_distance=50)
        
        touch_down = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch_down)
        
        time.sleep(0.1)
        touch_up = MockMotionEvent(x=100, y=200)  # 100px hacia arriba
        detector.on_touch_up(touch_up)
        
        assert callback.called
        gesture = callback.call_args[0][0]
        assert gesture.direction == "up"
    
    def test_swipe_too_short_ignored(self):
        """Swipe demasiado corto se ignora"""
        callback = Mock()
        detector = SwipeDetector(on_swipe=callback, min_distance=100)
        
        touch_down = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch_down)
        
        touch_up = MockMotionEvent(x=150, y=100)  # Solo 50px
        detector.on_touch_up(touch_up)
        
        assert not callback.called
    
    def test_swipe_too_slow_ignored(self):
        """Swipe demasiado lento se ignora"""
        callback = Mock()
        detector = SwipeDetector(on_swipe=callback, min_distance=100, min_velocity=300)
        
        touch_down = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch_down)
        
        time.sleep(1)  # Espera larga = velocidad baja
        touch_up = MockMotionEvent(x=200, y=100)
        detector.on_touch_up(touch_up)
        
        assert not callback.called
    
    def test_swipe_too_long_ignored(self):
        """Swipe demasiado largo en tiempo se ignora"""
        callback = Mock()
        detector = SwipeDetector(on_swipe=callback, max_time=100)  # 100ms
        
        touch_down = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch_down)
        
        time.sleep(0.2)  # 200ms > 100ms
        touch_up = MockMotionEvent(x=200, y=100)
        detector.on_touch_up(touch_up)
        
        assert not callback.called
    
    def test_swipe_gesture_properties(self):
        """Verificar propiedades de SwipeGesture"""
        callback = Mock()
        detector = SwipeDetector(on_swipe=callback, min_distance=50)
        
        touch_down = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch_down)
        
        time.sleep(0.1)
        touch_up = MockMotionEvent(x=200, y=100)
        detector.on_touch_up(touch_up)
        
        gesture = callback.call_args[0][0]
        assert isinstance(gesture, SwipeGesture)
        assert gesture.direction in ["left", "right", "up", "down"]
        assert gesture.velocity > 0
        assert gesture.distance > 0
        assert gesture.duration > 0


class TestLongPressDetector:
    """Tests para LongPressDetector"""
    
    def test_init_default_values(self):
        """Inicialización con valores por defecto"""
        detector = LongPressDetector()
        assert detector.duration == LongPressDetector.DEFAULT_DURATION
        assert detector.touching is False
    
    def test_init_custom_duration(self):
        """Inicialización con duración personalizada"""
        detector = LongPressDetector(duration=1.0)
        assert detector.duration == 1.0
    
    def test_touch_down_state(self):
        """on_touch_down establece estado"""
        detector = LongPressDetector()
        touch = MockMotionEvent(x=100, y=100)
        
        result = detector.on_touch_down(touch)
        
        assert result is False
        assert detector.touching is True
        assert detector.long_press_detected is False
    
    def test_long_press_detected(self):
        """Detectar long-press correctamente"""
        callback = Mock()
        detector = LongPressDetector(on_long_press=callback, duration=0.1)
        
        touch = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch)
        
        time.sleep(0.2)  # Esperar más que duration
        
        # Simular el chequeo
        detector._check_long_press(touch)
        
        assert callback.called
        gesture = callback.call_args[0][0]
        assert isinstance(gesture, LongPressGesture)
        assert gesture.duration > 0
    
    def test_long_press_cancelled_on_move(self):
        """Long-press se cancela si se mueve mucho"""
        callback = Mock()
        detector = LongPressDetector(on_long_press=callback, duration=0.1)
        
        touch_down = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch_down)
        
        # Mover más de 10px
        touch_move = MockMotionEvent(x=150, y=100)
        detector.on_touch_move(touch_move)
        
        # El evento no debería ser detectado
        assert detector.scheduled_event is None
    
    def test_long_press_cancelled_on_release(self):
        """Long-press se cancela al soltar"""
        callback = Mock()
        detector = LongPressDetector(on_long_press=callback, duration=0.5)
        
        touch = MockMotionEvent(x=100, y=100)
        detector.on_touch_down(touch)
        
        time.sleep(0.1)
        detector.on_touch_up(touch)
        
        # No debería detectarse (soltado antes de duration)
        assert detector.touching is False


class TestGestureManager:
    """Tests para GestureManager"""
    
    def test_init_state(self):
        """Inicialización correcta"""
        manager = GestureManager()
        assert manager.enabled is True
        assert manager.swipe_detector is not None
        assert manager.long_press_detector is not None
    
    def test_set_swipe_callback(self):
        """Configurar callback para swipe"""
        manager = GestureManager()
        callback = Mock()
        manager.set_swipe_callback(callback)
        
        assert manager.swipe_detector.on_swipe is callback
    
    def test_set_long_press_callback(self):
        """Configurar callback para long-press"""
        manager = GestureManager()
        callback = Mock()
        manager.set_long_press_callback(callback)
        
        assert manager.long_press_detector.on_long_press is callback
    
    def test_enable_disable(self):
        """Habilitar y deshabilitar gestos"""
        manager = GestureManager()
        
        assert manager.enabled is True
        manager.disable()
        assert manager.enabled is False
        manager.enable()
        assert manager.enabled is True
    
    def test_touch_delegation_when_disabled(self):
        """No delegar toques cuando está deshabilitado"""
        manager = GestureManager()
        callback = Mock()
        manager.set_swipe_callback(callback)
        
        manager.disable()
        
        touch = MockMotionEvent(x=100, y=100)
        manager.on_touch_down(touch)
        
        # No debería procesarse
        assert manager.swipe_detector.touching is False


class TestHelperFunctions:
    """Tests para funciones helper"""
    
    def test_get_gesture_manager_singleton(self):
        """get_gesture_manager retorna singleton"""
        manager1 = get_gesture_manager()
        manager2 = get_gesture_manager()
        
        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

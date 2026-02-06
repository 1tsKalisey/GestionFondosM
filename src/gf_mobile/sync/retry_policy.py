"""
RetryPolicy: Estrategia de reintentos con exponential backoff
"""

from dataclasses import dataclass
from typing import Optional
import time
import math


@dataclass
class RetryPolicy:
    """
    Configura comportamiento de reintentos con exponential backoff.
    
    Fórmula: delay = base_delay * (multiplier ^ attempt) + jitter
    Máximo: max_delay
    """
    
    base_delay: float = 1.0          # Delay inicial en segundos
    multiplier: float = 2.0           # Factor exponencial
    max_delay: float = 300.0          # Máximo delay (5 minutos)
    max_retries: int = 5              # Máximo número de reintentos
    jitter: bool = True               # Agregar aleatoriedad para evitar thundering herd

    def get_delay(self, attempt: int) -> float:
        """
        Calcula delay para el intento especificado.
        
        Args:
            attempt: Número de intento (0-based)
        
        Returns:
            Tiempo en segundos a esperar antes del siguiente intento
        """
        if attempt >= self.max_retries:
            return None  # No reintentar más
        
        # Delay exponencial: base_delay * multiplier^attempt
        delay = self.base_delay * (self.multiplier ** attempt)
        
        # Capped delay
        delay = min(delay, self.max_delay)
        
        # Agregar jitter (±20%)
        if self.jitter:
            jitter_factor = 0.8 + (0.4 * (hash(attempt) % 100) / 100)
            delay = delay * jitter_factor
        
        return delay

    def should_retry(self, attempt: int) -> bool:
        """¿Se debe reintentar después de este intento?"""
        return attempt < self.max_retries

    def __repr__(self) -> str:
        return (
            f"RetryPolicy(base={self.base_delay}s, "
            f"multiplier={self.multiplier}x, "
            f"max={self.max_delay}s, "
            f"max_retries={self.max_retries})"
        )

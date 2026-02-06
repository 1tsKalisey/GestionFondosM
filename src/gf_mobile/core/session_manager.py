"""
Gestor de sesiones con persistencia
Mantiene sesión activa hasta 3 meses
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import keyring

from gf_mobile.core.config import get_settings

logger = logging.getLogger(__name__)


class SessionData:
    """Datos de sesión persistente"""

    def __init__(
        self,
        user_id: str,
        email: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.created_at = created_at or datetime.now(timezone.utc)

    def is_valid(self, max_days: int = 90) -> bool:
        """Verificar si la sesión sigue siendo válida (< 3 meses)"""
        if not self.created_at:
            return False
        expiry_date = self.created_at + timedelta(days=max_days)
        return datetime.now(timezone.utc) < expiry_date

    def days_remaining(self, max_days: int = 90) -> int:
        """Obtener días restantes para que expire la sesión"""
        if not self.created_at:
            return 0
        expiry_date = self.created_at + timedelta(days=max_days)
        remaining = (expiry_date - datetime.now(timezone.utc)).days
        return max(0, remaining)

    def to_dict(self) -> Dict[str, Any]:
        """Serializar a diccionario"""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Deserializar desde diccionario"""
        return cls(
            user_id=data["user_id"],
            email=data.get("email"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class SessionManager:
    """Gestor de sesiones persistentes"""

    SESSION_STORAGE_KEY = "gestionfondos_session"
    SESSION_MAX_DAYS = 90  # 3 meses

    def __init__(self):
        self.settings = get_settings()
        self.current_session: Optional[SessionData] = None
        self._load_session()

    def _load_session(self) -> None:
        """Cargar sesión desde almacenamiento seguro"""
        try:
            stored = keyring.get_password("gestionfondos_mobile", self.SESSION_STORAGE_KEY)
            if stored:
                data = json.loads(stored)
                self.current_session = SessionData.from_dict(data)
                
                # Verificar si sigue siendo válida
                if self.current_session.is_valid(self.SESSION_MAX_DAYS):
                    logger.info(
                        f"Sesión válida cargada para usuario: {self.current_session.user_id}"
                    )
                else:
                    logger.info("Sesión expirada, limpiando...")
                    self._clear_session()
            else:
                logger.debug("No hay sesión almacenada")
        except Exception as e:
            logger.warning(f"Error al cargar sesión: {e}")
            self.current_session = None

    def _save_session(self, session: SessionData) -> None:
        """Guardar sesión en almacenamiento seguro"""
        try:
            keyring.set_password(
                "gestionfondos_mobile",
                self.SESSION_STORAGE_KEY,
                json.dumps(session.to_dict()),
            )
            logger.info(f"Sesión guardada para usuario: {session.user_id}")
        except Exception as e:
            logger.warning(f"No se pudo guardar sesión de forma segura: {e}")

    def _clear_session(self) -> None:
        """Limpiar sesión del almacenamiento"""
        try:
            keyring.delete_password("gestionfondos_mobile", self.SESSION_STORAGE_KEY)
            logger.info("Sesión eliminada del almacenamiento")
        except Exception:
            pass  # Ignorar si no existe

    def create_session(self, user_id: str, email: Optional[str] = None) -> SessionData:
        """Crear nueva sesión"""
        session = SessionData(user_id=user_id, email=email)
        self._save_session(session)
        self.current_session = session
        return session

    def has_valid_session(self) -> bool:
        """Verificar si hay sesión válida activa"""
        if not self.current_session:
            return False
        return self.current_session.is_valid(self.SESSION_MAX_DAYS)

    def get_current_session(self) -> Optional[SessionData]:
        """Obtener sesión actual si es válida"""
        if self.has_valid_session():
            return self.current_session
        return None

    def logout(self) -> None:
        """Cerrar sesión"""
        self._clear_session()
        self.current_session = None
        logger.info("Sesión cerrada")

    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Obtener información de la sesión actual"""
        if not self.has_valid_session():
            return None
        
        session = self.current_session
        return {
            "user_id": session.user_id,
            "email": session.email,
            "created_at": session.created_at.isoformat(),
            "days_remaining": session.days_remaining(self.SESSION_MAX_DAYS),
        }

"""
Configuración centralizada de la app.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values


@dataclass
class Settings:
    """Configuración de la aplicación."""

    # Firebase
    FIREBASE_API_KEY: str = ""
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_AUTH_DOMAIN: str = ""
    FIREBASE_STORAGE_BUCKET: str = ""
    FIREBASE_APP_ID: str = ""
    FIREBASE_MEASUREMENT_ID: str = ""

    # Firebase Cloud Messaging
    FIREBASE_FCM_VAPID_KEY: str = ""
    FIREBASE_FCM_SENDER_ID: str = ""

    # Google OAuth (para login con Google)
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8080"

    # Firestore URLs (REST API)
    FIRESTORE_API_URL: str = "https://firestore.googleapis.com/v1"
    FIREBASE_AUTH_URL: str = "https://identitytoolkit.googleapis.com/v1"

    # Database
    DB_PATH: Path = Path.home() / ".config" / "gestionfondos_mobile" / "app.db"

    # Sync
    SYNC_INTERVAL_MINUTES: int = 15
    SYNC_TIMEOUT_SECONDS: int = 30
    SYNC_MAX_RETRIES: int = 5

    # Security
    TOKEN_STORAGE_KEY: str = "gestionfondos_auth_tokens"
    DEVICE_ID_STORAGE_KEY: str = "gestionfondos_device_id"

    # UI
    THEME: str = "light"
    LANG: str = "es"

    # Debug
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    def ensure_db_dir(self) -> None:
        """Asegurar que existe el directorio de BD."""
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        return f"<Settings db={self.DB_PATH} theme={self.THEME}>"


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "si"}


def _as_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_raw_config() -> dict[str, Any]:
    dotenv_config = dotenv_values(".env")
    merged = {k: v for k, v in dotenv_config.items() if v is not None}
    merged.update(os.environ)
    return merged


def get_settings() -> Settings:
    """Factory para obtener settings a partir de .env y variables de entorno."""
    values = _load_raw_config()

    return Settings(
        FIREBASE_API_KEY=str(values.get("FIREBASE_API_KEY", "")),
        FIREBASE_PROJECT_ID=str(values.get("FIREBASE_PROJECT_ID", "")),
        FIREBASE_AUTH_DOMAIN=str(values.get("FIREBASE_AUTH_DOMAIN", "")),
        FIREBASE_STORAGE_BUCKET=str(values.get("FIREBASE_STORAGE_BUCKET", "")),
        FIREBASE_APP_ID=str(values.get("FIREBASE_APP_ID", "")),
        FIREBASE_MEASUREMENT_ID=str(values.get("FIREBASE_MEASUREMENT_ID", "")),
        FIREBASE_FCM_VAPID_KEY=str(values.get("FIREBASE_FCM_VAPID_KEY", "")),
        FIREBASE_FCM_SENDER_ID=str(values.get("FIREBASE_FCM_SENDER_ID", "")),
        GOOGLE_OAUTH_CLIENT_ID=str(values.get("GOOGLE_OAUTH_CLIENT_ID", "")),
        GOOGLE_OAUTH_CLIENT_SECRET=str(values.get("GOOGLE_OAUTH_CLIENT_SECRET", "")),
        GOOGLE_OAUTH_REDIRECT_URI=str(
            values.get("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8080")
        ),
        FIRESTORE_API_URL=str(
            values.get("FIRESTORE_API_URL", "https://firestore.googleapis.com/v1")
        ),
        FIREBASE_AUTH_URL=str(
            values.get("FIREBASE_AUTH_URL", "https://identitytoolkit.googleapis.com/v1")
        ),
        DB_PATH=Path(
            str(
                values.get(
                    "GF_DB_PATH",
                    Path.home() / ".config" / "gestionfondos_mobile" / "app.db",
                )
            )
        ),
        SYNC_INTERVAL_MINUTES=_as_int(values.get("GF_SYNC_INTERVAL"), 15),
        SYNC_TIMEOUT_SECONDS=_as_int(values.get("GF_SYNC_TIMEOUT"), 30),
        SYNC_MAX_RETRIES=_as_int(values.get("GF_SYNC_MAX_RETRIES"), 5),
        THEME=str(values.get("GF_THEME", "light")),
        LANG=str(values.get("GF_LANG", "es")),
        DEBUG=_as_bool(values.get("GF_DEBUG"), False),
        LOG_LEVEL=str(values.get("GF_LOG_LEVEL", "INFO")),
    )

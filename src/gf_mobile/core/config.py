"""
Configuración centralizada de la app
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Firebase
    FIREBASE_API_KEY: str = Field(default="", env="FIREBASE_API_KEY")
    FIREBASE_PROJECT_ID: str = Field(default="", env="FIREBASE_PROJECT_ID")
    FIREBASE_AUTH_DOMAIN: str = Field(default="", env="FIREBASE_AUTH_DOMAIN")
    FIREBASE_STORAGE_BUCKET: str = Field(default="", env="FIREBASE_STORAGE_BUCKET")
    FIREBASE_APP_ID: str = Field(default="", env="FIREBASE_APP_ID")
    FIREBASE_MEASUREMENT_ID: str = Field(default="", env="FIREBASE_MEASUREMENT_ID")

    # Firebase Cloud Messaging
    FIREBASE_FCM_VAPID_KEY: str = Field(default="", env="FIREBASE_FCM_VAPID_KEY")
    FIREBASE_FCM_SENDER_ID: str = Field(default="", env="FIREBASE_FCM_SENDER_ID")

    # Google OAuth (para login con Google)
    GOOGLE_OAUTH_CLIENT_ID: str = Field(default="", env="GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET: str = Field(default="", env="GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_REDIRECT_URI: str = Field(
        default="http://localhost:8080",
        env="GOOGLE_OAUTH_REDIRECT_URI",
    )

    # Firestore URLs (REST API)
    FIRESTORE_API_URL: str = Field(
        default="https://firestore.googleapis.com/v1",
        env="FIRESTORE_API_URL",
    )
    FIREBASE_AUTH_URL: str = Field(
        default="https://identitytoolkit.googleapis.com/v1",
        env="FIREBASE_AUTH_URL",
    )

    # Database
    DB_PATH: Path = Field(
        default_factory=lambda: Path.home() / ".config" / "gestionfondos_mobile" / "app.db",
        env="GF_DB_PATH",
    )

    # Sync
    SYNC_INTERVAL_MINUTES: int = Field(default=15, env="GF_SYNC_INTERVAL")
    SYNC_TIMEOUT_SECONDS: int = Field(default=30, env="GF_SYNC_TIMEOUT")
    SYNC_MAX_RETRIES: int = Field(default=5, env="GF_SYNC_MAX_RETRIES")

    # Security
    TOKEN_STORAGE_KEY: str = "gestionfondos_auth_tokens"
    DEVICE_ID_STORAGE_KEY: str = "gestionfondos_device_id"

    # UI
    THEME: str = Field(default="light", env="GF_THEME")
    LANG: str = Field(default="es", env="GF_LANG")

    # Debug
    DEBUG: bool = Field(default=False, env="GF_DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="GF_LOG_LEVEL")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",  # Ignorar variables extra del .env
    }

    def ensure_db_dir(self) -> None:
        """Asegurar que existe el directorio de BD"""
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        return f"<Settings db={self.DB_PATH} theme={self.THEME}>"


def get_settings() -> Settings:
    """Factory para obtener settings (singleton pattern)"""
    return Settings()

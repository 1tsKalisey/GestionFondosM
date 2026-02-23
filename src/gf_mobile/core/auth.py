"""
Autenticación con Firebase Auth usando REST API
Soporte para login, registro, refresh token, logout, Google Sign-In
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass
import importlib
import importlib.util
import asyncio

from gf_mobile.core.config import get_settings
from gf_mobile.core.exceptions import (
    AuthError,
    TokenExpiredError,
    InvalidCredentialsError,
    NetworkError,
)
from gf_mobile.core.http_client import request_json

logger = logging.getLogger(__name__)


@dataclass
class AuthTokens:
    """Estructura de tokens de autenticación"""

    id_token: str
    refresh_token: str
    expires_at: datetime
    user_id: str

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Verificar si token está expirado (con buffer de 5 min)"""
        return datetime.now(timezone.utc) >= (self.expires_at - timedelta(seconds=buffer_seconds))

    def to_dict(self) -> Dict[str, Any]:
        """Serializar a dict para almacenamiento"""
        return {
            "id_token": self.id_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthTokens":
        """Deserializar desde dict"""
        return cls(
            id_token=data["id_token"],
            refresh_token=data["refresh_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            user_id=data["user_id"],
        )


class AuthService:
    """
    Servicio de autenticación con Firebase Auth REST API
    Maneja: login, registro, refresh token, logout, token storage seguro
    """

    def __init__(self):
        self.settings = get_settings()
        self.tokens: Optional[AuthTokens] = None
        self._keyring = self._load_keyring()
        self._load_tokens_from_storage()

    def _load_keyring(self):
        """Carga keyring si está disponible en el entorno."""
        if importlib.util.find_spec("keyring") is None:
            return None
        try:
            return importlib.import_module("keyring")
        except Exception as exc:
            logger.warning(f"No se pudo inicializar keyring: {exc}")
            return None

    def _get_storage_key(self) -> str:
        """Clave única para almacenamiento de tokens (keyring)"""
        return self.settings.TOKEN_STORAGE_KEY

    def _store_tokens_secure(self, tokens: AuthTokens) -> None:
        """Almacenar tokens de forma segura usando keyring del SO"""
        if self._keyring is None:
            self.tokens = tokens
            return
        try:
            self._keyring.set_password(
                "gestionfondos_mobile",
                self._get_storage_key(),
                json.dumps(tokens.to_dict()),
            )
            logger.info("Tokens almacenados de forma segura")
        except Exception as e:
            logger.warning(f"No se pudo almacenar tokens de forma segura (keyring): {e}")
            # Fallback: almacenar en memoria (menos seguro pero funcional)
            self.tokens = tokens

    def _load_tokens_from_storage(self) -> None:
        """Cargar tokens desde almacenamiento seguro"""
        if self._keyring is None:
            self.tokens = None
            return
        try:
            stored = self._keyring.get_password(
                "gestionfondos_mobile",
                self._get_storage_key(),
            )
            if stored:
                data = json.loads(stored)
                self.tokens = AuthTokens.from_dict(data)
                logger.info(f"Tokens cargados para usuario {self.tokens.user_id}")
            else:
                logger.debug("No se encontraron tokens almacenados")
        except Exception as e:
            logger.debug(f"Error al cargar tokens: {e}")
            self.tokens = None

    def _clear_tokens_from_storage(self) -> None:
        """Limpiar tokens del almacenamiento"""
        if self._keyring is None:
            self.tokens = None
            return
        try:
            self._keyring.delete_password("gestionfondos_mobile", self._get_storage_key())
            logger.info("Tokens eliminados del almacenamiento")
        except Exception:
            pass  # Ignorar si no existen

    def _is_android(self) -> bool:
        return sys.platform == "android" or bool(os.environ.get("ANDROID_ARGUMENT"))

    def _ensure_firebase_auth_config(self) -> None:
        if not (self.settings.FIREBASE_API_KEY or "").strip():
            raise AuthError(
                "FIREBASE_API_KEY no configurada. En Android, empaqueta src/.env "
                "o define la variable en el entorno de build."
            )

    async def sign_up(self, email: str, password: str) -> AuthTokens:
        """
        Registrar nuevo usuario con email y contrasena
        
        Args:
            email: Email del usuario
            password: Contrasena (min 6 caracteres en Firebase)
        
        Returns:
            AuthTokens con idToken, refreshToken, etc.
        
        Raises:
            InvalidCredentialsError: Email ya existe o contrasena invalida
            NetworkError: Error de conectividad
        """
        self._ensure_firebase_auth_config()
        url = f"{self.settings.FIREBASE_AUTH_URL}/accounts:signUp"
        params = {"key": self.settings.FIREBASE_API_KEY}
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        try:
            status, data, text = await request_json(
                "POST", url, json_body=payload, params=params, timeout=10
            )

            if status == 200:
                tokens = self._extract_tokens(data or {}, email)
                self._store_tokens_secure(tokens)
                self.tokens = tokens
                logger.info(f"Usuario registrado: {email}")
                return tokens

            error_code = (data or {}).get("error", {}).get("message", "Unknown")
            if "EMAIL_EXISTS" in error_code:
                raise InvalidCredentialsError(f"El email {email} ya esta registrado")
            if "WEAK_PASSWORD" in error_code:
                raise InvalidCredentialsError("Contrasena muy debil (min 6 caracteres)")
            raise InvalidCredentialsError(f"Error al registrar: {error_code or text}")

        except (AuthError, InvalidCredentialsError):
            raise
        except Exception as e:
            raise NetworkError(f"Error de conexion al registrar: {e}")

    async def sign_in(self, email: str, password: str) -> AuthTokens:
        """
        Iniciar sesion con email y contrasena
        
        Args:
            email: Email del usuario
            password: Contrasena
        
        Returns:
            AuthTokens con idToken, refreshToken, etc.
        
        Raises:
            InvalidCredentialsError: Credenciales invalidas
            NetworkError: Error de conectividad
        """
        self._ensure_firebase_auth_config()
        url = f"{self.settings.FIREBASE_AUTH_URL}/accounts:signInWithPassword"
        params = {"key": self.settings.FIREBASE_API_KEY}
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        try:
            status, data, text = await request_json(
                "POST", url, json_body=payload, params=params, timeout=10
            )

            if status == 200:
                tokens = self._extract_tokens(data or {}, email)
                self._store_tokens_secure(tokens)
                self.tokens = tokens
                logger.info(f"Sesion iniciada: {email}")
                return tokens

            error_code = (data or {}).get("error", {}).get("message", "Unknown")
            if "INVALID_PASSWORD" in error_code or "INVALID_EMAIL" in error_code:
                raise InvalidCredentialsError("Email o contrasena incorrectos")
            if "USER_DISABLED" in error_code:
                raise InvalidCredentialsError("Usuario deshabilitado")
            raise InvalidCredentialsError(f"Error al iniciar sesion: {error_code or text}")

        except (AuthError, InvalidCredentialsError):
            raise
        except Exception as e:
            raise NetworkError(f"Error de conexion al iniciar sesion: {e}")

    async def refresh_tokens(self) -> AuthTokens:
        """
        Refrescar idToken usando refreshToken
        Llamar cuando idToken este proximo a expirar
        
        Returns:
            AuthTokens actualizado con nuevo idToken
        
        Raises:
            TokenExpiredError: RefreshToken expirado o invalido
            NetworkError: Error de conectividad
        """
        if not self.tokens or not self.tokens.refresh_token:
            raise AuthError("No hay tokens validos para refrescar")
        self._ensure_firebase_auth_config()

        url = "https://securetoken.googleapis.com/v1/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.tokens.refresh_token,
        }
        params = {"key": self.settings.FIREBASE_API_KEY}

        try:
            status, data, text = await request_json(
                "POST", url, data=payload, params=params, timeout=10
            )

            if status == 200:
                new_tokens = self._extract_tokens_from_refresh(data or {})
                # Preservar datos de usuario
                new_tokens.user_id = self.tokens.user_id
                self._store_tokens_secure(new_tokens)
                self.tokens = new_tokens
                logger.info(f"Tokens refrescados para usuario {new_tokens.user_id}")
                return new_tokens

            logger.warning("RefreshToken invalido o expirado")
            self.sign_out()
            raise TokenExpiredError("RefreshToken expirado")

        except (AuthError, TokenExpiredError):
            raise
        except Exception as e:
            raise NetworkError(f"Error al refrescar tokens: {e}")

    async def get_valid_id_token(self) -> str:
        """
        Obtener idToken válido, refrescando si es necesario
        Llamar antes de cada request a Firestore
        
        Returns:
            idToken válido y activo
        
        Raises:
            AuthError: No hay tokens o error al refrescar
        """
        if not self.tokens:
            raise AuthError("No autenticado. Debes iniciar sesión primero")

        if self.tokens.is_expired():
            logger.info("idToken expirado, refrescando...")
            await self.refresh_tokens()

        return self.tokens.id_token

    def get_user_id(self) -> Optional[str]:
        """Obtener user ID del usuario autenticado"""
        return self.tokens.user_id if self.tokens else None

    def get_current_user_email(self) -> Optional[str]:
        """Obtener email del usuario autenticado (si está disponible)"""
        # Firebase REST no devuelve email automáticamente; debe recuperarse de otra forma
        # Por ahora retornar None; mejorar en siguiente versión
        return None

    def is_authenticated(self) -> bool:
        """Verificar si usuario está autenticado"""
        return self.tokens is not None and not self.tokens.is_expired()

    def sign_out(self) -> None:
        """Cerrar sesión y limpiar tokens"""
        self._clear_tokens_from_storage()
        self.tokens = None
        logger.info("Sesión cerrada")
        
        # También limpiar sesión persistente
        try:
            from gf_mobile.core.session_manager import SessionManager
            session_manager = SessionManager()
            session_manager.logout()
        except Exception as e:
            logger.warning(f"Error al limpiar sesión: {e}")

    async def sign_in_with_google(self) -> AuthTokens:
        """
        Iniciar sesion con Google de forma simple
        Usa google-auth-oauthlib para manejar el flujo automaticamente
        """
        if self._is_android():
            raise AuthError(
                "Google Sign-In no esta soportado en Android en esta version. "
                "Usa email/contrasena o implementa un flujo OAuth nativo."
            )
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            import google.auth.transport.requests
            
            # Configuracion del cliente OAuth de Google
            # Necesitas crear esto en Google Cloud Console
            client_id = self.settings.GOOGLE_OAUTH_CLIENT_ID
            client_secret = self.settings.GOOGLE_OAUTH_CLIENT_SECRET
            redirect_uri = self.settings.GOOGLE_OAUTH_REDIRECT_URI

            if not client_id or not client_secret:
                raise AuthError(
                    "Falta configurar GOOGLE_OAUTH_CLIENT_ID y GOOGLE_OAUTH_CLIENT_SECRET en .env"
                )

            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            }
            
            # Scopes necesarios para obtener informacion basica del usuario
            scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email',
                     'https://www.googleapis.com/auth/userinfo.profile']
            
            # Crear flujo de autenticacion
            flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
            
            # Ejecutar el flujo local (abre navegador automaticamente)
            logger.info("Abriendo navegador para login de Google...")
            credentials = await asyncio.to_thread(
                flow.run_local_server, port=8080, prompt='consent'
            )
            
            # Obtener ID token de Google
            id_token = credentials.id_token
            
            if not id_token:
                raise AuthError("No se pudo obtener ID token de Google")
            
            # Intercambiar ID token por tokens de Firebase
            return await self._exchange_google_token_for_firebase(id_token)
            
        except ImportError:
            raise AuthError("Falta instalar: pip install google-auth-oauthlib")
        except Exception as e:
            logger.error(f"Error en Google Sign-In: {e}")
            raise AuthError(f"Error al iniciar sesion con Google: {e}")

    async def _exchange_google_token_for_firebase(self, google_id_token: str) -> AuthTokens:
        """Intercambiar ID token de Google por tokens de Firebase"""
        self._ensure_firebase_auth_config()
        url = f"{self.settings.FIREBASE_AUTH_URL}/accounts:signInWithIdp"
        params = {"key": self.settings.FIREBASE_API_KEY}
        payload = {
            "postBody": f"id_token={google_id_token}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnSecureToken": True,
        }
        
        try:
            status, data, text = await request_json(
                "POST", url, json_body=payload, params=params, timeout=10
            )

            if status == 200:
                email = (data or {}).get("email", "google_user")
                tokens = self._extract_tokens(data or {}, email)
                self._store_tokens_secure(tokens)
                self.tokens = tokens
                logger.info(f"Sesion iniciada con Google: {email}")
                return tokens

            error_msg = (data or {}).get("error", {}).get("message", "Unknown")
            logger.error(f"Error de Firebase: {error_msg}")
            logger.error(f"Response completa: {data or text}")
            raise AuthError(f"Error al autenticar con Google: {error_msg or text}")
        except AuthError:
            raise
        except Exception as e:
            raise NetworkError(f"Error de conexion con Google: {e}")

    @staticmethod
    def _extract_tokens(response: Dict[str, Any], email: str) -> AuthTokens:
        """Extraer tokens de respuesta de Firebase Auth"""
        id_token = response.get("idToken", "")
        refresh_token = response.get("refreshToken", "")
        expires_in_seconds = int(response.get("expiresIn", 3600))
        local_id = response.get("localId", "")

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

        return AuthTokens(
            id_token=id_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user_id=local_id,
        )

    @staticmethod
    def _extract_tokens_from_refresh(response: Dict[str, Any]) -> AuthTokens:
        """Extraer tokens de respuesta de token refresh"""
        id_token = response.get("id_token", "")
        refresh_token = response.get("refresh_token", "")
        expires_in_seconds = int(response.get("expires_in", 3600))

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

        return AuthTokens(
            id_token=id_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user_id="",  # Se actualiza desde tokens anterior
        )

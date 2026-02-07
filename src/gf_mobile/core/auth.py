"""
Autenticación con Firebase Auth usando REST API
Soporte para login, registro, refresh token, logout, Google Sign-In
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass
import importlib
import importlib.util
import aiohttp
import asyncio

from gf_mobile.core.config import get_settings
from gf_mobile.core.exceptions import (
    AuthError,
    TokenExpiredError,
    InvalidCredentialsError,
    NetworkError,
)

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
        return importlib.import_module("keyring")

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

    async def sign_up(self, email: str, password: str) -> AuthTokens:
        """
        Registrar nuevo usuario con email y contraseña
        
        Args:
            email: Email del usuario
            password: Contraseña (mín 6 caracteres en Firebase)
        
        Returns:
            AuthTokens con idToken, refreshToken, etc.
        
        Raises:
            InvalidCredentialsError: Email ya existe o contraseña inválida
            NetworkError: Error de conectividad
        """
        url = f"{self.settings.FIREBASE_AUTH_URL}/accounts:signUp"
        params = {"key": self.settings.FIREBASE_API_KEY}
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, params=params, timeout=10) as resp:
                    data = await resp.json()

                    if resp.status == 200:
                        tokens = self._extract_tokens(data, email)
                        self._store_tokens_secure(tokens)
                        self.tokens = tokens
                        logger.info(f"Usuario registrado: {email}")
                        return tokens
                    else:
                        error_code = data.get("error", {}).get("message", "Unknown")
                        if "EMAIL_EXISTS" in error_code:
                            raise InvalidCredentialsError(f"El email {email} ya está registrado")
                        elif "WEAK_PASSWORD" in error_code:
                            raise InvalidCredentialsError("Contraseña muy débil (mín 6 caracteres)")
                        else:
                            raise InvalidCredentialsError(f"Error al registrar: {error_code}")

        except aiohttp.ClientError as e:
            raise NetworkError(f"Error de conexión al registrar: {e}")

    async def sign_in(self, email: str, password: str) -> AuthTokens:
        """
        Iniciar sesión con email y contraseña
        
        Args:
            email: Email del usuario
            password: Contraseña
        
        Returns:
            AuthTokens con idToken, refreshToken, etc.
        
        Raises:
            InvalidCredentialsError: Credenciales inválidas
            NetworkError: Error de conectividad
        """
        url = f"{self.settings.FIREBASE_AUTH_URL}/accounts:signInWithPassword"
        params = {"key": self.settings.FIREBASE_API_KEY}
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, params=params, timeout=10) as resp:
                    data = await resp.json()

                    if resp.status == 200:
                        tokens = self._extract_tokens(data, email)
                        self._store_tokens_secure(tokens)
                        self.tokens = tokens
                        logger.info(f"Sesión iniciada: {email}")
                        return tokens
                    else:
                        error_code = data.get("error", {}).get("message", "Unknown")
                        if "INVALID_PASSWORD" in error_code or "INVALID_EMAIL" in error_code:
                            raise InvalidCredentialsError("Email o contraseña incorrectos")
                        elif "USER_DISABLED" in error_code:
                            raise InvalidCredentialsError("Usuario deshabilitado")
                        else:
                            raise InvalidCredentialsError(f"Error al iniciar sesión: {error_code}")

        except aiohttp.ClientError as e:
            raise NetworkError(f"Error de conexión al iniciar sesión: {e}")

    async def refresh_tokens(self) -> AuthTokens:
        """
        Refrescar idToken usando refreshToken
        Llamar cuando idToken esté próximo a expirar
        
        Returns:
            AuthTokens actualizado con nuevo idToken
        
        Raises:
            TokenExpiredError: RefreshToken expirado o inválido
            NetworkError: Error de conectividad
        """
        if not self.tokens or not self.tokens.refresh_token:
            raise AuthError("No hay tokens válidos para refrescar")

        url = "https://securetoken.googleapis.com/v1/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.tokens.refresh_token,
        }
        params = {"key": self.settings.FIREBASE_API_KEY}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, params=params, timeout=10) as resp:
                    data = await resp.json()

                    if resp.status == 200:
                        new_tokens = self._extract_tokens_from_refresh(data)
                        # Preservar datos de usuario
                        new_tokens.user_id = self.tokens.user_id
                        self._store_tokens_secure(new_tokens)
                        self.tokens = new_tokens
                        logger.info(f"Tokens refrescados para usuario {new_tokens.user_id}")
                        return new_tokens
                    else:
                        logger.warning("RefreshToken inválido o expirado")
                        self.sign_out()
                        raise TokenExpiredError("RefreshToken expirado")

        except aiohttp.ClientError as e:
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
        Iniciar sesión con Google de forma simple
        Usa google-auth-oauthlib para manejar el flujo automáticamente
        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            import google.auth.transport.requests
            
            # Configuración del cliente OAuth de Google
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
            
            # Scopes necesarios para obtener información básica del usuario
            scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 
                     'https://www.googleapis.com/auth/userinfo.profile']
            
            # Crear flujo de autenticación
            flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
            
            # Ejecutar el flujo local (abre navegador automáticamente)
            logger.info("Abriendo navegador para login de Google...")
            credentials = flow.run_local_server(port=8080, prompt='consent')
            
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
            raise AuthError(f"Error al iniciar sesión con Google: {e}")
    
    async def _exchange_google_token_for_firebase(self, google_id_token: str) -> AuthTokens:
        """Intercambiar ID token de Google por tokens de Firebase"""
        url = f"{self.settings.FIREBASE_AUTH_URL}/accounts:signInWithIdp"
        params = {"key": self.settings.FIREBASE_API_KEY}
        payload = {
            "postBody": f"id_token={google_id_token}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnSecureToken": True,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, params=params, timeout=10) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        email = data.get("email", "google_user")
                        tokens = self._extract_tokens(data, email)
                        self._store_tokens_secure(tokens)
                        self.tokens = tokens
                        logger.info(f"Sesión iniciada con Google: {email}")
                        return tokens
                    else:
                        error_msg = data.get("error", {}).get("message", "Unknown")
                        logger.error(f"Error de Firebase: {error_msg}")
                        logger.error(f"Response completa: {data}")
                        raise AuthError(f"Error al autenticar con Google: {error_msg}")
        except aiohttp.ClientError as e:
            raise NetworkError(f"Error de conexión con Google: {e}")

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

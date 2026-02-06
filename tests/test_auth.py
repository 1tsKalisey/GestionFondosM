"""
Tests para AuthService
Cubre: login, registro, token refresh, almacenamiento seguro
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from gf_mobile.core.auth import AuthService, AuthTokens
from gf_mobile.core.exceptions import (
    InvalidCredentialsError,
    TokenExpiredError,
    NetworkError,
)


class TestAuthTokens:
    """Tests para estructura de tokens"""

    def test_tokens_creation(self):
        """Crear tokens válidos"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        tokens = AuthTokens(
            id_token="id_token_xyz",
            refresh_token="refresh_token_abc",
            expires_at=expires_at,
            user_id="user_123",
        )

        assert tokens.id_token == "id_token_xyz"
        assert tokens.refresh_token == "refresh_token_abc"
        assert tokens.user_id == "user_123"
        assert not tokens.is_expired()

    def test_tokens_is_expired(self):
        """Verificar detección de expiración"""
        # Token expirado
        expired = AuthTokens(
            id_token="token",
            refresh_token="refresh",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            user_id="user",
        )
        assert expired.is_expired()

        # Token válido
        valid = AuthTokens(
            id_token="token",
            refresh_token="refresh",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            user_id="user",
        )
        assert not valid.is_expired()

    def test_tokens_buffer(self):
        """Verificar buffer de 5 minutos antes de expiración"""
        # Token vence en 4 minutos = considera expirado (buffer 5 min)
        nearly_expired = AuthTokens(
            id_token="token",
            refresh_token="refresh",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=4),
            user_id="user",
        )
        assert nearly_expired.is_expired()

    def test_tokens_serialization(self):
        """Serializar y deserializar tokens"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        original = AuthTokens(
            id_token="id_token_xyz",
            refresh_token="refresh_token_abc",
            expires_at=expires_at,
            user_id="user_123",
        )

        # Serializar
        data = original.to_dict()
        assert data["id_token"] == "id_token_xyz"
        assert data["user_id"] == "user_123"

        # Deserializar
        restored = AuthTokens.from_dict(data)
        assert restored.id_token == original.id_token
        assert restored.user_id == original.user_id
        assert restored.expires_at == original.expires_at


class TestAuthService:
    """Tests para AuthService"""

    @pytest.fixture
    def auth_service(self):
        """Crear instancia de AuthService para tests"""
        service = AuthService()
        yield service
        # Limpiar después de cada test
        service.sign_out()

    @pytest.mark.asyncio
    async def test_sign_up_success(self, auth_service):
        """Test registro exitoso"""
        # Mock de respuesta exitosa
        mock_response = {
            "idToken": "new_id_token",
            "refreshToken": "new_refresh_token",
            "expiresIn": "3600",
            "localId": "user_new_123",
        }

        with patch("gf_mobile.core.auth.aiohttp.ClientSession") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_resp
            )

            with patch.object(auth_service, "_store_tokens_secure") as mock_store:
                tokens = await auth_service.sign_up("test@example.com", "password123")

                assert tokens.id_token == "new_id_token"
                assert tokens.user_id == "user_new_123"
                assert tokens.refresh_token == "new_refresh_token"
                mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_up_email_exists(self, auth_service):
        """Test registro con email ya existente"""
        mock_response = {"error": {"message": "EMAIL_EXISTS"}}

        with patch("gf_mobile.core.auth.aiohttp.ClientSession") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 400
            mock_resp.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_resp
            )

            with pytest.raises(InvalidCredentialsError, match="ya está registrado"):
                await auth_service.sign_up("existing@example.com", "password123")

    @pytest.mark.asyncio
    async def test_sign_up_weak_password(self, auth_service):
        """Test registro con contraseña débil"""
        mock_response = {"error": {"message": "WEAK_PASSWORD"}}

        with patch("gf_mobile.core.auth.aiohttp.ClientSession") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 400
            mock_resp.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_resp
            )

            with pytest.raises(InvalidCredentialsError, match="muy débil"):
                await auth_service.sign_up("test@example.com", "short")

    @pytest.mark.asyncio
    async def test_sign_in_success(self, auth_service):
        """Test login exitoso"""
        mock_response = {
            "idToken": "login_id_token",
            "refreshToken": "login_refresh_token",
            "expiresIn": "3600",
            "localId": "user_existing_123",
        }

        with patch("gf_mobile.core.auth.aiohttp.ClientSession") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_resp
            )

            with patch.object(auth_service, "_store_tokens_secure"):
                tokens = await auth_service.sign_in("user@example.com", "password123")

                assert tokens.id_token == "login_id_token"
                assert tokens.user_id == "user_existing_123"

    @pytest.mark.asyncio
    async def test_sign_in_invalid_credentials(self, auth_service):
        """Test login con credenciales inválidas"""
        mock_response = {"error": {"message": "INVALID_PASSWORD"}}

        with patch("gf_mobile.core.auth.aiohttp.ClientSession") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 400
            mock_resp.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_resp
            )

            with pytest.raises(InvalidCredentialsError, match="Email o contraseña"):
                await auth_service.sign_in("wrong@example.com", "wrongpass")

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self, auth_service):
        """Test refresh de tokens exitoso"""
        # Setup: crear tokens iniciales
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        auth_service.tokens = AuthTokens(
            id_token="old_id_token",
            refresh_token="refresh_token_valid",
            expires_at=expires_at,
            user_id="user_123",
        )

        mock_response = {
            "id_token": "new_id_token",
            "refresh_token": "new_refresh_token",
            "expires_in": "3600",
        }

        with patch("gf_mobile.core.auth.aiohttp.ClientSession") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_resp
            )

            with patch.object(auth_service, "_store_tokens_secure"):
                new_tokens = await auth_service.refresh_tokens()

                assert new_tokens.id_token == "new_id_token"
                assert new_tokens.user_id == "user_123"  # Preservado

    @pytest.mark.asyncio
    async def test_refresh_tokens_expired(self, auth_service):
        """Test refresh con refreshToken expirado"""
        auth_service.tokens = AuthTokens(
            id_token="old_token",
            refresh_token="refresh_token_expired",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            user_id="user_123",
        )

        with patch("gf_mobile.core.auth.aiohttp.ClientSession") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 400
            mock_resp.json = AsyncMock(return_value={"error": "invalid_grant"})

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_resp
            )

            with pytest.raises(TokenExpiredError):
                await auth_service.refresh_tokens()

    @pytest.mark.asyncio
    async def test_get_valid_id_token(self, auth_service):
        """Test obtener idToken válido"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        auth_service.tokens = AuthTokens(
            id_token="valid_token",
            refresh_token="refresh",
            expires_at=expires_at,
            user_id="user_123",
        )

        token = await auth_service.get_valid_id_token()
        assert token == "valid_token"

    @pytest.mark.asyncio
    async def test_get_valid_id_token_not_authenticated(self, auth_service):
        """Test obtener token sin autenticarse"""
        auth_service.tokens = None

        with pytest.raises(Exception, match="autenticado"):
            await auth_service.get_valid_id_token()

    def test_is_authenticated(self, auth_service):
        """Test verificar autenticación"""
        assert not auth_service.is_authenticated()

        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        auth_service.tokens = AuthTokens(
            id_token="token",
            refresh_token="refresh",
            expires_at=expires_at,
            user_id="user_123",
        )
        assert auth_service.is_authenticated()

    def test_sign_out(self, auth_service):
        """Test cerrar sesión"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        auth_service.tokens = AuthTokens(
            id_token="token",
            refresh_token="refresh",
            expires_at=expires_at,
            user_id="user_123",
        )

        auth_service.sign_out()
        assert auth_service.tokens is None
        assert not auth_service.is_authenticated()

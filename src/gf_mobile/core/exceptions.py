"""
Custom exceptions para GestionFondos Mobile
"""


class GestionFondosError(Exception):
    """Base exception para toda la app"""

    pass


class AuthError(GestionFondosError):
    """Errores de autenticación"""

    pass


class TokenExpiredError(AuthError):
    """idToken expirado"""

    pass


class InvalidCredentialsError(AuthError):
    """Credenciales inválidas"""

    pass


class NetworkError(GestionFondosError):
    """Errores de red"""

    pass


class SyncError(GestionFondosError):
    """Errores de sincronización"""

    pass


class MergeConflictError(SyncError):
    """Conflicto de merge no resolvible"""

    pass


class DatabaseError(GestionFondosError):
    """Errores de base de datos local"""

    pass


class ValidationError(GestionFondosError):
    """Errores de validación de datos"""

    pass

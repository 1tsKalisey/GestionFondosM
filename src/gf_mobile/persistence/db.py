"""
Configuración de base de datos SQLite y aplicación de migraciones
"""

import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from gf_mobile.core.config import get_settings
from gf_mobile.persistence.models import Base

logger = logging.getLogger(__name__)


def build_engine():
    """
    Crear y configurar engine SQLite
    Usa StaticPool para evitar issues con threading en Kivy
    """
    settings = get_settings()
    settings.ensure_db_dir()

    db_url = f"sqlite:///{settings.DB_PATH}"

    logger.info(f"Creando engine SQLite: {db_url}")

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG,
    )

    return engine


def build_session_factory(engine=None):
    """Crear SessionFactory"""
    if engine is None:
        engine = build_engine()

    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionFactory


def apply_migrations(engine, migration_scripts: list[Path]):
    """
    Aplicar migraciones SQL en orden
    
    Args:
        engine: SQLAlchemy engine
        migration_scripts: List de archivos .sql ordenados
    """
    logger.info(f"Aplicando {len(migration_scripts)} migraciones...")

    with engine.connect() as conn:
        for script_path in migration_scripts:
            logger.debug(f"Ejecutando migración: {script_path.name}")
            with open(script_path, "r") as f:
                sql = f.read()
                # Dividir por ; para ejecutar múltiples statements
                for statement in sql.split(";"):
                    statement = statement.strip()
                    if statement:
                        try:
                            conn.execute(text(statement))
                        except Exception as e:
                            logger.warning(
                                f"Migración {script_path.name} ya aplicada o warning: {e}"
                            )
        conn.commit()

    logger.info("Migraciones completadas")


def init_database():
    """
    Inicializar base de datos: crear engine, aplicar migraciones, crear tables
    Llamar una sola vez en startup de la app
    """
    engine = build_engine()

    # Aplicar migraciones SQL
    migrations_dir = Path(__file__).parent / "migrations"
    if migrations_dir.exists():
        scripts = sorted(migrations_dir.glob("*.sql"))
        apply_migrations(engine, scripts)

    # Crear tablas desde modelos SQLAlchemy (si no existen)
    Base.metadata.create_all(engine)

    logger.info("Base de datos inicializada")

    return engine


def get_session(SessionFactory: sessionmaker) -> Session:
    """Obtener nueva sesión de BD"""
    return SessionFactory()

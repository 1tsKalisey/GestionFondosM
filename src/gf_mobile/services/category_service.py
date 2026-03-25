"""
CategoryService

Gestiona las categorias de transacciones alineado con el ORM actual.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import DatabaseError, ValidationError
from gf_mobile.persistence.models import Category, SyncOutbox, generate_uuid


class CategoryInput:
    """Input para crear/actualizar categorias."""

    def __init__(self, name: str, budget_group: str):
        self.name = name
        self.budget_group = budget_group


class CategoryService:
    """Servicio de gestion de categorias."""

    def __init__(self, session: Session, user_id: str = None):
        self.session = session
        self.user_id = user_id

    def create(self, data: CategoryInput) -> Category:
        """Crea una nueva categoria."""
        try:
            normalized_name, normalized_group = self._validate(data)
            existing = self._find_duplicate_by_name(normalized_name)
            if existing:
                return existing

            category = Category(
                name=normalized_name,
                budget_group=normalized_group,
            )
            self.session.add(category)
            self.session.flush()

            self._enqueue_sync(
                entity_type="category",
                operation="create",
                entity_id=str(category.id),
                payload=self._serialize(category),
            )
            self.session.commit()
            return category
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as exc:
            self.session.rollback()
            raise DatabaseError(f"Error al crear categoria: {str(exc)}")

    def update(self, category_id: int, data: CategoryInput) -> Category:
        """Actualiza una categoria existente."""
        try:
            normalized_name, normalized_group = self._validate(data)
            category = self._get_or_fail(category_id)

            duplicate = self._find_duplicate_by_name(normalized_name, exclude_id=category.id)
            if duplicate:
                raise ValidationError("Ya existe una categoria con el mismo nombre")

            category.name = normalized_name
            category.budget_group = normalized_group
            self.session.flush()

            self._enqueue_sync(
                entity_type="category",
                operation="update",
                entity_id=str(category.id),
                payload=self._serialize(category),
            )
            self.session.commit()
            return category
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as exc:
            self.session.rollback()
            raise DatabaseError(f"Error al actualizar categoria: {str(exc)}")

    def delete(self, category_id: int) -> bool:
        """Elimina una categoria."""
        try:
            category = self._get_or_fail(category_id)
            payload = self._serialize(category)

            self._enqueue_sync(
                entity_type="category",
                operation="delete",
                entity_id=str(category.id),
                payload=payload,
            )
            self.session.delete(category)
            self.session.commit()
            return True
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as exc:
            self.session.rollback()
            raise DatabaseError(f"Error al eliminar categoria: {str(exc)}")

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Obtiene una categoria por ID."""
        return self.session.query(Category).filter(Category.id == category_id).first()

    def list_all(self) -> list[Category]:
        """Lista todas las categorias."""
        return (
            self.session.query(Category)
            .order_by(func.lower(Category.budget_group), func.lower(Category.name))
            .all()
        )

    def _get_or_fail(self, category_id: int) -> Category:
        category = self.get_by_id(category_id)
        if not category:
            raise ValidationError(f"Categoria no encontrada: {category_id}")
        return category

    def _validate(self, data: CategoryInput) -> tuple[str, str]:
        name = (data.name or "").strip()
        if not name:
            raise ValidationError("Nombre de categoria requerido")

        budget_group = (data.budget_group or "").strip()
        if not budget_group:
            raise ValidationError("Grupo presupuestario requerido")

        return name, budget_group

    def _find_duplicate_by_name(
        self,
        name: str,
        exclude_id: Optional[int] = None,
    ) -> Optional[Category]:
        query = self.session.query(Category).filter(
            func.lower(func.trim(Category.name)) == name.lower()
        )
        if exclude_id is not None:
            query = query.filter(Category.id != exclude_id)
        return query.first()

    def _serialize(self, category: Category) -> dict:
        return {
            "id": category.id,
            "sync_id": category.sync_id,
            "name": category.name,
            "budget_group": category.budget_group,
            "created_at": self._format_timestamp(category.created_at),
        }

    def _format_timestamp(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    def _enqueue_sync(
        self,
        entity_type: str,
        operation: str,
        entity_id: str,
        payload: dict,
    ) -> None:
        event_type = "category_updated"
        if operation == "create":
            event_type = "category_created"
        elif operation == "delete":
            event_type = "category_deleted"
        outbox = SyncOutbox(
            id=generate_uuid(),
            entity_type=entity_type,
            operation=operation,
            event_type=event_type,
            entity_id=entity_id,
            payload=json.dumps(payload),
            created_at=datetime.now(timezone.utc),
            synced=False,
        )
        self.session.add(outbox)

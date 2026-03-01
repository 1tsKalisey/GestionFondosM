"""
CategoryService

Gestiona las categorias de transacciones.
"""

from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import ValidationError, DatabaseError
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

    # ==================== CRUD ====================

    def create(self, data: CategoryInput) -> Category:
        """Crea una nueva categoria."""
        try:
            normalized_name, normalized_group = self._validate(data)
            existing = self._find_duplicate(normalized_name, normalized_group)
            if existing:
                return existing

            category = Category(
                id=generate_uuid(),
                name=normalized_name,
                budget_group=normalized_group,
                synced=False,
            )
            self.session.add(category)
            self.session.flush()

            self._enqueue_sync("category", "create", category.id, self._serialize(category))
            self.session.commit()
            return category
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al crear categoria: {str(e)}")

    def update(self, category_id: str, data: CategoryInput) -> Category:
        """Actualiza una categoria existente."""
        try:
            normalized_name, normalized_group = self._validate(data)
            category = self._get_or_fail(category_id)

            duplicate = self._find_duplicate(normalized_name, normalized_group, exclude_id=category.id)
            if duplicate:
                raise ValidationError("Ya existe una categoria con el mismo nombre y grupo")

            category.name = normalized_name
            category.budget_group = normalized_group
            category.synced = False
            self.session.flush()

            self._enqueue_sync("category", "update", category.id, self._serialize(category))
            self.session.commit()
            return category
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al actualizar categoria: {str(e)}")

    def delete(self, category_id: str) -> bool:
        """Elimina una categoria."""
        try:
            category = self._get_or_fail(category_id)
            self._enqueue_sync("category", "delete", category.id, {})
            self.session.delete(category)
            self.session.commit()
            return True
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al eliminar categoria: {str(e)}")

    def get_by_id(self, category_id: str) -> Optional[Category]:
        """Obtiene una categoria por ID."""
        return self.session.query(Category).filter(Category.id == category_id).first()

    def list_all(self) -> List[Category]:
        """Lista todas las categorias."""
        return self.session.query(Category).all()

    # ==================== HELPERS ====================

    def _get_or_fail(self, category_id: str) -> Category:
        """Obtiene una categoria o falla."""
        category = self.get_by_id(category_id)
        if not category:
            raise ValidationError(f"Categoria no encontrada: {category_id}")
        return category

    def _validate(self, data: CategoryInput) -> tuple[str, str]:
        """Valida los datos de entrada y devuelve valores normalizados."""
        name = (data.name or "").strip()
        if not name:
            raise ValidationError("Nombre de categoria requerido")
        budget_group = (data.budget_group or "").strip()
        if not budget_group:
            raise ValidationError("Grupo presupuestario requerido")
        return name, budget_group

    def _find_duplicate(
        self,
        name: str,
        budget_group: str,
        exclude_id: Optional[str] = None,
    ) -> Optional[Category]:
        query = self.session.query(Category).filter(
            func.lower(func.trim(Category.name)) == name.lower(),
            func.lower(func.trim(Category.budget_group)) == budget_group.lower(),
        )
        if exclude_id is not None:
            query = query.filter(Category.id != exclude_id)
        return query.first()

    def _serialize(self, category: Category) -> dict:
        """Serializa una categoria para sincronizacion."""
        return {
            "id": category.id,
            "name": category.name,
            "budget_group": category.budget_group,
            "created_at": category.created_at.isoformat() if category.created_at else None,
            "updated_at": category.updated_at.isoformat() if category.updated_at else None,
        }

    def _enqueue_sync(self, entity_type: str, operation: str, entity_id: str, data: dict) -> None:
        """Encola una operacion para sincronizacion."""
        try:
            outbox = SyncOutbox(
                entity_type=entity_type,
                operation=operation,
                entity_id=entity_id,
                data=data,
                synced=False,
            )
            self.session.add(outbox)
        except Exception as e:
            # Log pero no falla
            print(f"Error al encolar sync: {str(e)}")

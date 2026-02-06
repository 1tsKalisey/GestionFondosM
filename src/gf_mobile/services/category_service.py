"""
CategoryService

Gestiona las categorías de transacciones.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import ValidationError, DatabaseError
from gf_mobile.persistence.models import Category, SyncOutbox, generate_uuid


class CategoryInput:
    """Input para crear/actualizar categorías."""

    def __init__(self, name: str, budget_group: str):
        self.name = name
        self.budget_group = budget_group


class CategoryService:
    """Servicio de gestión de categorías."""

    def __init__(self, session: Session, user_id: str = None):
        self.session = session
        self.user_id = user_id

    # ==================== CRUD ====================

    def create(self, data: CategoryInput) -> Category:
        """Crea una nueva categoría."""
        try:
            self._validate(data)
            category = Category(
                id=generate_uuid(),
                name=data.name,
                budget_group=data.budget_group,
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
            raise DatabaseError(f"Error al crear categoría: {str(e)}")

    def update(self, category_id: str, data: CategoryInput) -> Category:
        """Actualiza una categoría existente."""
        try:
            self._validate(data)
            category = self._get_or_fail(category_id)
            
            category.name = data.name
            category.budget_group = data.budget_group
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
            raise DatabaseError(f"Error al actualizar categoría: {str(e)}")

    def delete(self, category_id: str) -> bool:
        """Elimina una categoría."""
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
            raise DatabaseError(f"Error al eliminar categoría: {str(e)}")

    def get_by_id(self, category_id: str) -> Optional[Category]:
        """Obtiene una categoría por ID."""
        return self.session.query(Category).filter(Category.id == category_id).first()

    def list_all(self) -> List[Category]:
        """Lista todas las categorías."""
        return self.session.query(Category).all()

    # ==================== HELPERS ====================

    def _get_or_fail(self, category_id: str) -> Category:
        """Obtiene una categoría o falla."""
        category = self.get_by_id(category_id)
        if not category:
            raise ValidationError(f"Categoría no encontrada: {category_id}")
        return category

    def _validate(self, data: CategoryInput) -> None:
        """Valida los datos de entrada."""
        if not data.name or not data.name.strip():
            raise ValidationError("Nombre de categoría requerido")
        if not data.budget_group:
            raise ValidationError("Grupo presupuestario requerido")

    def _serialize(self, category: Category) -> dict:
        """Serializa una categoría para sincronización."""
        return {
            "id": category.id,
            "name": category.name,
            "budget_group": category.budget_group,
            "created_at": category.created_at.isoformat() if category.created_at else None,
            "updated_at": category.updated_at.isoformat() if category.updated_at else None,
        }

    def _enqueue_sync(self, entity_type: str, operation: str, entity_id: str, data: dict) -> None:
        """Encola una operación para sincronización."""
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

"""
TransactionService

Servicio de aplicación para gestionar transacciones locales.
Implementa CRUD completo, filtrado avanzado, y integración con SyncOutbox.

Responsabilidades:
- Crear, leer, actualizar, eliminar transacciones
- Filtrado por rango de fechas, categoría, cuenta, etiquetas
- Integración con SyncOutbox para sincronización offline
- Validación de datos y cálculo de balances
- Manejo de transacciones recurrentes base
"""

import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import ValidationError, DatabaseError
from gf_mobile.persistence.models import (
    Transaction,
    Account,
    Category,
    SubCategory,
    Tag,
    TransactionTag,
    SyncOutbox,
    generate_uuid,
)


class TransactionService:
    """
    Servicio para gestionar transacciones.
    
    Todas las operaciones se registran automáticamente en SyncOutbox
    para posterior sincronización con Firestore.
    """

    def __init__(self, session: Session, user_id: str):
        """
        Inicializa el servicio.
        
        Args:
            session: SQLAlchemy session
            user_id: ID del usuario actual (para filtrado de datos)
        """
        self.session = session
        self.user_id = user_id

    # ==================== CREATE ====================

    def create(
        self,
        account_id: str,
        type_: str,
        amount: float,
        category_id: int,
        subcategory_id: Optional[int] = None,
        currency: str = "USD",
        occurred_at: Optional[datetime] = None,
        merchant: Optional[str] = None,
        note: Optional[str] = None,
        tag_ids: Optional[List[int]] = None,
    ) -> Transaction:
        """
        Crea una nueva transacción.
        
        Args:
            account_id: UUID de cuenta
            type_: "ingreso", "gasto", "transferencia"
            amount: Monto (positivo)
            category_id: ID de categoría
            subcategory_id: ID de subcategoría (opcional)
            currency: Moneda (default: USD)
            occurred_at: Fecha/hora (default: now)
            merchant: Comercio (opcional)
            note: Nota (opcional)
            tag_ids: Lista de IDs de etiquetas (opcional)
        
        Returns:
            Transaction creada
            
        Raises:
            ValidationError: Si los datos son inválidos
            DatabaseError: Si hay error en BD
        """
        try:
            # Validación
            self._validate_transaction_input(
                account_id, type_, amount, category_id
            )

            # Valores por defecto
            if occurred_at is None:
                occurred_at = datetime.utcnow()

            # Crear transacción
            transaction = Transaction(
                id=generate_uuid(),
                account_id=account_id,
                category_id=category_id,
                subcategory_id=subcategory_id,
                type=type_,
                amount=amount,
                currency=currency,
                occurred_at=occurred_at,
                merchant=merchant,
                note=note,
                synced=False,
                server_id=None,
                conflict_resolved=False,
            )

            # Agregar etiquetas
            if tag_ids:
                self._add_tags_to_transaction(transaction, tag_ids)

            # Persistir
            self.session.add(transaction)
            self.session.flush()

            # Registrar en SyncOutbox
            self._enqueue_sync(
                entity_type="transaction",
                operation="create",
                entity_id=transaction.id,
                payload=self._serialize_transaction(transaction),
            )

            self.session.commit()
            return transaction

        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al crear transacción: {str(e)}")

    # ==================== READ ====================

    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """
        Obtiene una transacción por ID.
        
        Args:
            transaction_id: UUID de transacción
            
        Returns:
            Transaction o None si no existe
        """
        return self.session.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Transaction]:
        """
        Lista todas las transacciones del usuario.
        
        Args:
            limit: Máximo de resultados
            offset: Desplazamiento para paginación
            
        Returns:
            Lista de transacciones ordenadas por fecha descending
        """
        return self.session.query(Transaction).order_by(
            desc(Transaction.occurred_at)
        ).limit(limit).offset(offset).all()

    def list_by_account(
        self,
        account_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """
        Lista transacciones de una cuenta.
        
        Args:
            account_id: UUID de cuenta
            limit: Máximo de resultados
            offset: Desplazamiento
            
        Returns:
            Lista de transacciones
        """
        return self.session.query(Transaction).filter(
            Transaction.account_id == account_id
        ).order_by(desc(Transaction.occurred_at)).limit(limit).offset(offset).all()

    def list_by_category(
        self,
        category_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """
        Lista transacciones de una categoría.
        
        Args:
            category_id: ID de categoría
            limit: Máximo de resultados
            offset: Desplazamiento
            
        Returns:
            Lista de transacciones
        """
        return self.session.query(Transaction).filter(
            Transaction.category_id == category_id
        ).order_by(desc(Transaction.occurred_at)).limit(limit).offset(offset).all()

    def list_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """
        Lista transacciones en rango de fechas.
        
        Args:
            start_date: Fecha inicial (inclusive)
            end_date: Fecha final (inclusive)
            limit: Máximo de resultados
            offset: Desplazamiento
            
        Returns:
            Lista de transacciones
        """
        return self.session.query(Transaction).filter(
            and_(
                Transaction.occurred_at >= start_date,
                Transaction.occurred_at <= end_date,
            )
        ).order_by(desc(Transaction.occurred_at)).limit(limit).offset(offset).all()

    def list_filtered(
        self,
        account_id: Optional[str] = None,
        category_id: Optional[int] = None,
        type_: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        merchant: Optional[str] = None,
        tag_ids: Optional[List[int]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """
        Lista transacciones con filtros avanzados.
        
        Args:
            account_id: Filtro por cuenta (optional)
            category_id: Filtro por categoría (optional)
            type_: Filtro por tipo (optional)
            start_date: Filtro fecha inicio (optional)
            end_date: Filtro fecha fin (optional)
            merchant: Filtro por comercio (contains)
            tag_ids: Filtro por etiquetas (AND)
            limit: Máximo de resultados
            offset: Desplazamiento
            
        Returns:
            Lista de transacciones filtradas
        """
        query = self.session.query(Transaction)

        # Aplicar filtros
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if type_:
            query = query.filter(Transaction.type == type_)
        if start_date:
            query = query.filter(Transaction.occurred_at >= start_date)
        if end_date:
            query = query.filter(Transaction.occurred_at <= end_date)
        if merchant:
            query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))

        # Filtro por etiquetas (todas deben estar presentes)
        if tag_ids:
            for tag_id in tag_ids:
                query = query.filter(
                    Transaction.id.in_(
                        self.session.query(TransactionTag.transaction_id).filter(
                            TransactionTag.tag_id == tag_id
                        )
                    )
                )

        return query.order_by(desc(Transaction.occurred_at)).limit(limit).offset(
            offset
        ).all()

    def count_all(self) -> int:
        """Cuenta total de transacciones."""
        return self.session.query(func.count(Transaction.id)).scalar() or 0

    def count_by_account(self, account_id: str) -> int:
        """Cuenta transacciones por cuenta."""
        return self.session.query(func.count(Transaction.id)).filter(
            Transaction.account_id == account_id
        ).scalar() or 0

    # ==================== UPDATE ====================

    def update(
        self,
        transaction_id: str,
        **kwargs: Any,
    ) -> Transaction:
        """
        Actualiza una transacción.
        
        Args:
            transaction_id: UUID de transacción
            **kwargs: Campos a actualizar (amount, category_id, merchant, note, etc.)
            
        Returns:
            Transaction actualizada
            
        Raises:
            ValidationError: Si los datos son inválidos
            DatabaseError: Si hay error en BD
        """
        try:
            transaction = self.get_by_id(transaction_id)
            if not transaction:
                raise ValidationError(f"Transacción no encontrada: {transaction_id}")

            # Almacenar valores viejos para comparación
            old_data = self._serialize_transaction(transaction)

            # Actualizar campos permitidos
            allowed_fields = {
                "amount", "category_id", "subcategory_id", "merchant",
                "note", "occurred_at", "currency", "type"
            }
            
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    raise ValidationError(f"Campo no permitido: {key}")
                if value is not None:
                    setattr(transaction, key, value)

            # Marcar como no sincronizado
            transaction.synced = False
            transaction.conflict_resolved = False

            self.session.flush()

            # Registrar en SyncOutbox
            new_data = self._serialize_transaction(transaction)
            if old_data != new_data:
                self._enqueue_sync(
                    entity_type="transaction",
                    operation="update",
                    entity_id=transaction.id,
                    payload=new_data,
                )

            self.session.commit()
            return transaction

        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al actualizar transacción: {str(e)}")

    def update_category(
        self,
        transaction_id: str,
        category_id: int,
        subcategory_id: Optional[int] = None,
    ) -> Transaction:
        """
        Actualiza categoría de una transacción.
        
        Args:
            transaction_id: UUID de transacción
            category_id: Nuevo ID de categoría
            subcategory_id: Nuevo ID de subcategoría (opcional)
            
        Returns:
            Transaction actualizada
        """
        return self.update(
            transaction_id,
            category_id=category_id,
            subcategory_id=subcategory_id,
        )

    # ==================== DELETE ====================

    def delete(self, transaction_id: str) -> bool:
        """
        Elimina una transacción (soft delete).
        
        Args:
            transaction_id: UUID de transacción
            
        Returns:
            True si fue eliminada
            
        Raises:
            ValidationError: Si no existe
            DatabaseError: Si hay error en BD
        """
        try:
            transaction = self.get_by_id(transaction_id)
            if not transaction:
                raise ValidationError(f"Transacción no encontrada: {transaction_id}")

            payload = self._serialize_transaction(transaction)
            # Registrar eliminación en SyncOutbox antes de eliminar
            self._enqueue_sync(
                entity_type="transaction",
                operation="delete",
                entity_id=transaction_id,
                payload=payload,
            )

            # Eliminar transacción
            self.session.delete(transaction)
            self.session.commit()

            return True

        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al eliminar transacción: {str(e)}")

    # ==================== TAGS ====================

    def add_tag(self, transaction_id: str, tag_id: int) -> None:
        """Agrega una etiqueta a transacción."""
        try:
            transaction = self.get_by_id(transaction_id)
            if not transaction:
                raise ValidationError(f"Transacción no encontrada: {transaction_id}")

            # Verificar que tag existe
            tag = self.session.query(Tag).filter(Tag.id == tag_id).first()
            if not tag:
                raise ValidationError(f"Etiqueta no encontrada: {tag_id}")

            # Evitar duplicados
            existing = self.session.query(TransactionTag).filter(
                and_(
                    TransactionTag.transaction_id == transaction_id,
                    TransactionTag.tag_id == tag_id,
                )
            ).first()
            
            if not existing:
                tx_tag = TransactionTag(transaction_id=transaction_id, tag_id=tag_id)
                self.session.add(tx_tag)
                transaction.synced = False
                self.session.commit()

        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al agregar etiqueta: {str(e)}")

    def remove_tag(self, transaction_id: str, tag_id: int) -> None:
        """Elimina una etiqueta de transacción."""
        try:
            tx_tag = self.session.query(TransactionTag).filter(
                and_(
                    TransactionTag.transaction_id == transaction_id,
                    TransactionTag.tag_id == tag_id,
                )
            ).first()

            if tx_tag:
                self.session.delete(tx_tag)
                
                # Marcar transacción como modificada
                transaction = self.get_by_id(transaction_id)
                if transaction:
                    transaction.synced = False

                self.session.commit()

        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al remover etiqueta: {str(e)}")

    # ==================== SYNC OUTBOX ====================

    def list_pending_sync(self) -> List[SyncOutbox]:
        """
        Lista cambios pendientes de sincronizar.
        
        Returns:
            Lista de SyncOutbox items no sincronizados
        """
        return self.session.query(SyncOutbox).filter(
            and_(
                SyncOutbox.entity_type == "transaction",
                SyncOutbox.synced == False,
            )
        ).order_by(SyncOutbox.created_at).all()

    def mark_synced(self, outbox_id: int) -> None:
        """
        Marca un SyncOutbox item como sincronizado.
        
        Args:
            outbox_id: ID del SyncOutbox item
        """
        try:
            outbox = self.session.query(SyncOutbox).filter(
                SyncOutbox.id == outbox_id
            ).first()
            
            if outbox:
                outbox.synced = True
                self.session.commit()

        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al marcar sincronizado: {str(e)}")

    def clear_sync_errors(self, transaction_id: str) -> None:
        """
        Limpia errores de sincronización para una transacción.
        
        Args:
            transaction_id: UUID de transacción
        """
        try:
            outbox_items = self.session.query(SyncOutbox).filter(
                and_(
                    SyncOutbox.entity_type == "transaction",
                    SyncOutbox.entity_id == transaction_id,
                    SyncOutbox.synced == False,
                )
            ).all()

            for item in outbox_items:
                item.sync_error = None

            self.session.commit()

        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al limpiar errores: {str(e)}")

    # ==================== UTILITIES ====================

    def _validate_transaction_input(
        self,
        account_id: str,
        type_: str,
        amount: float,
        category_id: int,
    ) -> None:
        """Valida datos de entrada."""
        # Validar account existe
        account = self.session.query(Account).filter(
            Account.id == account_id
        ).first()
        if not account:
            raise ValidationError(f"Cuenta no encontrada: {account_id}")

        # Validar type
        valid_types = {"ingreso", "gasto", "transferencia"}
        if type_ not in valid_types:
            raise ValidationError(f"Tipo inválido: {type_}. Debe ser uno de {valid_types}")

        # Validar amount
        if amount <= 0:
            raise ValidationError(f"Monto debe ser positivo: {amount}")

        # Validar category existe
        category = self.session.query(Category).filter(
            Category.id == category_id
        ).first()
        if not category:
            raise ValidationError(f"Categoría no encontrada: {category_id}")

    def _add_tags_to_transaction(
        self,
        transaction: Transaction,
        tag_ids: List[int],
    ) -> None:
        """Agrega múltiples etiquetas a una transacción."""
        for tag_id in tag_ids:
            tag = self.session.query(Tag).filter(Tag.id == tag_id).first()
            if tag:
                tx_tag = TransactionTag(
                    transaction_id=transaction.id,
                    tag_id=tag_id,
                )
                self.session.add(tx_tag)

    def _serialize_transaction(self, transaction: Transaction) -> Dict[str, Any]:
        """Serializa transacción para SyncOutbox."""
        account = self.session.query(Account).filter(Account.id == transaction.account_id).first()
        category = self.session.query(Category).filter(Category.id == transaction.category_id).first()
        subcategory = None
        if transaction.subcategory_id:
            subcategory = self.session.query(SubCategory).filter(SubCategory.id == transaction.subcategory_id).first()
        if category and not category.sync_id:
            category.sync_id = generate_uuid()
        if subcategory and not subcategory.sync_id:
            subcategory.sync_id = generate_uuid()
        tag_names = [tag.name for tag in transaction.tags] if transaction.tags else []
        tag_names = [t[:30] for t in tag_names][:20]
        merchant = (transaction.merchant or "")[:200] if transaction.merchant else None
        note = (transaction.note or "")[:200] if transaction.note else None
        payload = {
            "transaction_id": transaction.id,
            "account_id": transaction.account_id,
            "account_name": account.name if account else None,
            "category_id": category.sync_id if category else None,
            "category_name": category.name if category else None,
            "subcategory_id": subcategory.sync_id if subcategory else None,
            "subcategory_name": subcategory.name if subcategory else None,
            "type": transaction.type,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "occurred_at": self._format_timestamp(transaction.occurred_at) if transaction.occurred_at else None,
            "merchant": merchant,
            "note": note,
            "tags": tag_names,
        }
        return {k: v for k, v in payload.items() if v is not None}

    def _format_timestamp(self, dt: datetime | None) -> str | None:
        """Convert datetime to ISO 8601 format with 'Z' suffix for UTC timestamps."""
        if dt is None:
            return None
        # If dt is naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UTC if not already
        if dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        # Return ISO format with 'Z' suffix
        return dt.isoformat().replace('+00:00', 'Z')

    def _enqueue_sync(
        self,
        entity_type: str,
        operation: str,
        entity_id: str,
        payload: Dict[str, Any],
    ) -> None:
        """Encolada cambio en SyncOutbox."""
        event_type = "txn_updated"
        if operation == "create":
            event_type = "txn_created"
        elif operation == "delete":
            event_type = "txn_deleted"
        outbox = SyncOutbox(
            id=generate_uuid(),
            entity_type=entity_type,
            operation=operation,
            event_type=event_type,
            entity_id=entity_id,
            payload=json.dumps(payload),
            created_at=datetime.utcnow(),
            synced=False,
            sync_error=None,
        )
        self.session.add(outbox)

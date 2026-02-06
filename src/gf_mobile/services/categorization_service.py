"""
CategorizationService: Categorización automática de transacciones basada en ML simple
"""

import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from gf_mobile.persistence.models import (
    Transaction,
    Category,
    SubCategory,
    CategorizationRule,
    SyncOutbox,
    generate_uuid,
)


class CategorizationService:
    """
    Aprende reglas de categorización de transacciones basándose en:
    - Nombre del comercio (merchant)
    - Patrones históricos
    - Reglas explícitas definidas por el usuario
    
    Patrón: Rule-based + learning (confidence score)
    """

    def __init__(self, session: Session):
        self.session = session

    def categorize_transaction(
        self,
        merchant: str,
        amount: float,
        category_id: Optional[int] = None,
    ) -> Tuple[int, float]:
        """
        Categoriza una transacción por merchant.
        Retorna (category_id, confidence).
        
        Si category_id es proporcionado, aprende de ello.
        """
        if not merchant or not isinstance(merchant, str):
            raise ValueError("merchant must be non-empty string")

        # Buscar regla existente
        rule = (
            self.session.query(CategorizationRule)
            .filter(CategorizationRule.merchant_keyword == merchant.lower())
            .first()
        )

        if rule:
            return rule.category_id, rule.confidence

        # Si no hay regla, usar histórico
        if category_id is None:
            category_id, confidence = self._predict_from_history(merchant, amount)
        else:
            # Usuario especificó categoría - crear/actualizar regla
            if rule:
                rule.confidence = min(rule.confidence + 0.1, 1.0)  # Aumentar confianza
            else:
                rule = CategorizationRule(
                    merchant_keyword=merchant.lower(),
                    category_id=category_id,
                    confidence=0.7,  # Confianza inicial para regla creada por usuario
                    user_defined=True,
                    created_at=datetime.now(timezone.utc),
                )
                self.session.add(rule)
            self.session.flush()
            confidence = rule.confidence

        return category_id or 1, confidence  # Default a categoría 1 si no hay sugerencia

    def learn_from_transaction(
        self,
        transaction_id: str,
        merchant: str,
        category_id: int,
    ) -> CategorizationRule:
        """Aprende una regla a partir de una transacción categorizada por el usuario."""
        if not merchant or not isinstance(merchant, str):
            raise ValueError("merchant must be non-empty string")

        # Buscar o crear regla
        rule = (
            self.session.query(CategorizationRule)
            .filter(CategorizationRule.merchant_keyword == merchant.lower())
            .first()
        )

        is_new = rule is None
        if rule:
            # Aumentar confianza (máx 0.95 para evitar sobre-confianza)
            rule.confidence = min(rule.confidence + 0.05, 0.95)
            rule.updated_at = datetime.now(timezone.utc)
        else:
            rule = CategorizationRule(
                merchant_keyword=merchant.lower(),
                category_id=category_id,
                confidence=0.6,  # Confianza inicial desde aprendizaje
                user_defined=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.session.add(rule)

        self.session.flush()
        self._enqueue_sync(
            rule_id=rule.id,
            operation="create" if is_new else "update",
            payload=self._serialize_rule(rule),
        )
        self.session.commit()
        return rule

    def get_category_suggestion(
        self,
        merchant: str,
        amount: float,
    ) -> Optional[Dict[str, Any]]:
        """Obtiene una sugerencia de categoría para un merchant dado."""
        rule = (
            self.session.query(CategorizationRule)
            .filter(CategorizationRule.merchant_keyword == merchant.lower())
            .first()
        )

        if rule:
            category = self.session.query(Category).filter(Category.id == rule.category_id).first()
            return {
                "category_id": rule.category_id,
                "category_name": category.name if category else None,
                "confidence": rule.confidence,
                "user_defined": rule.user_defined,
            }

        return None

    def get_rules_by_category(self, category_id: int) -> List[CategorizationRule]:
        """Obtiene todas las reglas para una categoría dada."""
        return (
            self.session.query(CategorizationRule)
            .filter(CategorizationRule.category_id == category_id)
            .order_by(CategorizationRule.confidence.desc())
            .all()
        )

    def delete_rule(self, rule_id: str) -> bool:
        """Elimina una regla de categorización."""
        rule = (
            self.session.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
        )
        if not rule:
            return False

        self.session.delete(rule)
        self.session.flush()

        self._enqueue_sync(
            rule_id=rule_id,
            operation="delete",
            payload={"id": rule_id},
        )
        self.session.commit()
        return True

    def update_rule_confidence(self, rule_id: str, confidence: float) -> CategorizationRule:
        """Actualiza la confianza de una regla."""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        rule = (
            self.session.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
        )
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")

        rule.confidence = confidence
        rule.updated_at = datetime.now(timezone.utc)
        self.session.flush()

        self._enqueue_sync(
            rule_id=rule.id,
            operation="update",
            payload=self._serialize_rule(rule),
        )
        self.session.commit()
        return rule

    def list_pending_sync(self) -> List[Dict[str, Any]]:
        """Retorna reglas pendientes de sincronización."""
        outbox_items = (
            self.session.query(SyncOutbox)
            .filter(
                and_(
                    SyncOutbox.entity_type == "categorization_rule",
                    SyncOutbox.synced == False,
                )
            )
            .all()
        )
        return [
            {
                "id": item.id,
                "entity_id": item.entity_id,
                "operation": item.operation,
                "payload": item.payload,
                "sync_error": item.sync_error,
            }
            for item in outbox_items
        ]

    def mark_synced(self, outbox_id: int) -> None:
        """Marca un elemento del outbox como sincronizado."""
        outbox = self.session.query(SyncOutbox).filter(SyncOutbox.id == outbox_id).first()
        if outbox:
            outbox.synced = True
            outbox.sync_error = None
            self.session.commit()

    # ==================== Métodos privados ====================

    def _predict_from_history(self, merchant: str, amount: float) -> Tuple[int, float]:
        """Predice categoría a partir del histórico de transacciones similares."""
        # Buscar transacciones con merchant similar (fuzzy match simplificado)
        similar_keyword = f"%{merchant.lower()[:5]}%"  # Primeros 5 caracteres
        similar_txs = (
            self.session.query(Transaction.category_id, func.count(Transaction.id))
            .filter(Transaction.merchant.ilike(similar_keyword))
            .group_by(Transaction.category_id)
            .order_by(func.count(Transaction.id).desc())
            .limit(1)
            .all()
        )

        if similar_txs and similar_txs[0][0] is not None:
            return similar_txs[0][0], 0.4  # Confianza baja (histórico)

        return 1, 0.0  # Sin predicción

    def _serialize_rule(self, rule: CategorizationRule) -> Dict[str, Any]:
        """Serializa una regla para SyncOutbox."""
        return {
            "id": rule.id,
            "merchant_keyword": rule.merchant_keyword,
            "category_id": rule.category_id,
            "confidence": rule.confidence,
            "user_defined": rule.user_defined,
            "created_at": self._format_timestamp(rule.created_at),
            "updated_at": self._format_timestamp(rule.updated_at),
        }

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
        self, rule_id: str, operation: str, payload: Dict[str, Any]
    ) -> None:
        """Encola un cambio de regla para sincronización."""
        outbox = SyncOutbox(
            id=generate_uuid(),
            entity_type="categorization_rule",
            entity_id=rule_id,
            operation=operation,
            payload=json.dumps(payload),
            synced=False,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(outbox)

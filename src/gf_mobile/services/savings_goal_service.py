"""
SavingsGoalService: Gestión de objetivos de ahorro
"""

import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from gf_mobile.persistence.models import SavingsGoal, SyncOutbox, generate_uuid


class SavingsGoalService:
    """
    Gestiona objetivos de ahorro con seguimiento de progreso e hitos.
    
    Patrón: Valida entrada → crea/actualiza ORM → flush() → enqueue SyncOutbox → commit()
    """

    def __init__(self, session: Session):
        self.session = session

    def create_goal(
        self,
        user_id: int,
        name: str,
        target_amount: float,
        current_amount: float = 0.0,
        deadline: Optional[datetime] = None,
        category_id: Optional[int] = None,
    ) -> SavingsGoal:
        """Crea un nuevo objetivo de ahorro."""
        self._validate_input(name, target_amount, current_amount)

        # Auto-marcar como logrado si current >= target
        achieved = current_amount >= target_amount

        goal = SavingsGoal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            deadline=deadline,
            category_id=category_id,
            achieved=achieved,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(goal)
        self.session.flush()

        self._enqueue_sync(
            goal_id=goal.id,
            operation="create",
            payload=self._serialize_goal(goal),
        )
        self.session.commit()
        return goal

    def update_goal(
        self,
        goal_id: str,
        name: Optional[str] = None,
        target_amount: Optional[float] = None,
        current_amount: Optional[float] = None,
        deadline: Optional[datetime] = None,
        achieved: Optional[bool] = None,
    ) -> SavingsGoal:
        """Actualiza un objetivo de ahorro."""
        goal = self.session.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        updated = False
        if name is not None:
            goal.name = name
            updated = True
        if target_amount is not None:
            if target_amount <= 0:
                raise ValueError("target_amount must be > 0")
            goal.target_amount = target_amount
            updated = True
        if current_amount is not None:
            if current_amount < 0:
                raise ValueError("current_amount cannot be negative")
            goal.current_amount = current_amount
            # Auto-marcar como logrado si se alcanza el objetivo
            if current_amount >= goal.target_amount:
                goal.achieved = True
            updated = True
        if deadline is not None:
            goal.deadline = deadline
            updated = True
        if achieved is not None:
            goal.achieved = achieved
            updated = True

        if updated:
            goal.updated_at = datetime.now(timezone.utc)
            self.session.flush()

            self._enqueue_sync(
                goal_id=goal.id,
                operation="update",
                payload=self._serialize_goal(goal),
            )
            self.session.commit()

        return goal

    def delete_goal(self, goal_id: str) -> bool:
        """Elimina un objetivo de ahorro."""
        goal = self.session.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
        if not goal:
            return False

        self.session.delete(goal)
        self.session.flush()

        self._enqueue_sync(
            goal_id=goal_id,
            operation="delete",
            payload={"id": goal_id},
        )
        self.session.commit()
        return True

    def get_goal(self, goal_id: str) -> Optional[SavingsGoal]:
        """Obtiene un objetivo por ID."""
        return self.session.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()

    def list_goals(self, achieved: Optional[bool] = None, limit: int = 100) -> List[SavingsGoal]:
        """Lista objetivos, opcionalmente filtrados por estado logrado."""
        query = self.session.query(SavingsGoal)
        if achieved is not None:
            query = query.filter(SavingsGoal.achieved == achieved)
        return query.limit(limit).all()

    def get_progress(self, goal_id: str) -> Dict[str, Any]:
        """Retorna el progreso de un objetivo (porcentaje, monto faltante, etc)."""
        goal = self.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        percentage = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        remaining = max(0, goal.target_amount - goal.current_amount)

        return {
            "goal_id": goal.id,
            "name": goal.name,
            "current": goal.current_amount,
            "target": goal.target_amount,
            "percentage": round(percentage, 2),
            "remaining": round(remaining, 2),
            "achieved": goal.achieved,
            "deadline": goal.deadline.isoformat() if goal.deadline else None,
        }

    def add_contribution(self, goal_id: str, amount: float) -> SavingsGoal:
        """Suma una contribución al objetivo y actualiza estado."""
        if amount <= 0:
            raise ValueError("Contribution amount must be > 0")

        goal = self.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.achieved = True

            goal.updated_at = datetime.now(timezone.utc)
        self.session.flush()

        self._enqueue_sync(
            goal_id=goal.id,
            operation="update",
            payload=self._serialize_goal(goal),
        )
        self.session.commit()
        return goal

    def list_pending_sync(self) -> List[Dict[str, Any]]:
        """Retorna objetivos pendientes de sincronización."""
        outbox_items = (
            self.session.query(SyncOutbox)
            .filter(
                and_(
                    SyncOutbox.entity_type == "savings_goal",
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

    def _validate_input(self, name: str, target_amount: float, current_amount: float) -> None:
        """Valida parámetros de entrada."""
        if not name or not isinstance(name, str):
            raise ValueError("name must be non-empty string")

        if not isinstance(target_amount, (int, float)) or target_amount <= 0:
            raise ValueError("target_amount must be numeric and > 0")

        if not isinstance(current_amount, (int, float)) or current_amount < 0:
            raise ValueError("current_amount must be numeric and >= 0")

    def _serialize_goal(self, goal: SavingsGoal) -> Dict[str, Any]:
        """Serializa un objetivo para SyncOutbox."""
        return {
            "id": goal.id,
            "name": goal.name,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "deadline": goal.deadline.isoformat() if goal.deadline else None,
            "category_id": goal.category_id,
            "achieved": goal.achieved,
            "created_at": goal.created_at.isoformat() if goal.created_at else None,
            "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
            "server_id": goal.server_id,
        }

    def _enqueue_sync(
        self, goal_id: str, operation: str, payload: Dict[str, Any]
    ) -> None:
        """Encola un cambio de objetivo para sincronización."""
        outbox = SyncOutbox(
            id=generate_uuid(),
            entity_type="savings_goal",
            entity_id=goal_id,
            operation=operation,
            payload=json.dumps(payload),
            synced=False,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(outbox)

"""
Modelos SQLAlchemy para GestionFondos Mobile
Sincronizados con el desktop pero con UUIDs en lugar de auto-increment IDs
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

try:
    # SQLAlchemy >=1.4 (incluye 2.x)
    from sqlalchemy.orm import declarative_base
except ImportError:
    # Compatibilidad defensiva para builds móviles con SQLAlchemy 1.3.x
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


def generate_uuid() -> str:
    """Generar UUID v4 como string"""
    return str(uuid.uuid4())


class User(Base):
    """Usuario de la aplicación (typically single user per device)"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    server_uid = Column(String(255), unique=True, nullable=True)  # Firebase UID
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name}>"


class Account(Base):
    """Cuenta bancaria, tarjeta, etc."""

    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # checking, savings, credit_card, cash
    currency = Column(String(3), nullable=False, default="USD")
    opening_balance = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Sync fields
    synced = Column(Boolean, default=False)
    server_id = Column(String(255), nullable=True)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_accounts_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name} type={self.type}>"


class Category(Base):
    """Categoría de gasto (sistema, compartidas)"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    sync_id = Column(String(36), nullable=True, unique=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    budget_group = Column(String(50), nullable=False)  # Necesidades, Ocio, Ahorro, Otros
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    subcategories = relationship(
        "SubCategory", back_populates="category", cascade="all, delete-orphan"
    )
    transactions = relationship("Transaction", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name}>"


class SubCategory(Base):
    """Subcategoría"""

    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True)
    sync_id = Column(String(36), nullable=True, unique=True, default=generate_uuid)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    category = relationship("Category", back_populates="subcategories")
    transactions = relationship("Transaction", back_populates="subcategory")

    __table_args__ = (UniqueConstraint("category_id", "name", name="uq_subcategory"),)

    def __repr__(self) -> str:
        return f"<SubCategory id={self.id} name={self.name}>"


class Transaction(Base):
    """Transacción de gasto, ingreso o transferencia"""

    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=True)
    recurring_id = Column(Integer, ForeignKey("recurring_transactions.id"), nullable=True)

    type = Column(String(20), nullable=False)  # ingreso, gasto, transferencia
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    occurred_at = Column(DateTime, nullable=False)
    merchant = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # PFM fields
    merchant_raw = Column(String(255), nullable=True)
    merchant_normalized = Column(String(255), nullable=True)
    needs_review = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)
    external_hash = Column(String(255), nullable=True)
    is_duplicate_candidate = Column(Boolean, default=False)

    # Sync fields
    synced = Column(Boolean, default=False)
    conflict_resolved = Column(Boolean, default=False)
    server_id = Column(String(255), nullable=True)

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    subcategory = relationship("SubCategory", back_populates="transactions")
    recurring = relationship("RecurringTransaction", back_populates="transactions")
    tags = relationship(
        "Tag", secondary="transaction_tags", back_populates="transactions", cascade="all"
    )

    __table_args__ = (
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_category_id", "category_id"),
        Index("ix_transactions_occurred_at", "occurred_at"),
    )

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} amount={self.amount} type={self.type}>"


class RecurringTransaction(Base):
    """Transacción recurrente (semanal, mensual, anual)"""

    __tablename__ = "recurring_transactions"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)

    frequency = Column(String(50), nullable=False)  # weekly, monthly, monthly:2, annual
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    auto_generate = Column(Boolean, default=False)
    next_run = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Sync fields
    synced = Column(Boolean, default=False)
    server_id = Column(String(255), nullable=True)

    category = relationship("Category")
    subcategory = relationship("SubCategory")
    account = relationship("Account")
    transactions = relationship("Transaction", back_populates="recurring")

    __table_args__ = (Index("ix_recurring_next_run", "next_run"),)

    def __repr__(self) -> str:
        return f"<RecurringTransaction id={self.id} name={self.name} freq={self.frequency}>"


class Tag(Base):
    """Etiqueta para transacciones"""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)

    transactions = relationship("Transaction", secondary="transaction_tags", back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name}>"

class TransactionTag(Base):
    """Clase ORM para tabla association transaction_tags"""

    __tablename__ = "transaction_tags"

    transaction_id = Column(String(36), ForeignKey("transactions.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    def __repr__(self) -> str:
        return f"<TransactionTag txn={self.transaction_id} tag={self.tag_id}>"


class Budget(Base):
    """Presupuesto por categoría por mes"""

    __tablename__ = "budgets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    month = Column(String(7), nullable=False)  # YYYY-MM
    amount = Column(Float, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Sync fields
    synced = Column(Boolean, default=False)
    server_id = Column(String(255), nullable=True)

    category = relationship("Category")

    __table_args__ = (UniqueConstraint("category_id", "month", name="uq_budget_cat_month"),)

    def __repr__(self) -> str:
        return f"<Budget id={self.id} category={self.category_id} month={self.month}>"


class SyncOutbox(Base):
    """Cola local de cambios pendientes de sincronizar"""

    __tablename__ = "sync_outbox"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(50), nullable=True)  # legacy
    operation = Column(String(20), nullable=True)  # legacy
    event_type = Column(String(32), nullable=True)
    entity_id = Column(String(255), nullable=False)
    payload = Column(Text, nullable=False)  # JSON del objeto

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    synced = Column(Boolean, default=False)
    sync_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    next_attempt_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    __table_args__ = (Index("ix_sync_outbox_synced", "synced"),)

    def __repr__(self) -> str:
        return f"<SyncOutbox id={self.id} op={self.operation} entity={self.entity_type}>"


class SyncState(Base):
    """Estado de sincronización (key-value store)"""

    __tablename__ = "sync_state"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<SyncState {self.key}={self.value}>"


class AppliedEvent(Base):
    """Eventos ya aplicados (idempotencia)"""

    __tablename__ = "applied_events"

    event_id = Column(String(128), primary_key=True)
    applied_at = Column(DateTime, nullable=False, default=datetime.now)


class Alert(Base):
    """Alerta de gastos, presupuestos, anomalías"""

    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    alert_type = Column(String(50), nullable=False)  # duplicate, anomaly, budget, recurring, overdraft
    severity = Column(String(20), nullable=False)  # info, warning, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)

    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    amount = Column(Float, nullable=True)

    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    action_taken = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    expires_at = Column(DateTime, nullable=True)

    # Sync fields
    synced = Column(Boolean, default=False)
    server_id = Column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_alerts_is_read", "is_read"),
        Index("ix_alerts_is_dismissed", "is_dismissed"),
    )

    def __repr__(self) -> str:
        return f"<Alert id={self.id} type={self.alert_type}>"


class SavingsGoal(Base):
    """Meta de ahorro personal"""

    __tablename__ = "savings_goals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)  # Monto actual ahorrado
    deadline = Column(DateTime, nullable=True)  # Fecha límite objetivo
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    achieved = Column(Boolean, default=False)  # Flag si se logró el objetivo
    description = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Sync fields
    synced = Column(Boolean, default=False)
    server_id = Column(String(255), nullable=True)

    transactions = relationship("SavingsTransaction", back_populates="goal", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SavingsGoal id={self.id} name={self.name}>"

    @property
    def progress_percent(self) -> float:
        """Porcentaje de progreso hacia meta"""
        if self.target_amount <= 0:
            return 0.0
        return min((self.current_amount / self.target_amount) * 100, 100.0)


class SavingsTransaction(Base):
    """Transacción dentro de una meta de ahorro"""

    __tablename__ = "savings_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    savings_goal_id = Column(String(36), ForeignKey("savings_goals.id"), nullable=False)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    amount = Column(Float, nullable=False)  # Positivo o negativo
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now)

    # Sync fields
    synced = Column(Boolean, default=False)
    server_id = Column(String(255), nullable=True)

    goal = relationship("SavingsGoal", back_populates="transactions")
    transaction = relationship("Transaction")

    def __repr__(self) -> str:
        return f"<SavingsTransaction id={self.id} amount={self.amount}>"


class Setting(Base):
    """Configuración de la app (key-value)"""

    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<Setting {self.key}={self.value}>"


class HealthScore(Base):
    """Puntuación de salud financiera"""

    __tablename__ = "health_scores"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)  # 0-900
    income_stability_score = Column(Integer, nullable=True)  # 0-180
    savings_ratio_score = Column(Integer, nullable=True)
    liquidity_score = Column(Integer, nullable=True)
    incidents_score = Column(Integer, nullable=True)
    expense_flexibility_score = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)  # JSON con detalles

    calculated_at = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self) -> str:
        return f"<HealthScore score={self.score}>"


class CategorizationRule(Base):
    """Regla de categorización automática basada en keywords de merchant"""

    __tablename__ = "categorization_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_keyword = Column(String(255), nullable=False, unique=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    confidence = Column(Float, default=0.5)  # 0.0 a 1.0
    user_defined = Column(Boolean, default=False)  # True si fue definido por usuario

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<CategorizationRule keyword={self.merchant_keyword} confidence={self.confidence}>"

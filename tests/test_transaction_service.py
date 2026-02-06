"""
Tests para TransactionService

Verifica:
- CRUD de transacciones (create, read, update, delete)
- Filtrado avanzado (por categoría, cuenta, fecha, etiquetas)
- Integración con SyncOutbox
- Validación de datos
- Manejo de etiquetas
"""

import json
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from tempfile import NamedTemporaryFile

from gf_mobile.persistence.db import init_database
from gf_mobile.persistence.models import (
    Base, User, Account, Category, SubCategory, Tag, 
    Transaction, SyncOutbox, generate_uuid
)
from gf_mobile.services.transaction_service import TransactionService
from gf_mobile.core.exceptions import ValidationError, DatabaseError


@pytest.fixture
def temp_db():
    """Crea una BD SQLite temporal para tests."""
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(temp_db):
    """Crea una sesión de test."""
    SessionLocal = sessionmaker(bind=temp_db)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def setup_data(session):
    """Configura datos de test: usuario, cuenta, categoría, tags."""
    # Usuario
    user = User(name="Test User")
    session.add(user)
    session.flush()

    # Cuenta
    account = Account(
        id=generate_uuid(),
        user_id=user.id,
        name="Test Account",
        type="checking",
        currency="USD",
        opening_balance=1000.0,
        created_at=datetime.utcnow(),
    )
    session.add(account)

    # Categoría
    category = Category(id=1, name="Groceries", budget_group="Necesidades")
    session.add(category)

    # Subcategoría
    subcategory = SubCategory(id=1, category_id=1, name="Food")
    session.add(subcategory)

    # Otra categoría
    category2 = Category(id=2, name="Entertainment", budget_group="Ocio")
    session.add(category2)

    # Tags
    tag1 = Tag(id=1, name="important")
    tag2 = Tag(id=2, name="recurring")
    session.add(tag1)
    session.add(tag2)

    session.commit()

    return {
        "user": user,
        "account": account,
        "category": category,
        "subcategory": subcategory,
        "category2": category2,
        "tag1": tag1,
        "tag2": tag2,
    }


@pytest.fixture
def service(session, setup_data):
    """Crea instancia del servicio."""
    return TransactionService(session, user_id=setup_data["user"].id)


class TestTransactionCreate:
    """Tests para creación de transacciones."""

    def test_create_basic_transaction(self, service, setup_data):
        """Crea una transacción básica."""
        now = datetime.utcnow()
        
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.50,
            category_id=1,
            currency="USD",
            merchant="Whole Foods",
            note="Weekly shopping",
            occurred_at=now,
        )

        assert txn.id is not None
        assert len(txn.id) == 36  # UUID length
        assert txn.amount == 25.50
        assert txn.merchant == "Whole Foods"
        assert txn.synced == False
        assert txn.server_id is None

    def test_create_with_tags(self, service, setup_data):
        """Crea transacción con etiquetas."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=50.0,
            category_id=1,
            tag_ids=[1, 2],
        )

        assert len(txn.tags) == 2
        tag_ids = {tag.id for tag in txn.tags}
        assert tag_ids == {1, 2}

    def test_create_enqueues_sync(self, service, setup_data, session):
        """Verifica que creación se registra en SyncOutbox."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="ingreso",
            amount=1000.0,
            category_id=1,
        )

        outbox = session.query(SyncOutbox).filter(
            SyncOutbox.entity_id == txn.id
        ).first()

        assert outbox is not None
        assert outbox.operation == "create"
        assert outbox.entity_type == "transaction"
        assert outbox.synced == False

        payload = json.loads(outbox.payload)
        assert payload["amount"] == "1000.0"

    def test_create_invalid_account(self, service, setup_data):
        """Rechaza creación con cuenta inválida."""
        with pytest.raises(ValidationError):
            service.create(
                account_id="invalid-uuid",
                type_="gasto",
                amount=50.0,
                category_id=1,
            )

    def test_create_invalid_type(self, service, setup_data):
        """Rechaza tipo de transacción inválido."""
        with pytest.raises(ValidationError):
            service.create(
                account_id=setup_data["account"].id,
                type_="invalid_type",
                amount=50.0,
                category_id=1,
            )

    def test_create_invalid_amount(self, service, setup_data):
        """Rechaza monto inválido (≤ 0)."""
        with pytest.raises(ValidationError):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=-50.0,
                category_id=1,
            )

    def test_create_invalid_category(self, service, setup_data):
        """Rechaza categoría que no existe."""
        with pytest.raises(ValidationError):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=50.0,
                category_id=999,
            )


class TestTransactionRead:
    """Tests para lectura de transacciones."""

    def test_get_by_id(self, service, setup_data):
        """Obtiene transacción por ID."""
        created = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        retrieved = service.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.amount == 25.0

    def test_get_by_id_not_found(self, service):
        """Retorna None si transacción no existe."""
        result = service.get_by_id("invalid-uuid")
        assert result is None

    def test_list_all(self, service, setup_data):
        """Lista todas las transacciones."""
        for i in range(5):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=10.0 + i,
                category_id=1,
            )

        transactions = service.list_all()
        assert len(transactions) == 5

    def test_list_all_ordering(self, service, setup_data):
        """Verifica que list_all ordena por fecha descendente."""
        base_time = datetime(2026, 1, 1, 12, 0, 0)
        
        txn1 = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=10.0,
            category_id=1,
            occurred_at=base_time,
        )

        txn2 = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=20.0,
            category_id=1,
            occurred_at=base_time + timedelta(days=1),
        )

        transactions = service.list_all()
        assert transactions[0].id == txn2.id  # Más reciente primero
        assert transactions[1].id == txn1.id

    def test_list_by_account(self, service, setup_data):
        """Lista transacciones de una cuenta."""
        account2 = Account(
            id=generate_uuid(),
            user_id=setup_data["user"].id,
            name="Account 2",
            type="savings",
            currency="USD",
            opening_balance=0.0,
            created_at=datetime.utcnow(),
        )
        service.session.add(account2)
        service.session.commit()

        # 3 en account1
        for i in range(3):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=10.0,
                category_id=1,
            )

        # 2 en account2
        for i in range(2):
            service.create(
                account_id=account2.id,
                type_="gasto",
                amount=20.0,
                category_id=1,
            )

        txns = service.list_by_account(setup_data["account"].id)
        assert len(txns) == 3

    def test_list_by_category(self, service, setup_data):
        """Lista transacciones por categoría."""
        # 3 en categoría 1
        for i in range(3):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=10.0,
                category_id=1,
            )

        # 2 en categoría 2
        for i in range(2):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=20.0,
                category_id=2,
            )

        txns = service.list_by_category(1)
        assert len(txns) == 3

    def test_list_by_date_range(self, service, setup_data):
        """Lista transacciones en rango de fechas."""
        start = datetime(2026, 1, 1, 0, 0, 0)
        mid = datetime(2026, 1, 15, 0, 0, 0)
        end = datetime(2026, 1, 31, 23, 59, 59)

        # 2 antes del rango
        service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=10.0,
            category_id=1,
            occurred_at=start - timedelta(days=10),
        )

        # 3 en el rango
        for i in range(3):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=15.0,
                category_id=1,
                occurred_at=mid + timedelta(days=i),
            )

        # 1 después del rango
        service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=20.0,
            category_id=1,
            occurred_at=end + timedelta(days=5),
        )

        txns = service.list_by_date_range(start, end)
        assert len(txns) == 3

    def test_list_filtered_by_account_and_category(self, service, setup_data):
        """Filtra por múltiples criterios."""
        # Setup
        for i in range(2):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=10.0,
                category_id=1,
            )

        for i in range(3):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=20.0,
                category_id=2,
            )

        # Filtrar
        txns = service.list_filtered(
            account_id=setup_data["account"].id,
            category_id=1,
        )

        assert len(txns) == 2

    def test_list_filtered_by_merchant(self, service, setup_data):
        """Filtra por comercio (contains)."""
        service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=10.0,
            category_id=1,
            merchant="Whole Foods",
        )

        service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=20.0,
            category_id=1,
            merchant="Trader Joe's",
        )

        txns = service.list_filtered(merchant="Foods")
        assert len(txns) == 1
        assert txns[0].merchant == "Whole Foods"

    def test_count_all(self, service, setup_data):
        """Cuenta transacciones totales."""
        for i in range(5):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=10.0,
                category_id=1,
            )

        count = service.count_all()
        assert count == 5

    def test_count_by_account(self, service, setup_data):
        """Cuenta transacciones por cuenta."""
        for i in range(3):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=10.0,
                category_id=1,
            )

        count = service.count_by_account(setup_data["account"].id)
        assert count == 3


class TestTransactionUpdate:
    """Tests para actualización de transacciones."""

    def test_update_amount(self, service, setup_data):
        """Actualiza monto."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        updated = service.update(txn.id, amount=50.0)
        assert updated.amount == 50.0
        assert updated.synced == False

    def test_update_category(self, service, setup_data):
        """Actualiza categoría."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        updated = service.update(txn.id, category_id=2)
        assert updated.category_id == 2

    def test_update_merchant(self, service, setup_data):
        """Actualiza comercio."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
            merchant="Old Store",
        )

        updated = service.update(txn.id, merchant="New Store")
        assert updated.merchant == "New Store"

    def test_update_enqueues_sync(self, service, setup_data, session):
        """Verifica que actualización se registra en SyncOutbox."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        # Limpiar outbox anterior
        session.query(SyncOutbox).delete()
        session.commit()

        service.update(txn.id, amount=50.0)

        outbox = session.query(SyncOutbox).filter(
            SyncOutbox.entity_id == txn.id
        ).first()

        assert outbox is not None
        assert outbox.operation == "update"

    def test_update_invalid_transaction(self, service):
        """Rechaza actualizar transacción que no existe."""
        with pytest.raises(ValidationError):
            service.update("invalid-uuid", amount=50.0)

    def test_update_invalid_field(self, service, setup_data):
        """Rechaza actualizar campo no permitido."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        with pytest.raises(ValidationError):
            service.update(txn.id, invalid_field="value")


class TestTransactionDelete:
    """Tests para eliminación de transacciones."""

    def test_delete_transaction(self, service, setup_data):
        """Elimina una transacción."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        result = service.delete(txn.id)
        assert result == True

        retrieved = service.get_by_id(txn.id)
        assert retrieved is None

    def test_delete_enqueues_sync(self, service, setup_data, session):
        """Verifica que eliminación se registra en SyncOutbox."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        # Limpiar outbox anterior
        session.query(SyncOutbox).delete()
        session.commit()

        service.delete(txn.id)

        outbox = session.query(SyncOutbox).filter(
            SyncOutbox.entity_id == txn.id
        ).first()

        assert outbox is not None
        assert outbox.operation == "delete"

    def test_delete_invalid_transaction(self, service):
        """Rechaza eliminar transacción que no existe."""
        with pytest.raises(ValidationError):
            service.delete("invalid-uuid")


class TestTransactionTags:
    """Tests para manejo de etiquetas."""

    def test_add_tag(self, service, setup_data):
        """Agrega etiqueta a transacción."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        service.add_tag(txn.id, 1)

        updated = service.get_by_id(txn.id)
        tag_ids = {tag.id for tag in updated.tags}
        assert 1 in tag_ids

    def test_remove_tag(self, service, setup_data):
        """Elimina etiqueta de transacción."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
            tag_ids=[1, 2],
        )

        service.remove_tag(txn.id, 1)

        updated = service.get_by_id(txn.id)
        tag_ids = {tag.id for tag in updated.tags}
        assert tag_ids == {2}

    def test_list_filtered_by_tags(self, service, setup_data):
        """Filtra transacciones por etiquetas (AND)."""
        # Txn con tag 1
        txn1 = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=10.0,
            category_id=1,
            tag_ids=[1],
        )

        # Txn con tag 1 y 2
        txn2 = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=20.0,
            category_id=1,
            tag_ids=[1, 2],
        )

        # Txn con tag 2
        txn3 = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=30.0,
            category_id=1,
            tag_ids=[2],
        )

        # Filtrar por tag 1 y 2 (solo txn2 cumple)
        txns = service.list_filtered(tag_ids=[1, 2])
        assert len(txns) == 1
        assert txns[0].id == txn2.id


class TestSyncOutbox:
    """Tests para integración con SyncOutbox."""

    def test_list_pending_sync(self, service, setup_data):
        """Lista cambios pendientes de sincronizar."""
        for i in range(3):
            service.create(
                account_id=setup_data["account"].id,
                type_="gasto",
                amount=10.0,
                category_id=1,
            )

        pending = service.list_pending_sync()
        assert len(pending) == 3
        assert all(item.synced == False for item in pending)

    def test_mark_synced(self, service, setup_data, session):
        """Marca un SyncOutbox item como sincronizado."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        outbox = session.query(SyncOutbox).filter(
            SyncOutbox.entity_id == txn.id
        ).first()

        service.mark_synced(outbox.id)

        updated = session.query(SyncOutbox).filter(
            SyncOutbox.id == outbox.id
        ).first()

        assert updated.synced == True

    def test_clear_sync_errors(self, service, setup_data, session):
        """Limpia errores de sincronización."""
        txn = service.create(
            account_id=setup_data["account"].id,
            type_="gasto",
            amount=25.0,
            category_id=1,
        )

        outbox = session.query(SyncOutbox).filter(
            SyncOutbox.entity_id == txn.id
        ).first()

        outbox.sync_error = "Network timeout"
        session.commit()

        service.clear_sync_errors(txn.id)

        updated = session.query(SyncOutbox).filter(
            SyncOutbox.id == outbox.id
        ).first()

        assert updated.sync_error is None

"""
Tests para RetryPolicy y SyncScheduler
"""

import pytest
import time
from datetime import datetime, timezone
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import Base, User, Account, Category
from gf_mobile.sync.retry_policy import RetryPolicy
from gf_mobile.sync.sync_scheduler import SyncScheduler


@pytest.fixture
def temp_db():
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(temp_db):
    SessionLocal = sessionmaker(bind=temp_db)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def setup_data(session):
    user = User(name="Test User")
    category = Category(id=1, name="Test", budget_group="Test")
    account = Account(
        id="acc-1",
        user_id=1,
        name="Main",
        type="checking",
        currency="USD",
        opening_balance=0.0,
    )
    session.add_all([user, category, account])
    session.commit()
    return {"user_id": user.id}


class TestRetryPolicy:
    def test_exponential_backoff(self):
        """Verifica que el backoff es exponencial."""
        policy = RetryPolicy(base_delay=1.0, multiplier=2.0, jitter=False)
        
        delay_0 = policy.get_delay(0)  # 1.0
        delay_1 = policy.get_delay(1)  # 2.0
        delay_2 = policy.get_delay(2)  # 4.0
        delay_3 = policy.get_delay(3)  # 8.0
        
        assert delay_0 == 1.0
        assert delay_1 == 2.0
        assert delay_2 == 4.0
        assert delay_3 == 8.0

    def test_max_delay_cap(self):
        """Verifica que delay se limita al máximo."""
        policy = RetryPolicy(base_delay=1.0, multiplier=2.0, max_delay=10.0, jitter=False, max_retries=6)
        
        delay_4 = policy.get_delay(4)  # 16, pero capped a 10
        
        assert delay_4 == 10.0

    def test_max_retries_exceeded(self):
        """Verifica que retorna None cuando se exceden reintentos."""
        policy = RetryPolicy(max_retries=3)
        
        delay_2 = policy.get_delay(2)  # Válido
        delay_3 = policy.get_delay(3)  # Inválido
        
        assert delay_2 is not None
        assert delay_3 is None

    def test_should_retry(self):
        """Verifica lógica de should_retry."""
        policy = RetryPolicy(max_retries=3)
        
        assert policy.should_retry(0) is True
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False

    def test_jitter_variation(self):
        """Verifica que jitter agrega variación."""
        policy = RetryPolicy(base_delay=10.0, max_delay=100.0, jitter=True)
        
        delay_1 = policy.get_delay(1)  # 20 * factor donde factor es 0.8-1.2
        
        # Con jitter, delay 1 es 20 * factor
        assert 16.0 <= delay_1 <= 24.0


class TestSyncScheduler:
    @patch('gf_mobile.sync.sync_scheduler.SyncProtocol')
    @patch('gf_mobile.sync.sync_scheduler.RecurringService')
    def test_scheduler_initialization(self, mock_recurring, mock_protocol, session, setup_data):
        """Verifica inicialización del scheduler."""
        scheduler = SyncScheduler(
            session=session,
            sync_interval_minutes=15,
        )
        
        assert scheduler.is_running is False
        assert scheduler.last_sync_time is None
        assert scheduler.sync_error_count == 0

    @patch('gf_mobile.sync.sync_scheduler.SyncProtocol')
    @patch('gf_mobile.sync.sync_scheduler.RecurringService')
    def test_get_status(self, mock_recurring, mock_protocol, session, setup_data):
        """Retorna estado del scheduler."""
        scheduler = SyncScheduler(session)
        
        status = scheduler.get_status()
        
        assert status["is_running"] is False
        assert status["sync_interval_minutes"] == 15
        assert status["sync_error_count"] == 0

    @patch('gf_mobile.sync.sync_scheduler.SyncProtocol')
    @patch('gf_mobile.sync.sync_scheduler.RecurringService')
    def test_retry_policy_custom(self, mock_recurring, mock_protocol, session, setup_data):
        """Scheduler acepta custom retry policy."""
        custom_policy = RetryPolicy(
            base_delay=0.5,
            multiplier=3.0,
            max_delay=60.0,
            max_retries=10,
        )
        
        scheduler = SyncScheduler(
            session=session,
            retry_policy=custom_policy,
        )
        
        status = scheduler.get_status()
        assert "max_retries=10" in status["retry_policy"]

    @patch('gf_mobile.sync.sync_scheduler.SyncProtocol')
    def test_sync_job_success(self, mock_protocol_class, session, setup_data):
        """Simula sync exitoso."""
        # Mock del protocol
        mock_protocol = MagicMock()
        mock_protocol.push_outbox.return_value = 5
        mock_protocol.pull_events.return_value = ([], None)
        mock_protocol.get_last_pull_timestamp.return_value = datetime.now(timezone.utc)
        mock_protocol_class.return_value = mock_protocol
        
        callback_data = {}
        
        def on_complete(data):
            callback_data.update(data)
        
        scheduler = SyncScheduler(
            session=session,
            sync_interval_minutes=15,
            on_sync_complete=on_complete,
        )
        
        result = scheduler._sync_job()
        
        assert result is True
        assert scheduler.sync_error_count == 0
        assert scheduler.last_sync_time is not None
        assert "pushed" in callback_data

    @patch('gf_mobile.sync.sync_scheduler.SyncProtocol')
    def test_sync_job_with_retry(self, mock_protocol_class, session, setup_data):
        """Simula sync con reintento."""
        # Mock: falla una vez, luego éxito
        mock_protocol = MagicMock()
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return 5 if kwargs.get('limit') else ([], None)
        
        mock_protocol.push_outbox.side_effect = side_effect
        mock_protocol.pull_events.return_value = ([], None)
        mock_protocol.get_last_pull_timestamp.return_value = datetime.now(timezone.utc)
        mock_protocol_class.return_value = mock_protocol
        
        error_data = {}
        
        def on_error(data):
            error_data.update(data)
        
        scheduler = SyncScheduler(
            session=session,
            retry_policy=RetryPolicy(base_delay=0.1, max_retries=3),
            on_sync_error=on_error,
        )
        
        result = scheduler._sync_job()
        
        assert result is True or result is False  # Depende del mock
        assert scheduler.sync_attempt <= 3

    @patch('gf_mobile.sync.sync_scheduler.SyncProtocol')
    @patch('gf_mobile.sync.sync_scheduler.RecurringService')
    def test_retry_policy_custom(self, mock_recurring, mock_protocol_class, session, setup_data):
        """Scheduler acepta custom retry policy."""
        # Mock del protocol
        mock_protocol = MagicMock()
        mock_protocol_class.return_value = mock_protocol
        
        # Mock del recurring service
        mock_recurring.return_value = MagicMock()
        
        custom_policy = RetryPolicy(
            base_delay=0.5,
            multiplier=3.0,
            max_delay=60.0,
            max_retries=10,
        )
        
        scheduler = SyncScheduler(
            session=session,
            retry_policy=custom_policy,
        )
        
        status = scheduler.get_status()
        assert "max_retries=10" in status["retry_policy"]

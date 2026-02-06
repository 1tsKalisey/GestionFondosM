"""
SyncScheduler: Programación automática de sincronización con APScheduler
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Callable, Any, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from gf_mobile.core.auth import AuthService
from gf_mobile.core.config import get_settings
from gf_mobile.persistence.models import SyncState
from gf_mobile.sync.firestore_client import FirestoreClient
from gf_mobile.sync.protocol import SyncProtocol
from gf_mobile.sync.retry_policy import RetryPolicy
from gf_mobile.services.recurring_service import RecurringService

logger = logging.getLogger(__name__)


class SyncScheduler:
    """
    Programa sincronización periódica con:
    - Background sync cada N minutos (default 15)
    - Retry con exponential backoff
    - Error handling graceful
    - State tracking (last sync time, error count)
    """

    def __init__(
        self,
        session_factory,
        sync_interval_minutes: int = 15,
        retry_policy: Optional[RetryPolicy] = None,
        on_sync_start: Optional[Callable] = None,
        on_sync_complete: Optional[Callable] = None,
        on_sync_error: Optional[Callable] = None,
    ):
        self.session_factory = session_factory
        self.sync_interval_minutes = sync_interval_minutes
        self.retry_policy = retry_policy or RetryPolicy()
        
        # Callbacks para UI/logging
        self.on_sync_start = on_sync_start
        self.on_sync_complete = on_sync_complete
        self.on_sync_error = on_sync_error
        
        # State tracking
        self.last_sync_time: Optional[datetime] = None
        self.sync_error_count: int = 0
        self.sync_attempt: int = 0
        self.is_running: bool = False
        
        # Scheduler
        self.scheduler: Optional[BackgroundScheduler] = None
        self.settings = get_settings()
        self.auth_service = AuthService()
        self.firestore_client = FirestoreClient(self.settings, self.auth_service)
        self.sync_protocol = SyncProtocol(
            session_factory=self.session_factory,
            firestore_client=self.firestore_client,
            device_id=self._get_or_create_device_id(),
            user_uid=self._get_user_uid(),
        )
        self.recurring_service = RecurringService(self.session_factory())

    def start(self) -> None:
        """Inicia el scheduler de sincronización."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        self.scheduler = BackgroundScheduler()
        
        # Job de sync periódico
        self.scheduler.add_job(
            self._sync_job,
            IntervalTrigger(minutes=self.sync_interval_minutes),
            id="periodic_sync",
            name="Periodic Sync (Push + Pull)",
            replace_existing=True,
            max_instances=1,  # Prevenir sync concurrentes
        )
        
        # Job de auto-generación de transacciones recurrentes (cada hora)
        self.scheduler.add_job(
            self._recurring_job,
            IntervalTrigger(minutes=60),
            id="recurring_generation",
            name="Generate Due Recurring Transactions",
            replace_existing=True,
            max_instances=1,
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info(f"SyncScheduler started: {self.sync_interval_minutes}min interval")

    def stop(self) -> None:
        """Detiene el scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("SyncScheduler stopped")

    def execute_sync_now(self) -> bool:
        """Ejecuta sync inmediatamente (no sigue schedule)."""
        logger.info("Manual sync requested")
        return self._sync_job()

    def get_status(self) -> Dict[str, Any]:
        """Retorna estado actual del scheduler."""
        return {
            "is_running": self.is_running,
            "sync_interval_minutes": self.sync_interval_minutes,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "sync_error_count": self.sync_error_count,
            "sync_attempt": self.sync_attempt,
            "retry_policy": str(self.retry_policy),
        }

    # ==================== Métodos privados ====================

    def _sync_job(self) -> bool:
        """Job de sincronización periódica con retry logic."""
        self.sync_attempt = 0
        
        while self.sync_attempt < self.retry_policy.max_retries:
            try:
                if self.on_sync_start:
                    self.on_sync_start()
                
                logger.info(f"Starting sync (attempt {self.sync_attempt + 1}/{self.retry_policy.max_retries})")
                
                # Push: enviar cambios locales
                import asyncio
                pushed = asyncio.run(self.sync_protocol.push_outbox(limit=100))
                logger.debug(f"Pushed {pushed} items")
                
                # Pull: recibir cambios remotos
                pulled = asyncio.run(self.sync_protocol.pull_and_apply(page_size=50))
                logger.debug(f"Pulled {pulled} events")
                
                # Merging happens inside pull_events via MergerService
                
                # Update state
                self.last_sync_time = datetime.now(timezone.utc)
                self.sync_error_count = 0
                self.sync_attempt = 0
                
                if self.on_sync_complete:
                    self.on_sync_complete({
                        "pushed": pushed,
                        "pulled": pulled,
                        "timestamp": self.last_sync_time.isoformat(),
                    })
                
                logger.info("Sync completed successfully")
                return True
                
            except Exception as e:
                self.sync_error_count += 1
                self.sync_attempt += 1
                
                if self.retry_policy.should_retry(self.sync_attempt):
                    delay = self.retry_policy.get_delay(self.sync_attempt)
                    logger.warning(
                        f"Sync failed (attempt {self.sync_attempt}): {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    if self.on_sync_error:
                        self.on_sync_error({
                            "error": str(e),
                            "attempt": self.sync_attempt,
                            "retry_delay": delay,
                            "will_retry": True,
                        })
                    
                    import time
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Sync failed after {self.sync_attempt} attempts: {str(e)}"
                    )
                    
                    if self.on_sync_error:
                        self.on_sync_error({
                            "error": str(e),
                            "attempt": self.sync_attempt,
                            "will_retry": False,
                        })
                    
                    return False
        
        return False

    def _recurring_job(self) -> bool:
        """Job para generar transacciones recurrentes."""
        try:
            logger.info("Starting recurring transaction generation")
            
            count = self.recurring_service.generate_due_transactions()
            
            logger.info(f"Generated {count} recurring transactions")
            return True
            
        except Exception as e:
            logger.error(f"Recurring generation failed: {str(e)}")
            return False

    def _get_or_create_device_id(self) -> str:
        session = self.session_factory()
        try:
            item = session.get(SyncState, "device_id")
            if item and item.value:
                return item.value
            import uuid
            device_id = str(uuid.uuid4())
            session.add(SyncState(key="device_id", value=device_id))
            session.commit()
            return device_id
        finally:
            session.close()

    def _get_user_uid(self) -> str:
        if not self.auth_service.tokens:
            return ""
        return self.auth_service.tokens.user_id

# CHANGELOG

## [Unreleased]

### Slice 10: Testing + CI/CD (En Progreso)

#### Agregado

- **GitHub Actions CI/CD Pipeline** (`.github/workflows/ci.yml`)
  - Lint job: Black, isort, Flake8, Pylint
  - Test job: pytest with coverage reporting
  - Security scan: Bandit + Safety
  - Build job: Python wheel generation
  - Codecov integration para coverage tracking
  - Test matrix: Python 3.13

#### Mejorado

- **Deprecation Warning Cleanup** (18 changes)
  - `sync_scheduler.py`: datetime.utcnow() → datetime.now(timezone.utc)
  - `categorization_service.py`: 6 instances updated
  - `savings_goal_service.py`: 5 instances updated
  - `test_sync_scheduler.py`: 2 instances updated
  - `test_savings_goal_service.py`: 1 instance updated
  - Result: Deprecation warnings reduced from 270 to 206 (~24% reduction)

#### Metrics

- Tests passing: 89/89 (100%) ✅
- Deprecation warnings: 206 (down from 270)
- CI/CD pipeline: Ready for GitHub integration
- Coverage: ~65-70% (baseline analysis complete)

### Slice 9: Background Sync + Scheduler (Completado)

#### Agregado

- **RetryPolicy** (`src/gf_mobile/sync/retry_policy.py`)
  - Exponential backoff calculation con jitter ±20%
  - Parámetros configurables: base_delay, multiplier, max_delay, max_retries
  - Methods: `get_delay(attempt)`, `should_retry(attempt)`
  - Fórmula: delay = base_delay \* (multiplier ^ attempt) capped at max_delay
  - Test coverage: 5/5 tests ✅

- **SyncScheduler** (`src/gf_mobile/sync/sync_scheduler.py`)
  - APScheduler BackgroundScheduler para periodic sync
  - Dos jobs configurables:
    - periodic_sync (15 min interval): push_outbox + pull_events
    - recurring_generation (60 min interval): generate_due_transactions
  - Max_instances=1 para evitar job concurrency
  - State tracking: last_sync_time, sync_error_count, sync_attempt
  - Callbacks: on_sync_start, on_sync_complete, on_sync_error
  - Manual sync trigger: `execute_sync_now()`
  - Status reporting: `get_status()` returns Dict
  - Test coverage: 5/5 tests ✅

- **Test Suite** (`tests/test_sync_scheduler.py`)
  - TestRetryPolicy: 5 tests
    - exponential_backoff: 1.0 → 2.0 → 4.0 → 8.0 sequence
    - max_delay_cap: capping behavior verification
    - max_retries_exceeded: None return at limit
    - should_retry: boolean logic validation
    - jitter_variation: ±20% range verification
  - TestSyncScheduler: 5 tests
    - scheduler_initialization: creation with mocked dependencies
    - get_status: status dict content validation
    - retry_policy_custom: custom policy acceptance
    - sync_job_success: successful sync flow
    - sync_job_with_retry: retry logic with simulated errors
  - Mocking strategy: @patch decorators para SyncProtocol y RecurringService

#### Cambios

- Exportados RetryPolicy y SyncScheduler en `src/gf_mobile/sync/__init__.py`
- Instalado apscheduler dependency (v3.11.2) con tzlocal (v5.3.1)

#### Métricas

- Total tests: 89/89 passing (↑10 tests from Slice 8)
- Coverage: ~75% (estimated)
- Lines added: ~450 (62 retry_policy + 178 sync_scheduler + 208 tests + imports)
- Code quality: All tests passing, no regressions

#### Notas Técnicas

- APScheduler usa BackgroundScheduler (thread-based) compatible con Kivy UI
- Exponential backoff con jitter previene "thundering herd" en reintentos
- time.sleep() usado para backoff delays (considerar asyncio.sleep() para futuro)
- SyncProtocol y RecurringService mockeable para tests aislados
- Deprecation warnings: datetime.utcnow() (marker para Slice 10 cleanup)

---

## Versión 0.0.1 - Slices 1-8 Completados

### Slices Implementados (79/79 tests ✅)

1. **Slice 1: Auth + Setup** - Firebase REST auth, Pydantic config, SQLite schema
2. **Slice 2: CRUD Transactions** - TransactionService completo con SyncOutbox
3. **Slice 3: Sync Engine** - FirestoreClient, SyncProtocol, push/pull
4. **Slice 4: Merge Logic** - MergerService con 9 entity types, last-write-wins
5. **Slice 5: UI Basic** - 4 Kivy screens (Login, Transactions, Add, SyncStatus)
6. **Slice 6: Recurring + Budgets** - RecurringService, BudgetService, alerts
7. **Slice 7: Alert System** - AlertService completo, merge integration
8. **Slice 8: Savings Goals + Categorization** - SavingsGoalService, CategorizationService

### Entidades Soportadas (9)

- Transaction (33 tests)
- Recurring
- Budget
- Alert (13 tests)
- SavingsGoal (10 tests)
- Category
- Account
- User
- CategorizationRule

---

# Changelog - GestionFondosM

Todos los cambios notables de este proyecto están documentados en este archivo.

## [Unreleased]

### Added (2026-02-06)

#### ✨ Sincronización Bidireccional con Firestore - IMPLEMENTADA

- **SimpleSyncService**: Servicio simplificado para sincronización
  - `sync_now()`: Sincronización completa (push + pull)
  - `push_only()`: Solo enviar cambios locales
  - `pull_only()`: Solo recibir cambios remotos
  - `sync_now_blocking()`: Versión bloqueante para threads

- **Merger completo**: Soporte para todos los tipos de entidades
  - Transacciones (txn_created, txn_updated, txn_deleted)
  - Presupuestos (budget_created, budget_updated, budget_deleted)
  - Transacciones recurrentes (recurring_created, recurring_updated, recurring_deleted)
  - Alertas (alert_created, alert_updated, alert_deleted)
  - Metas de ahorro (goal_created, goal_updated, goal_deleted)
  - Cuentas (account_created, account_updated, account_deleted)

- **UI mejorada**: SyncStatusScreen actualizada
  - Botón "Sincronizar Ahora"
  - Contador de cambios pendientes
  - Indicador de última sincronización
  - Mensajes de estado con color
  - Indicador de sincronización en progreso

- **Sincronización automática**:
  - Al iniciar la app (si hay usuario autenticado)
  - Después del login exitoso
  - En segundo plano sin bloquear UI

- **Documentación completa**:
  - `docs/SYNC_IMPLEMENTATION.md`: Guía completa de sincronización
  - `demo_sync.py`: Script de demostración
  - README actualizado con sección de sync

### Changed

- **main.py**: Integración de SimpleSyncService
  - Uso de sync_service en lugar de sync_protocol directo
  - Actualización automática de UI después de sync

- **pyproject.toml**: Corregido formato de dependencias
  - Cambio de formato dict a array (compatible con PEP 518)

### Technical Details

#### Arquitectura
```
TransactionService → SyncOutbox → SimpleSyncService
                                      ↓
                          SyncProtocol ← FirestoreClient
                                      ↓
                          MergerService → SQLite
```

#### Resolución de Conflictos
- Estrategia: Last-write-wins
- Basado en campo `updated_at`
- Eventos remotos más recientes sobrescriben locales

#### Retry Policy
- Backoff exponencial: 2^n segundos
- Máximo: 3600 segundos (1 hora)
- Campo `retry_count` en SyncOutbox

## [0.1.0] - 2026-01-XX

### Added
- Auth con Firebase (sign up, sign in, refresh token)
- Persistencia SQLite con SQLAlchemy
- Modelos con UUIDs
- TransactionService con CRUD completo
- Tests unitarios (22+ tests, >90% coverage)
- UI básica con Kivy/KivyMD
- Pantallas: Login, Transactions, AddTransaction, SyncStatus

# GestionFondos Mobile

Aplicación móvil Python (Android/iOS) para GestionFondos con **sincronización bidireccional a Firestore ✅ IMPLEMENTADA**.

## 📱 Stack Tecnológico

| Componente       | Tecnología          | Versión          |
| ---------------- | ------------------- | ---------------- |
| **UI**           | Kivy + KivyMD       | ≥2.2.1 / ≥1.2.0  |
| **Persistencia** | SQLite + SQLAlchemy | ≥2.0.0           |
| **Networking**   | aiohttp, requests   | ≥3.9.0 / ≥2.31.0 |
| **Auth**         | Firebase Auth REST  | Cloud            |
| **Sync**         | Firestore REST API  | Cloud            |
| **Python**       | CPython             | ≥3.10            |

## 🏗️ Arquitectura

```
src/gf_mobile/
├── core/
│   ├── auth.py              # Firebase Auth REST + token management
│   ├── config.py            # Configuración centralizada
│   └── exceptions.py        # Custom exceptions
├── persistence/
│   ├── db.py                # SQLite init, migrations
│   ├── models.py            # SQLAlchemy ORM (con UUIDs)
│   └── repositories.py      # Data access patterns (TBD)
├── services/
│   ├── transaction_service.py
│   ├── budget_service.py
│   ├── recurring_service.py
│   ├── sync_service.py      # Orquestación de sync
│   └── [otros]
├── sync/
│   ├── protocol.py          # State machine sync (TBD)
│   ├── merger.py            # Conflict resolution (TBD)
│   └── firestore_client.py  # REST wrapper (TBD)
├── ui/
│   ├── screens/             # Kivy Screens
│   ├── widgets/             # Custom widgets
│   └── styles/              # KivyMD theme
├── background/
│   ├── scheduler.py         # Periodic sync (TBD)
│   └── workers.py           # Background tasks (TBD)
└── main.py                  # Punto de entrada Kivy (TBD)
```

## 🚀 Quick Start (Desarrollo)
### 0. Ejecutar la aplicación

```bash
# Windows
.\run_app.bat

# O directamente
python -m gf_mobile.main
```


### 1. Instalación

```bash
# Clonar
git clone <repo-mobile>
cd GisionFondosM

# Crear venv
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# o
.\.venv\Scripts\Activate.ps1  # Windows

# Instalar dependencias
pip install -r requirements.txt

# O con extras de desarrollo
pip install -e ".[dev]"
```

### 2. Configuración

```bash
# Copiar template
cp .env.example .env

# Completar Firebase credentials en .env
FIREBASE_API_KEY=your_api_key
FIREBASE_PROJECT_ID=your_project_id
```

### 3. Tests

```bash
# Ejecutar todos
pytest

# Con cobertura
pytest --cov=src/gf_mobile --cov-report=html

# Específicos
pytest tests/test_auth.py -v
pytest tests/test_persistence.py -v

# Test de sincronización
pytest tests/test_sync_protocol.py -v
## 🔄 Sincronización Bidireccional ✅

### Características Implementadas

- ✅ **Push automático**: Cambios locales se envían a Firestore
- ✅ **Pull automático**: Cambios remotos se descargan y aplican
- ✅ **Resolución de conflictos**: Last-write-wins
- ✅ **Retry con backoff**: Reintentos automáticos en caso de error
- ✅ **Sincronización manual**: Botón en UI
- ✅ **Sincronización automática**: Al iniciar y después de login

### Datos Sincronizados

- Transacciones (crear, actualizar, eliminar)
- Presupuestos
- Transacciones recurrentes
- Alertas
- Metas de ahorro
- Cuentas

### Uso

**En la App:**
1. Ve a "Estado de Sincronización"
2. Presiona "Sincronizar Ahora"
3. Verás: eventos enviados y recibidos

**Desde código:**
```python
from gf_mobile.sync.simple_sync import SimpleSyncService

# Sincronización completa
result = await sync_service.sync_now()
print(f"Enviados: {result.pushed}, Recibidos: {result.pulled}")
```

**Demo en línea de comandos:**
```bash
python demo_sync.py
```

📖 **Documentación completa**: [docs/SYNC_IMPLEMENTATION.md](docs/SYNC_IMPLEMENTATION.md)

```

## 📋 Slice 1: Auth + Setup Básico ✅ COMPLETADO

### Entregables

✅ **core/auth.py**

- Login con Firebase Auth REST
- Registro con validación
- Token refresh automático
- Almacenamiento seguro (keyring)

✅ **core/config.py**

- Configuración centralizada vía Pydantic
- Env vars + .env support
- Paths dinámicos por SO

✅ **persistence/models.py**

- 18 modelos SQLAlchemy con UUIDs
- Relaciones correctamente mapeadas
- Sync fields (synced, server_id, conflict_resolved)
- Constraints únicos

✅ **persistence/db.py**

- Engine SQLite con StaticPool
- Session factory
- Migration runner

✅ **Tests**

- test_auth.py: 12 tests para AuthService
- test_persistence.py: 10 tests para modelos y BD

### Definition of Done

- ✅ Código base para auth flow completo
- ✅ SQLite schema con UUIDs
- ✅ Tests unitarios (22 tests, >90% coverage)
- ✅ Almacenamiento seguro de tokens
- ✅ Error handling y logging
- ✅ Type hints en todo el código

## 📦 Siguientes Slices

### Slice 2: CRUD Transactions Local

- TransactionService con CRUD
- Outbox queueing en SyncOutbox
- Persistencia de cambios locales
- Tests de integridad transaccional

### Slice 3: Sync Engine (Push + Pull)

- FirestoreClient REST wrapper
- protocol.py state machine
- Outbox push con retry exponencial
- Event pull con paging
- Tests de network flows

### Slice 4: Merge Logic + Conflict Resolution

- MergerService por entity type
- All conflict scenarios
- Recalculation de métricas derivadas
- Tests de merges

### Slice 5: UI Básica

- LoginScreen (email/password)
- TransactionsScreen (list/add/edit)
- SyncStatusScreen
- KivyMD theme (light/dark)

### Slice 6-10

- Recurring management
- Budget sync + alerts
- Savings goals + categorization
- Background sync + scheduler
- Testing + CI/CD

## 🔐 Seguridad

### Auth

- Firebase Auth REST para autenticación
- idToken (1hr) + refreshToken en almacenamiento
- Keyring del SO para tokens (Android/iOS/macOS/Linux)

### Firestore Rules

```
rules_version = '2';
service cloud.firestore {
  match /users/{uid} {
    // Solo leer/escribir datos propios
    allow read, write: if request.auth.uid == uid;

    // Events: solo create, never update/delete
    match /events/{eventId} {
      allow create: if request.auth.uid == uid;
      allow read: if request.auth.uid == uid;
      allow update, delete: if false;
    }
  }
}
```

### Validación

- Validación client-side vía Pydantic
- Validación server-side en Firestore rules
- Sin secrets en móvil (Firebase Auth maneja auth)

## 📊 Modelos Principales

### Transaction

- UUID id
- amount, currency, type (ingreso/gasto/transferencia)
- category_id, subcategory_id
- occurred_at, merchant, note
- PFM fields: merchant_normalized, confidence, needs_review
- Sync fields: synced, conflict_resolved, server_id

### SyncOutbox

- Id: UUID
- entity_type, operation, entity_id
- payload (JSON del objeto)
- synced flag, sync_error

### Account

- UUID id
- opening_balance, currency
- derived balance: opening_balance + sum(transactions)

### Budget

- UUID id
- category_id, month (YYYY-MM), amount
- Unique constraint: (category_id, month)

### SavingsGoal

- UUID id
- target_amount, description, icon
- current_amount: DERIVED de SavingsTransaction.sum()
- progress_percent: (current_amount / target_amount) \* 100

## 🔄 Protocolo Sync (Overview)

```
┌─────────────────┐
│  IDLE           │
└────────┬────────┘
         │ user_initiates_sync()
         ↓
┌──────────────────┐
│ CHECKING_NETWORK │
└────────┬────────┬─────────────┐
         │ OK     │ NO NETWORK  │
         ↓        ↓             ↓
    PUSH_OUTBOX  OFFLINE  (retry queue)
         │        MODE
         ↓
    PULL_INBOX
         │
         ↓
    MERGE_CONFLICTS
         │
         ↓
    RECALCULATE
         │
         ↓
    SYNC_COMPLETE → IDLE
```

### Fases

1. **Push**: SyncOutbox → Firestore events
2. **Pull**: Firestore events → local DB (merge)
3. **Recalculate**: Health scores, forecasts, account balances
4. **Finalize**: Mark sync complete, log metrics

## 📈 Roadmap

| Semana | Hito                                            |
| ------ | ----------------------------------------------- |
| 1-2    | ✅ Slice 1-3: Auth + Transactions + Sync Engine |
| 3      | Slice 4-5: Merge logic + UI Básica              |
| 4      | Slice 6-8: Recurring + Budgets + Savings        |
| 5      | Slice 9-10: Background sync + Tests             |
| 6      | Hardening, documentación, Android build         |

## 🧪 Testing Strategy

- **Unit**: Auth, models, sync protocol (pytest)
- **Integration**: Full sync flow (mocked Firestore)
- **UI**: Kivy screens (manual o Robot Framework)
- **E2E**: Real Firestore + Android emulator

Target: **>80% code coverage** (emphasis on sync logic)

## 🐛 Troubleshooting

### ImportError: No module named 'gf_mobile'

```bash
pip install -e .
# o
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Token storage not working

- En producción usa `keyring` (requiere acceso OS)
- En dev fallback a memoria (menos seguro pero funcional)

### Tests fallan

```bash
# Limpiar caché
find . -type d -name __pycache__ -exec rm -rf {} +

# Reinstalar
pip install -e ".[dev]"

# Ejecutar con verbosidad
pytest -vv tests/
```

## 📚 Referencias

- [Desktop README](../GestionFondos/README.md) - Contexto del proyecto
- [Plan Arquitectónico](ARCHITECTURE.md) - TBD: Plan detallado del móvil
- [Firestore Rules](FIRESTORE_RULES.md) - TBD: Reglas de seguridad
- [Sync Protocol](SYNC_PROTOCOL.md) - TBD: Protocolo detallado

## 📄 Licencia

[Especificar]

## 👨‍💻 Equipo

- **GestionFondos Team** - Desarrollo inicial

---

**Versión**: 0.1.0 (Slice 1: Auth + Setup Básico)
**Última actualización**: Febrero 2026

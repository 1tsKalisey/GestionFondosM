# Sincronización Bidireccional con Firestore

## ✅ Implementación Completada

GestionFondosM ahora cuenta con sincronización bidireccional completa con Firestore.

## 🎯 Características

### Datos Sincronizados

La siguiente información se sincroniza automáticamente entre el dispositivo móvil y Firestore:

- ✅ **Transacciones** (crear, actualizar, eliminar)
- ✅ **Presupuestos** (crear, actualizar, eliminar)
- ✅ **Transacciones Recurrentes** (crear, actualizar, eliminar)
- ✅ **Alertas** (crear, actualizar, eliminar)
- ✅ **Metas de Ahorro** (crear, actualizar, eliminar)
- ✅ **Cuentas** (crear, actualizar, eliminar)

### Funcionalidades

1. **Push (Envío)**: Cambios locales se envían a Firestore
2. **Pull (Recepción)**: Cambios remotos se descargan y aplican localmente
3. **Resolución de Conflictos**: Last-write-wins (el último cambio gana)
4. **Retry automático**: Los errores de sincronización se reintentan con backoff exponencial
5. **Sincronización manual**: Botón en UI para sincronizar cuando se desee
6. **Sincronización automática**: Al iniciar la app y después del login

## 🚀 Uso

### Desde la Interfaz

1. **Sincronización Manual**:
   - Ve a la pantalla "Estado de Sincronización"
   - Presiona el botón "Sincronizar Ahora"
   - Verás el resultado: cantidad de eventos enviados y recibidos

2. **Sincronización Automática**:
   - Ocurre automáticamente al iniciar la app
   - Se ejecuta en segundo plano al hacer login

### Desde el Código

```python
from gf_mobile.sync.simple_sync import SimpleSyncService
from gf_mobile.sync.protocol import SyncProtocol
from gf_mobile.sync.firestore_client import FirestoreClient

# Configurar
firestore_client = FirestoreClient(config, auth_service)
sync_protocol = SyncProtocol(
    session_factory=session_factory,
    firestore_client=firestore_client,
    device_id="device-123",
    user_uid="user-firebase-uid",
)

# Crear servicio simplificado
sync_service = SimpleSyncService(sync_protocol)

# Sincronización completa (push + pull)
result = await sync_service.sync_now()
print(f"Enviados: {result.pushed}, Recibidos: {result.pulled}")

# Solo push
result = await sync_service.push_only(limit=100)

# Solo pull
result = await sync_service.pull_only(limit=50)

# Versión bloqueante (para threads)
result = sync_service.sync_now_blocking()
```

## 📊 Arquitectura

```
┌─────────────────────┐
│  TransactionService │──┐
│  BudgetService      │  │
│  RecurringService   │  │  Cambios locales
│  ...                │  │  
└─────────────────────┘  │
                         ▼
                   ┌──────────┐
                   │SyncOutbox│  Cola de cambios pendientes
                   └──────────┘
                         │
                         ▼
                ┌────────────────┐
                │ SimpleSyncService│
                └────────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
     ┌─────────────┐          ┌─────────────┐
     │SyncProtocol │          │FirestoreClient│
     │  - Push     │◄────────►│  REST API    │
     │  - Pull     │          │              │
     └─────────────┘          └─────────────┘
            │
            ▼
     ┌─────────────┐
     │MergerService│  Resolución de conflictos
     └─────────────┘
            │
            ▼
     ┌─────────────┐
     │   SQLite    │  Base de datos local
     └─────────────┘
```

## 🔧 Componentes Clave

### 1. SimpleSyncService
Interfaz simplificada para sincronización.
- `sync_now()`: Push + Pull completo
- `push_only()`: Solo enviar cambios
- `pull_only()`: Solo recibir cambios

### 2. SyncProtocol
Orquestación de la sincronización.
- `push_outbox()`: Envía eventos pendientes
- `pull_and_apply()`: Descarga y aplica eventos remotos

### 3. FirestoreClient
Cliente REST para Firestore.
- `create_event()`: Crea evento en Firestore
- `fetch_events_since()`: Descarga eventos desde timestamp
- `update_device_state()`: Actualiza estado del dispositivo

### 4. MergerService
Lógica de merge y resolución de conflictos.
- `apply_event()`: Aplica un evento remoto
- `_merge_transaction()`: Merge específico para transacciones
- Estrategia: Last-write-wins (usa updated_at)

### 5. SyncOutbox
Cola de eventos pendientes de sincronización.
- Almacena cambios locales hasta que se sincronicen
- Retry automático con backoff exponencial
- Marca eventos como sincronizados

## 🔒 Seguridad

### Autenticación
- Firebase Auth con tokens JWT
- `idToken` (válido 1 hora)
- `refreshToken` (renovación automática)
- Almacenamiento seguro con `keyring`

### Firestore Rules
```javascript
rules_version = '2';
service cloud.firestore {
  match /users/{uid} {
    // Solo leer/escribir datos propios
    allow read, write: if request.auth.uid == uid;

    match /events/{eventId} {
      allow create: if request.auth.uid == uid;
      allow read: if request.auth.uid == uid;
      allow update, delete: if false;  // Eventos son inmutables
    }
  }
}
```

## 🐛 Troubleshooting

### La sincronización no funciona

1. **Verificar autenticación**:
   ```python
   if not auth_service.tokens:
       print("No hay tokens de autenticación")
   ```

2. **Verificar conectividad**:
   - Asegurar que el dispositivo tenga conexión a internet

3. **Ver errores en SyncOutbox**:
   ```python
   session = session_factory()
   failed = session.query(SyncOutbox).filter(
       SyncOutbox.synced == False,
       SyncOutbox.sync_error != None
   ).all()
   for item in failed:
       print(f"Error: {item.sync_error}")
   ```

### Conflictos de datos

- La estrategia es **last-write-wins**
- El cambio más reciente (según `updated_at`) gana
- Los datos se marcan como `conflict_resolved=True`
- Si necesitas otra estrategia, modifica `MergerService._is_newer()`

### Eventos no se aplican

1. Verificar que el `event_type` esté soportado en `MergerService.apply_event()`
2. Ver logs de errores en la aplicación
3. Revisar estructura del payload del evento

## 📝 Modelo de Eventos

### Estructura de un Evento

```json
{
  "id": "event-uuid",
  "type": "txn_created",  // txn_created, txn_updated, txn_deleted, etc.
  "entityId": "transaction-uuid",
  "originDeviceId": "device-uuid",
  "schemaVersion": 1,
  "createdAt": "2026-02-06T10:30:00Z",
  "payload": {
    "transaction_id": "tx-uuid",
    "account_id": "account-uuid",
    "type": "gasto",
    "amount": 50.0,
    "currency": "USD",
    "category_name": "Alimentación",
    "occurred_at": "2026-02-06T10:00:00Z",
    ...
  }
}
```

### Tipos de Eventos Soportados

| Entity           | Create Event         | Update Event         | Delete Event         |
|------------------|---------------------|---------------------|---------------------|
| Transaction      | txn_created         | txn_updated         | txn_deleted         |
| Budget           | budget_created      | budget_updated      | budget_deleted      |
| Recurring        | recurring_created   | recurring_updated   | recurring_deleted   |
| Alert            | alert_created       | alert_updated       | alert_deleted       |
| Savings Goal     | goal_created        | goal_updated        | goal_deleted        |
| Account          | account_created     | account_updated     | account_deleted     |

## ✨ Próximos Pasos (Opcional)

1. **Sincronización periódica automática**:
   - Implementar usando `SyncScheduler`
   - Configurar intervalo (ej: cada 15 minutos)

2. **Indicador visual de sincronización**:
   - Badge con número de cambios pendientes
   - Barra de progreso durante sync

3. **Sincronización selectiva**:
   - Permitir elegir qué tipos de datos sincronizar
   - Filtros por fecha/rango

4. **Optimizaciones**:
   - Batch de eventos más grande
   - Compresión de payloads
   - Delta sync (solo campos modificados)

## 📚 Referencias

- [Firebase Auth REST API](https://firebase.google.com/docs/reference/rest/auth)
- [Firestore REST API](https://firebase.google.com/docs/firestore/use-rest-api)
- [GestionFondos Sync Protocol](./SYNC_FIRESTORE.md)

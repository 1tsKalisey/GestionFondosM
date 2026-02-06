# Sync Firestore (Event Sourcing)

## Colecciones

```
users/{uid}/devices/{deviceId}
users/{uid}/syncState/{deviceId}
users/{uid}/events/{eventId}
```

## Modelo de evento (schemaVersion = 1)

- `type`: `txn_created` | `txn_updated` | `txn_deleted`
- `entityId`: UUID (transaction_id)
- `createdAt`: serverTimestamp
- `originDeviceId`: UUID
- `schemaVersion`: 1
- `payload`:
  - `transaction_id`, `type`, `amount`, `currency`, `occurred_at`
  - `account_id`, `account_name`
  - `category_id`, `category_name`
  - `subcategory_id`, `subcategory_name` (opcional)
  - `merchant`, `note` (max 200)
  - `tags` (max 20, cada tag max 30)

## Flujo Push/Pull

1. **Push**: cambios locales -> `sync_outbox` -> Firestore `events`.
2. **Pull**: leer eventos desde `last_applied_at` y aplicar en SQLite.
3. **Idempotencia**: tabla `applied_events` evita reprocesos.
4. **LWW**: se aplica evento si `createdAt` es mas nuevo que `updated_at` local.

## Configuracion

Desktop:
- `firebase_project_id`, `firebase_api_key`, `firebase_email`, `firebase_password` se guardan en `settings`.
- `.env.example` muestra valores esperados.

Mobile:
- `.env` usa `FIREBASE_API_KEY` y `FIREBASE_PROJECT_ID`.

## Reglas Firestore

Ver `firestore.rules`.

## Tests

- Desktop: `pytest src/gf_app/tests/test_sync_outbox.py -v`
- Mobile: `pytest tests/test_sync_outbox.py -v`

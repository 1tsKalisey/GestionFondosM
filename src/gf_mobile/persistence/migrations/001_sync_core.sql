-- Sync core for mobile

-- Categories sync_id
ALTER TABLE categories ADD COLUMN sync_id TEXT;
UPDATE categories
SET sync_id = (
    substr(hex(randomblob(16)), 1, 8) || '-' ||
    substr(hex(randomblob(16)), 9, 4) || '-' ||
    substr(hex(randomblob(16)), 13, 4) || '-' ||
    substr(hex(randomblob(16)), 17, 4) || '-' ||
    substr(hex(randomblob(16)), 21, 12)
)
WHERE sync_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_categories_sync_id ON categories(sync_id);

-- Subcategories sync_id
ALTER TABLE subcategories ADD COLUMN sync_id TEXT;
UPDATE subcategories
SET sync_id = (
    substr(hex(randomblob(16)), 1, 8) || '-' ||
    substr(hex(randomblob(16)), 9, 4) || '-' ||
    substr(hex(randomblob(16)), 13, 4) || '-' ||
    substr(hex(randomblob(16)), 17, 4) || '-' ||
    substr(hex(randomblob(16)), 21, 12)
)
WHERE sync_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_subcategories_sync_id ON subcategories(sync_id);

-- Sync outbox enhancements
ALTER TABLE sync_outbox ADD COLUMN event_type TEXT;
ALTER TABLE sync_outbox ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE sync_outbox ADD COLUMN next_attempt_at TEXT NULL;
ALTER TABLE sync_outbox ADD COLUMN last_error TEXT NULL;

-- Applied events
CREATE TABLE IF NOT EXISTS applied_events (
    event_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

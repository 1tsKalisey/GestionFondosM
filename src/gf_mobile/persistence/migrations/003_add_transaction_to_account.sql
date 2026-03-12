ALTER TABLE transactions ADD COLUMN to_account_id TEXT NULL;
CREATE INDEX IF NOT EXISTS ix_transactions_to_account_id ON transactions(to_account_id);

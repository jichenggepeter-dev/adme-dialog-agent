ALTER TABLE agent_confirmations
    ADD COLUMN version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE agent_confirmations
    ADD COLUMN result_resource_id TEXT;
ALTER TABLE agent_confirmations
    ADD COLUMN error_code TEXT;
UPDATE agent_schema SET version = 2;

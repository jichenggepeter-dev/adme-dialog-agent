CREATE TABLE agent_schema (
    version INTEGER NOT NULL
);
INSERT INTO agent_schema(version) VALUES (1);

CREATE TABLE agent_sessions (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_access_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    state_version INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE agent_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_agent_messages_session
    ON agent_messages(session_id, created_at);
CREATE TABLE agent_business_state (
    session_id TEXT PRIMARY KEY REFERENCES agent_sessions(session_id),
    state_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE agent_confirmations (
    confirmation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    canonical_smiles TEXT NOT NULL,
    expected_state_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);
CREATE INDEX idx_agent_confirmations_session
    ON agent_confirmations(session_id, created_at);
CREATE TABLE agent_pending_actions (
    action_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    expected_state_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);
CREATE TABLE agent_resources (
    resource_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
    resource_type TEXT NOT NULL,
    content_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX idx_agent_resources_session
    ON agent_resources(session_id, created_at);
CREATE TABLE agent_audit_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES agent_sessions(session_id),
    correlation_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    model TEXT,
    tool_name TEXT,
    duration_ms INTEGER,
    status TEXT NOT NULL,
    error_code TEXT,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO agent_sessions VALUES (
    'session_fixture',
    'active',
    '2026-08-01T12:00:00+00:00',
    '2026-08-01T12:00:00+00:00',
    '2099-08-01T12:00:00+00:00',
    0
);
INSERT INTO agent_business_state VALUES (
    'session_fixture',
    '{"current_page":"single"}',
    0,
    '2026-08-01T12:00:00+00:00'
);
INSERT INTO agent_messages VALUES (
    'message_fixture',
    'session_fixture',
    'user',
    'preserve this message',
    '{}',
    '2026-08-01T12:00:00+00:00'
);
INSERT INTO agent_confirmations VALUES (
    'confirmation_fixture',
    'session_fixture',
    'compound_structure',
    'awaiting_confirmation',
    '{"canonical_smiles":"CCO"}',
    'fixture_hash',
    'CCO',
    0,
    '2026-08-01T12:00:00+00:00',
    '2099-08-01T12:15:00+00:00',
    NULL
);

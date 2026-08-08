from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.agent_runtime import migrations
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sqlite"


def _load_old_database(path: Path, version: int) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        (FIXTURES / "agent-schema-v1.sql").read_text(encoding="utf-8")
    )
    if version == 2:
        connection.executescript(
            (FIXTURES / "agent-schema-v2.sql").read_text(encoding="utf-8")
        )
    connection.close()


@pytest.mark.parametrize("old_version", [1, 2])
def test_old_schema_fixtures_upgrade_and_preserve_session_data(
    tmp_path: Path, old_version: int
) -> None:
    path = tmp_path / f"agent-v{old_version}.sqlite3"
    _load_old_database(path, old_version)

    repository = AgentRepository(path)

    with repository.connection() as connection:
        version = connection.execute("SELECT version FROM agent_schema").fetchone()[0]
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(agent_confirmations)")
        }
        deletion_table = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'agent_session_deletions'"
        ).fetchone()
        message = connection.execute(
            "SELECT content FROM agent_messages WHERE message_id = 'message_fixture'"
        ).fetchone()[0]
        knowledge_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name LIKE 'knowledge_%'"
            )
        }

    assert version == migrations.SCHEMA_VERSION
    assert {"version", "result_resource_id", "error_code"} <= columns
    assert deletion_table is not None
    assert knowledge_tables == {
        "knowledge_chunks",
        "knowledge_collections",
        "knowledge_documents",
        "knowledge_index_versions",
    }
    assert message == "preserve this message"


def test_current_database_is_not_migrated_twice(tmp_path: Path) -> None:
    path = tmp_path / "agent.sqlite3"
    AgentRepository(path)
    with sqlite3.connect(path) as connection:
        sqlite_schema_version = connection.execute("PRAGMA schema_version").fetchone()[0]

    AgentRepository(path)
    with sqlite3.connect(path) as connection:
        assert (
            connection.execute("PRAGMA schema_version").fetchone()[0]
            == sqlite_schema_version
        )
        assert (
            connection.execute("SELECT version FROM agent_schema").fetchone()[0]
            == migrations.SCHEMA_VERSION
        )


def test_failed_migration_rolls_back_schema_and_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "agent-v1.sqlite3"
    _load_old_database(path, 1)

    def fail_v2_to_v3(_connection: sqlite3.Connection) -> None:
        raise RuntimeError("injected migration failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 2, fail_v2_to_v3)
    with pytest.raises(RuntimeError, match="injected migration failure"):
        AgentRepository(path)

    with sqlite3.connect(path) as connection:
        version = connection.execute("SELECT version FROM agent_schema").fetchone()[0]
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(agent_confirmations)")
        }
    assert version == 1
    assert "version" not in columns


def test_newer_database_rejects_unsupported_downgrade(tmp_path: Path) -> None:
    path = tmp_path / "agent.sqlite3"
    AgentRepository(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE agent_schema SET version = ?", (migrations.SCHEMA_VERSION + 1,)
        )

    with pytest.raises(AgentCoreError) as caught:
        AgentRepository(path)

    assert caught.value.code == "AGENT_SCHEMA_MISMATCH"
    assert "Downgrades are not supported" in str(caught.value)

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.knowledge_routes import get_knowledge_service
from app.main import app
from app.services.knowledge import KnowledgeError, KnowledgeService


def _service(tmp_path: Path) -> KnowledgeService:
    return KnowledgeService(
        db_path=tmp_path / "app.sqlite3",
        data_root=tmp_path / "data",
    )


def test_local_collection_full_lifecycle(tmp_path: Path) -> None:
    service = _service(tmp_path)
    collection = service.create_collection("Transporter notes")

    added = service.add_document(
        collection["collection_id"],
        "notes.md",
        b"# Transporters\n\nP-glycoprotein can affect drug disposition.",
        rights_basis="created_by_user",
    )
    document = added["document"]
    first = service.search(collection["collection_id"], "P-glycoprotein disposition")

    assert added["duplicate"] is False
    assert first["evidence_label"] == "user_provided"
    assert first["matches"][0]["document_id"] == document["document_id"]
    assert first["matches"][0]["chunk_id"].startswith("user_chunk_")

    replaced = service.replace_document(
        collection["collection_id"],
        document["document_id"],
        "notes.md",
        b"# Clearance\n\nRenal clearance is the updated topic.",
        rights_basis="created_by_user",
    )
    assert replaced["document"]["revision"] == 2
    assert service.search(collection["collection_id"], "P-glycoprotein")["matches"] == []
    assert service.search(collection["collection_id"], "renal clearance")["matches"]

    service.delete_document(collection["collection_id"], document["document_id"])
    assert service.get_collection(collection["collection_id"])["documents"] == []
    assert service.search(collection["collection_id"], "renal clearance")["matches"] == []

    service.delete_collection(collection["collection_id"])
    with pytest.raises(KnowledgeError, match="Collection was not found"):
        service.get_collection(collection["collection_id"])


def test_duplicate_and_file_validation_are_explicit(tmp_path: Path) -> None:
    service = _service(tmp_path)
    collection_id = service.create_collection("Local papers")["collection_id"]
    content = b"A deterministic local reference."

    first = service.add_document(
        collection_id,
        "reference.txt",
        content,
        rights_basis="permission_or_license",
    )
    duplicate = service.add_document(
        collection_id,
        "renamed.txt",
        content,
        rights_basis="permission_or_license",
    )

    assert duplicate["duplicate"] is True
    assert duplicate["document"]["document_id"] == first["document"]["document_id"]
    assert len(service.get_collection(collection_id)["documents"]) == 1

    invalid_files = (
        ("paper.pdf", b"not a pdf", "KNOWLEDGE_FILE_TYPE_UNSUPPORTED"),
        ("../notes.txt", b"path-like", "KNOWLEDGE_FILENAME_INVALID"),
        ("notes.txt", b"\xff", "KNOWLEDGE_ENCODING_UNSUPPORTED"),
    )
    for filename, payload, code in invalid_files:
        with pytest.raises(KnowledgeError) as caught:
            service.add_document(
                collection_id,
                filename,
                payload,
                rights_basis="created_by_user",
            )
        assert caught.value.code == code


def test_failed_rebuild_keeps_the_last_readable_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path)
    collection_id = service.create_collection("Failure test")["collection_id"]
    document = service.add_document(
        collection_id,
        "stable.txt",
        b"The stable indexed passage.",
        rights_basis="created_by_user",
    )["document"]

    def fail_index(*_args: object, **_kwargs: object) -> Path:
        raise OSError("injected index failure")

    monkeypatch.setattr(service, "_persist_index", fail_index)
    with pytest.raises(KnowledgeError) as caught:
        service.replace_document(
            collection_id,
            document["document_id"],
            "stable.txt",
            b"A replacement that must not become active.",
            rights_basis="created_by_user",
        )

    assert caught.value.code == "KNOWLEDGE_INDEX_FAILED"
    current = service.get_document(collection_id, document["document_id"])
    assert current["revision"] == 1
    assert service.search(collection_id, "stable indexed passage")["matches"]
    assert service.search(collection_id, "replacement")["matches"] == []


def test_no_key_api_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_ENABLED", "false")
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("ADME_DATA_DIR", str(tmp_path / "data"))
    get_knowledge_service.cache_clear()
    client = TestClient(app)

    created = client.post("/knowledge/collections", json={"name": "API notes"})
    assert created.status_code == 200
    collection_id = created.json()["collection_id"]

    uploaded = client.post(
        f"/knowledge/collections/{collection_id}/documents",
        data={"rights_basis": "created_by_user"},
        files={"file": ("notes.txt", b"Mass balance studies track administered material.", "text/plain")},
    )
    assert uploaded.status_code == 200

    searched = client.post(
        f"/knowledge/collections/{collection_id}/search",
        json={"query": "mass balance", "top_k": 3},
    )
    assert searched.status_code == 200
    assert searched.json()["matches"][0]["display_name"] == "notes.txt"
    get_knowledge_service.cache_clear()


from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import threading
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from app.agent_runtime.repositories import AgentRepository


MAX_COLLECTIONS = 10
MAX_DOCUMENTS_PER_COLLECTION = 100
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_COLLECTION_BYTES = 25 * 1024 * 1024
MAX_FILENAME_CHARS = 120
MAX_QUERY_CHARS = 2_000
MAX_TOP_K = 5
CHUNK_CHARS = 1_200
CHUNK_OVERLAP = 200
INDEX_SCHEMA_VERSION = 1
RIGHTS_BASES = {
    "created_by_user",
    "permission_or_license",
    "public_domain",
    "other_authorized_research_use",
}
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class KnowledgeError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class KnowledgeService:
    def __init__(self, db_path: str | Path, data_root: str | Path):
        self.repository = AgentRepository(db_path)
        self.root = Path(data_root) / "knowledge"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @classmethod
    def from_environment(cls) -> "KnowledgeService":
        return cls(
            db_path=os.getenv("AGENT_DB_PATH", "data/agent.sqlite3"),
            data_root=os.getenv("ADME_DATA_DIR", "data"),
        )

    def create_collection(self, name: str) -> dict[str, Any]:
        display_name = " ".join(name.split())
        if not display_name or len(display_name) > 120:
            raise KnowledgeError(
                "KNOWLEDGE_COLLECTION_NAME_INVALID",
                "Collection names must contain 1 to 120 characters.",
            )
        with self._lock, self.repository.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM knowledge_collections"
            ).fetchone()[0]
            if count >= MAX_COLLECTIONS:
                raise KnowledgeError(
                    "KNOWLEDGE_COLLECTION_LIMIT",
                    f"At most {MAX_COLLECTIONS} local collections are supported.",
                    409,
                )
            collection_id = f"collection_{uuid4().hex}"
            now = _now()
            connection.execute(
                """INSERT INTO knowledge_collections
                   VALUES (?, ?, 'ready', 'local_only', 0, ?, ?)""",
                (collection_id, display_name, now, now),
            )
            connection.commit()
        return self.get_collection(collection_id)

    def list_collections(self) -> list[dict[str, Any]]:
        with self.repository.connection() as connection:
            rows = connection.execute(
                "SELECT collection_id FROM knowledge_collections ORDER BY created_at, collection_id"
            ).fetchall()
        return [self.get_collection(row["collection_id"]) for row in rows]

    def get_collection(self, collection_id: str) -> dict[str, Any]:
        with self.repository.connection() as connection:
            collection = connection.execute(
                "SELECT * FROM knowledge_collections WHERE collection_id = ?",
                (collection_id,),
            ).fetchone()
            if collection is None:
                raise KnowledgeError(
                    "KNOWLEDGE_COLLECTION_NOT_FOUND", "Collection was not found.", 404
                )
            documents = connection.execute(
                """SELECT * FROM knowledge_documents WHERE collection_id = ?
                   ORDER BY created_at, document_id""",
                (collection_id,),
            ).fetchall()
        document_values = [_document_contract(row) for row in documents]
        return {
            **dict(collection),
            "document_count": len(document_values),
            "normalized_bytes": sum(item["normalized_bytes"] for item in document_values),
            "documents": document_values,
        }

    def get_document(self, collection_id: str, document_id: str) -> dict[str, Any]:
        with self.repository.connection() as connection:
            row = connection.execute(
                """SELECT * FROM knowledge_documents
                   WHERE collection_id = ? AND document_id = ?""",
                (collection_id, document_id),
            ).fetchone()
        if row is None:
            self.get_collection(collection_id)
            raise KnowledgeError(
                "KNOWLEDGE_DOCUMENT_NOT_FOUND", "Document was not found.", 404
            )
        return _document_contract(row)

    def add_document(
        self,
        collection_id: str,
        filename: str,
        content: bytes,
        *,
        rights_basis: str,
        source_url: str | None = None,
    ) -> dict[str, Any]:
        upload = _validate_upload(filename, content, rights_basis, source_url)
        with self._lock:
            collection = self.get_collection(collection_id)
            duplicate = next(
                (
                    document
                    for document in collection["documents"]
                    if document["sha256"] == upload["sha256"]
                ),
                None,
            )
            if duplicate is not None:
                return {"duplicate": True, "document": duplicate}
            if collection["document_count"] >= MAX_DOCUMENTS_PER_COLLECTION:
                raise KnowledgeError(
                    "KNOWLEDGE_DOCUMENT_LIMIT",
                    f"A collection may contain at most {MAX_DOCUMENTS_PER_COLLECTION} documents.",
                    409,
                )
            if collection["normalized_bytes"] + upload["normalized_bytes"] > MAX_COLLECTION_BYTES:
                raise KnowledgeError(
                    "KNOWLEDGE_COLLECTION_SIZE_LIMIT",
                    "The collection would exceed its 25 MiB normalized-text limit.",
                    409,
                )

            document_id = f"document_{uuid4().hex}"
            now = _now()
            document = {
                "document_id": document_id,
                "collection_id": collection_id,
                "display_name": upload["display_name"],
                "media_type": upload["media_type"],
                "size_bytes": len(content),
                "normalized_bytes": upload["normalized_bytes"],
                "sha256": upload["sha256"],
                "revision": 1,
                "state": "ready",
                "rights_basis": rights_basis,
                "source_url": upload["source_url"],
                "created_at": now,
                "updated_at": now,
                "text": upload["text"],
            }
            revision_path = self._write_revision(document, content)
            proposed = self._documents_with_text(
                collection_id, collection["documents"]
            ) + [document]
            try:
                index = self._prepare_index(
                    collection_id, collection["active_index_version"] + 1, proposed
                )
                with self.repository.connection() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        """INSERT INTO knowledge_documents
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        _document_values(document),
                    )
                    self._activate_index(connection, collection_id, index)
                    connection.commit()
            except Exception:
                shutil.rmtree(revision_path, ignore_errors=True)
                raise
            self._cleanup_inactive_indexes(collection_id, index["version"])
            return {"duplicate": False, "document": self.get_document(collection_id, document_id)}

    def replace_document(
        self,
        collection_id: str,
        document_id: str,
        filename: str,
        content: bytes,
        *,
        rights_basis: str,
        source_url: str | None = None,
    ) -> dict[str, Any]:
        upload = _validate_upload(filename, content, rights_basis, source_url)
        with self._lock:
            collection = self.get_collection(collection_id)
            current = self.get_document(collection_id, document_id)
            if upload["sha256"] == current["sha256"]:
                return {"duplicate": True, "document": current}
            if any(
                document["document_id"] != document_id
                and document["sha256"] == upload["sha256"]
                for document in collection["documents"]
            ):
                raise KnowledgeError(
                    "KNOWLEDGE_DUPLICATE_DOCUMENT",
                    "The replacement duplicates another document in this collection.",
                    409,
                )
            new_total = (
                collection["normalized_bytes"]
                - current["normalized_bytes"]
                + upload["normalized_bytes"]
            )
            if new_total > MAX_COLLECTION_BYTES:
                raise KnowledgeError(
                    "KNOWLEDGE_COLLECTION_SIZE_LIMIT",
                    "The collection would exceed its 25 MiB normalized-text limit.",
                    409,
                )

            updated = {
                **current,
                "display_name": upload["display_name"],
                "media_type": upload["media_type"],
                "size_bytes": len(content),
                "normalized_bytes": upload["normalized_bytes"],
                "sha256": upload["sha256"],
                "revision": current["revision"] + 1,
                "rights_basis": rights_basis,
                "source_url": upload["source_url"] if source_url is not None else current["source_url"],
                "updated_at": _now(),
                "text": upload["text"],
            }
            revision_path = self._write_revision(updated, content)
            proposed = [
                updated if item["document_id"] == document_id else item
                for item in self._documents_with_text(
                    collection_id, collection["documents"]
                )
            ]
            try:
                index = self._prepare_index(
                    collection_id, collection["active_index_version"] + 1, proposed
                )
                with self.repository.connection() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        """UPDATE knowledge_documents
                           SET display_name=?, media_type=?, size_bytes=?, normalized_bytes=?,
                               sha256=?, revision=?, rights_basis=?, source_url=?, updated_at=?
                           WHERE collection_id=? AND document_id=?""",
                        (
                            updated["display_name"],
                            updated["media_type"],
                            updated["size_bytes"],
                            updated["normalized_bytes"],
                            updated["sha256"],
                            updated["revision"],
                            updated["rights_basis"],
                            updated["source_url"],
                            updated["updated_at"],
                            collection_id,
                            document_id,
                        ),
                    )
                    self._activate_index(connection, collection_id, index)
                    connection.commit()
            except Exception:
                shutil.rmtree(revision_path, ignore_errors=True)
                raise
            old_revision = self._revision_path(collection_id, document_id, current["revision"])
            shutil.rmtree(old_revision, ignore_errors=True)
            self._cleanup_inactive_indexes(collection_id, index["version"])
            return {"duplicate": False, "document": self.get_document(collection_id, document_id)}

    def delete_document(self, collection_id: str, document_id: str) -> dict[str, Any]:
        with self._lock:
            collection = self.get_collection(collection_id)
            self.get_document(collection_id, document_id)
            proposed = [
                item
                for item in self._documents_with_text(
                    collection_id, collection["documents"]
                )
                if item["document_id"] != document_id
            ]
            index = self._prepare_index(
                collection_id, collection["active_index_version"] + 1, proposed
            )
            with self.repository.connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "DELETE FROM knowledge_documents WHERE collection_id=? AND document_id=?",
                    (collection_id, document_id),
                )
                self._activate_index(connection, collection_id, index)
                connection.commit()
            shutil.rmtree(self._document_root(collection_id, document_id), ignore_errors=True)
            self._cleanup_inactive_indexes(collection_id, index["version"])
            return {"deleted": True, "collection_id": collection_id, "document_id": document_id}

    def delete_collection(self, collection_id: str) -> dict[str, Any]:
        with self._lock:
            collection = self.get_collection(collection_id)
            with self.repository.connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "DELETE FROM knowledge_collections WHERE collection_id = ?",
                    (collection_id,),
                )
                connection.commit()
            shutil.rmtree(self._collection_root(collection_id), ignore_errors=True)
        return {
            "deleted": True,
            "collection_id": collection_id,
            "document_count": collection["document_count"],
        }

    def reindex(self, collection_id: str) -> dict[str, Any]:
        with self._lock:
            collection = self.get_collection(collection_id)
            proposed = self._documents_with_text(
                collection_id, collection["documents"]
            )
            index = self._prepare_index(
                collection_id, collection["active_index_version"] + 1, proposed
            )
            with self.repository.connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._activate_index(connection, collection_id, index)
                connection.commit()
            self._cleanup_inactive_indexes(collection_id, index["version"])
            return self.get_collection(collection_id)

    def search(self, collection_id: str, query: str, top_k: int = 3) -> dict[str, Any]:
        normalized_query = " ".join(query.split())
        if not normalized_query or len(normalized_query) > MAX_QUERY_CHARS:
            raise KnowledgeError(
                "KNOWLEDGE_QUERY_INVALID",
                f"Search queries must contain 1 to {MAX_QUERY_CHARS} characters.",
            )
        bounded_top_k = max(1, min(top_k, MAX_TOP_K))
        collection = self.get_collection(collection_id)
        with self.repository.connection() as connection:
            rows = connection.execute(
                """SELECT c.*, d.display_name, d.source_url, d.rights_basis
                   FROM knowledge_chunks c
                   JOIN knowledge_documents d
                     ON d.collection_id = c.collection_id AND d.document_id = c.document_id
                   WHERE c.collection_id = ? AND c.index_version = ?""",
                (collection_id, collection["active_index_version"]),
            ).fetchall()
        tokens = _tokenize(normalized_query)
        ranked = _rank(tokens, [dict(row) for row in rows]) if tokens else []
        matches = [
            {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "document_revision": row["document_revision"],
                "display_name": row["display_name"],
                "source_url": row["source_url"],
                "rights_basis": row["rights_basis"],
                "position": row["position"],
                "excerpt": row["excerpt"],
                "score": round(score, 6),
            }
            for score, row in ranked[:bounded_top_k]
            if score > 0
        ]
        return {
            "query": normalized_query,
            "collection_id": collection_id,
            "index_version": collection["active_index_version"],
            "evidence_label": "user_provided",
            "matches": matches,
        }

    def _documents_with_text(
        self, collection_id: str, documents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        values = []
        for document in documents:
            path = self._revision_path(
                collection_id, document["document_id"], document["revision"]
            ) / "normalized.txt"
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise KnowledgeError(
                    "KNOWLEDGE_STORAGE_ERROR",
                    "A stored document could not be read.",
                    500,
                ) from exc
            values.append({**document, "text": text})
        return values

    def _write_revision(self, document: dict[str, Any], source: bytes) -> Path:
        target = self._revision_path(
            document["collection_id"], document["document_id"], document["revision"]
        )
        temporary = target.parent / f".tmp-{uuid4().hex}"
        try:
            temporary.mkdir(parents=True)
            (temporary / "source").write_bytes(source)
            (temporary / "normalized.txt").write_text(document["text"], encoding="utf-8")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary.replace(target)
        except OSError as exc:
            shutil.rmtree(temporary, ignore_errors=True)
            raise KnowledgeError(
                "KNOWLEDGE_STORAGE_ERROR", "The document could not be stored.", 500
            ) from exc
        return target

    def _build_index(
        self,
        collection_id: str,
        version: int,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        document_refs = [
            {
                "document_id": item["document_id"],
                "revision": item["revision"],
                "sha256": item["sha256"],
            }
            for item in sorted(documents, key=lambda value: value["document_id"])
        ]
        chunks: list[dict[str, Any]] = []
        for document in sorted(documents, key=lambda value: value["document_id"]):
            for position, excerpt in _chunks(document["text"]):
                token_counts = Counter(_tokenize(excerpt))
                location = f"{document['document_id']}\0{document['revision']}\0{position}\0{excerpt}"
                chunks.append(
                    {
                        "chunk_id": "user_chunk_"
                        + hashlib.sha256(location.encode()).hexdigest()[:20],
                        "document_id": document["document_id"],
                        "document_revision": document["revision"],
                        "position": position,
                        "excerpt": excerpt,
                        "excerpt_hash": hashlib.sha256(excerpt.encode()).hexdigest(),
                        "tokens": dict(sorted(token_counts.items())),
                        "length": sum(token_counts.values()),
                    }
                )
        digest = hashlib.sha256(_canonical(document_refs)).hexdigest()
        return {
            "schema_version": INDEX_SCHEMA_VERSION,
            "collection_id": collection_id,
            "version": version,
            "source_digest": digest,
            "retrieval_config": {
                "algorithm": "lexical_bm25_v1",
                "chunk_chars": CHUNK_CHARS,
                "overlap_chars": CHUNK_OVERLAP,
            },
            "created_at": _now(),
            "documents": document_refs,
            "chunks": chunks,
        }

    def _prepare_index(
        self,
        collection_id: str,
        version: int,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        index = self._build_index(collection_id, version, documents)
        try:
            self._persist_index(collection_id, index)
        except OSError as exc:
            raise KnowledgeError(
                "KNOWLEDGE_INDEX_FAILED",
                "The collection index could not be rebuilt; the previous index remains active.",
                500,
            ) from exc
        return index

    def _persist_index(self, collection_id: str, index: dict[str, Any]) -> Path:
        index_root = self._collection_root(collection_id) / "indexes"
        target = index_root / str(index["version"])
        temporary = index_root / f".tmp-{uuid4().hex}"
        try:
            if target.exists():
                shutil.rmtree(target)
            temporary.mkdir(parents=True)
            rendered = json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            (temporary / "index.json").write_text(rendered, encoding="utf-8")
            json.loads((temporary / "index.json").read_text(encoding="utf-8"))
            temporary.replace(target)
        except OSError:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return target

    def _activate_index(
        self,
        connection: Any,
        collection_id: str,
        index: dict[str, Any],
    ) -> None:
        connection.execute(
            """INSERT INTO knowledge_index_versions
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                collection_id,
                index["version"],
                index["schema_version"],
                index["source_digest"],
                json.dumps(index["retrieval_config"], sort_keys=True),
                index["created_at"],
            ),
        )
        connection.executemany(
            """INSERT INTO knowledge_chunks
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    collection_id,
                    index["version"],
                    chunk["chunk_id"],
                    chunk["document_id"],
                    chunk["document_revision"],
                    chunk["position"],
                    chunk["excerpt"],
                    chunk["excerpt_hash"],
                    json.dumps(chunk["tokens"], sort_keys=True),
                    chunk["length"],
                )
                for chunk in index["chunks"]
            ],
        )
        connection.execute(
            """UPDATE knowledge_collections
               SET active_index_version = ?, updated_at = ?
               WHERE collection_id = ?""",
            (index["version"], index["created_at"], collection_id),
        )
        connection.execute(
            """DELETE FROM knowledge_index_versions
               WHERE collection_id = ? AND version <> ?""",
            (collection_id, index["version"]),
        )

    def _cleanup_inactive_indexes(self, collection_id: str, active_version: int) -> None:
        index_root = self._collection_root(collection_id) / "indexes"
        if not index_root.exists():
            return
        for path in index_root.iterdir():
            if path.name != str(active_version):
                shutil.rmtree(path, ignore_errors=True)

    def _collection_root(self, collection_id: str) -> Path:
        return self.root / "collections" / collection_id

    def _document_root(self, collection_id: str, document_id: str) -> Path:
        return self._collection_root(collection_id) / "documents" / document_id

    def _revision_path(self, collection_id: str, document_id: str, revision: int) -> Path:
        return self._document_root(collection_id, document_id) / "revisions" / str(revision)

def _validate_upload(
    filename: str,
    content: bytes,
    rights_basis: str,
    source_url: str | None,
) -> dict[str, Any]:
    if (
        not filename
        or len(filename) > MAX_FILENAME_CHARS
        or Path(filename).name != filename
        or "/" in filename
        or "\\" in filename
        or "\0" in filename
    ):
        raise KnowledgeError(
            "KNOWLEDGE_FILENAME_INVALID",
            f"Filenames must contain at most {MAX_FILENAME_CHARS} characters and no path.",
        )
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".md"}:
        raise KnowledgeError(
            "KNOWLEDGE_FILE_TYPE_UNSUPPORTED",
            "Use a UTF-8 .txt or .md file.",
        )
    if not content:
        raise KnowledgeError("KNOWLEDGE_FILE_EMPTY", "The selected file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise KnowledgeError(
            "KNOWLEDGE_FILE_TOO_LARGE", "Files must be 2 MiB or smaller."
        )
    try:
        text = content.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").strip()
    except UnicodeDecodeError as exc:
        raise KnowledgeError(
            "KNOWLEDGE_ENCODING_UNSUPPORTED", "Use a UTF-8 encoded file."
        ) from exc
    if not text:
        raise KnowledgeError("KNOWLEDGE_FILE_EMPTY", "The selected file has no text.")
    if rights_basis not in RIGHTS_BASES:
        raise KnowledgeError(
            "KNOWLEDGE_RIGHTS_BASIS_INVALID", "Select a supported rights basis."
        )
    normalized_url = _validate_source_url(source_url)
    return {
        "display_name": filename,
        "media_type": "text/markdown" if suffix == ".md" else "text/plain",
        "text": text,
        "normalized_bytes": len(text.encode("utf-8")),
        "sha256": hashlib.sha256(content).hexdigest(),
        "source_url": normalized_url,
    }


def _validate_source_url(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if len(normalized) > 2_000 or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise KnowledgeError(
            "KNOWLEDGE_SOURCE_URL_INVALID", "Source URLs must use http or https."
        )
    return normalized


def _document_values(document: dict[str, Any]) -> tuple[Any, ...]:
    return (
        document["document_id"],
        document["collection_id"],
        document["display_name"],
        document["media_type"],
        document["size_bytes"],
        document["normalized_bytes"],
        document["sha256"],
        document["revision"],
        document["state"],
        document["rights_basis"],
        document["source_url"],
        document["created_at"],
        document["updated_at"],
    )


def _document_contract(row: Any) -> dict[str, Any]:
    value = dict(row)
    return {
        key: value[key]
        for key in (
            "document_id",
            "collection_id",
            "display_name",
            "media_type",
            "size_bytes",
            "normalized_bytes",
            "sha256",
            "revision",
            "state",
            "rights_basis",
            "source_url",
            "created_at",
            "updated_at",
        )
    }


def _chunks(text: str) -> list[tuple[int, str]]:
    if len(text) <= CHUNK_CHARS:
        return [(0, text)]
    result: list[tuple[int, str]] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start + CHUNK_CHARS // 2, end), text.rfind(" ", start + CHUNK_CHARS // 2, end))
            if boundary > start:
                end = boundary
        excerpt = text[start:end].strip()
        if excerpt:
            result.append((start, excerpt))
        if end >= len(text):
            break
        start = max(start + 1, end - CHUNK_OVERLAP)
    return result


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _rank(query_tokens: list[str], chunks: list[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
    if not chunks:
        return []
    average_length = sum(row["length"] for row in chunks) / len(chunks)
    frequencies = {
        token: sum(token in json.loads(row["tokens_json"]) for row in chunks)
        for token in set(query_tokens)
    }
    ranked = []
    for row in chunks:
        counts = json.loads(row["tokens_json"])
        score = 0.0
        for token in query_tokens:
            frequency = counts.get(token, 0)
            if not frequency:
                continue
            document_frequency = frequencies[token]
            inverse = math.log(
                1 + (len(chunks) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = frequency + 1.5 * (
                0.25 + 0.75 * row["length"] / max(average_length, 1)
            )
            score += inverse * frequency * 2.5 / denominator
        ranked.append((score, row))
    return sorted(ranked, key=lambda item: (-item[0], item[1]["chunk_id"]))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _now() -> str:
    return datetime.now(UTC).isoformat()

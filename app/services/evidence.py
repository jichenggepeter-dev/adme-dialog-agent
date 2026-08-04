from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / "resources" / "evidence" / "index.json"
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?%?")
CLAUSE_RE = re.compile(r"\s+(?:and|以及|和)\s+", re.IGNORECASE)
PROHIBITED_PATTERNS = (
    "safe for",
    "safest",
    "diagnose",
    "diagnosis",
    "treat my",
    "treatment for",
    "what dose",
    "dosing recommendation",
    "rank compounds",
    "rank these",
    "best compound",
    "recommend a compound",
    "for my patient",
    "患者",
    "剂量",
    "诊断",
    "治疗建议",
    "最安全",
    "给化合物排名",
    "推荐化合物",
)
SEARCH_STOP_WORDS = {
    "about",
    "corpus",
    "does",
    "document",
    "fda",
    "guidance",
    "say",
    "show",
    "the",
    "these",
    "this",
    "what",
    "when",
    "with",
}


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class EvidenceService:
    def __init__(
        self,
        index_path: Path = DEFAULT_INDEX,
        *,
        index_data: dict[str, Any] | None = None,
    ) -> None:
        self.index_path = index_path
        self.index_data = deepcopy(index_data) if index_data is not None else None

    def search(self, query: str, top_k: int = 3) -> dict[str, Any]:
        normalized = " ".join(query.split())
        lowered = normalized.lower()
        if any(pattern in lowered for pattern in PROHIBITED_PATTERNS):
            return self._empty(
                normalized,
                "prohibited",
                "This evidence workflow cannot provide diagnosis, dosing, clinical safety conclusions, compound ranking, or treatment recommendations.",
            )

        try:
            index = self._load_index()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return self._empty(
                normalized,
                "no_evidence",
                "The local evidence index is unavailable. The prediction workflow remains available independently.",
                availability="unavailable",
                warnings=[f"Evidence index unavailable: {type(exc).__name__}."],
            )

        documents = index["documents"]
        query_tokens = [token for token in tokenize(normalized) if token not in SEARCH_STOP_WORDS]
        if not query_tokens:
            return self._empty(normalized, "no_evidence", "No searchable evidence terms were provided.")
        ranked = self._rank(query_tokens, documents)
        matches = [
            item
            for item in ranked
            if item[0] >= 0.2
            and len(set(query_tokens) & set(item[1]["tokens"])) >= min(2, len(set(query_tokens)))
        ][: max(1, min(top_k, 5))]
        if not matches:
            return self._empty(
                normalized,
                "no_evidence",
                "No adequate passage was found in the approved local evidence corpus.",
            )

        stale_request = any(term in query_tokens for term in ("withdrawn", "superseded", "obsolete"))
        if stale_request:
            stale = [item for item in matches if item[1]["status"] != "current"]
            if stale:
                evidence = [self._citation(document) for _, document in stale]
                return {
                    **self._empty(
                        normalized,
                        "stale_only",
                        "Only superseded or non-current evidence matched. It is shown for provenance and must not be used as current guidance.",
                    ),
                    "evidence": evidence,
                    "source_count": len({item["source_id"] for item in evidence}),
                }

        current = [item for item in matches if item[1]["status"] == "current"]
        if not current:
            evidence = [self._citation(document) for _, document in matches]
            return {
                **self._empty(
                    normalized,
                    "stale_only",
                    "Only superseded or non-current evidence matched. It is shown for provenance and must not be used as current guidance.",
                ),
                "evidence": evidence,
                "source_count": len({item["source_id"] for item in evidence}),
            }

        documents_used = [document for _, document in current]
        status = "conflicting" if self._has_conflict(documents_used) else "supported"
        clauses = [clause for clause in CLAUSE_RE.split(lowered) if clause.strip()]
        if status == "supported" and len(clauses) > 1:
            coverage = [self._clause_covered(clause, documents) for clause in clauses]
            if any(coverage) and not all(coverage):
                status = "partial"

        evidence = [self._citation(document) for document in documents_used]
        claims = []
        for document, citation in zip(documents_used, evidence, strict=True):
            claim = document["claim"]
            if self._numbers_supported(claim, [citation["excerpt"]]):
                claims.append({"text": claim, "evidence": [citation]})
        if not claims:
            return self._empty(
                normalized,
                "no_evidence",
                "Retrieved passages could not support a traceable claim, so the workflow abstained.",
            )

        summary = {
            "supported": "Current indexed FDA evidence supports the bounded claims below.",
            "partial": "Only part of the question is covered by current indexed FDA evidence.",
            "conflicting": "Current indexed passages conflict. The competing claims are shown without a single synthesized conclusion.",
        }[status]
        return {
            "query": normalized,
            "status": status,
            "availability": "available",
            "assistant_summary": summary,
            "claims": claims,
            "evidence": evidence,
            "source_count": len({item["source_id"] for item in evidence}),
            "warnings": [],
        }

    def _load_index(self) -> dict[str, Any]:
        index = self.index_data
        if index is None:
            index = json.loads(self.index_path.read_text(encoding="utf-8"))
        if index.get("schema_version") != 1 or not isinstance(index.get("documents"), list):
            raise ValueError("Invalid evidence index.")
        required = {"chunk_id", "source_id", "title", "url", "status", "tokens", "excerpt", "claim"}
        if any(not required.issubset(document) for document in index["documents"]):
            raise ValueError("Invalid evidence document.")
        return index

    @staticmethod
    def _rank(query_tokens: list[str], documents: list[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
        total = len(documents)
        average_length = sum(document["length"] for document in documents) / max(total, 1)
        document_frequency = {
            token: sum(1 for document in documents if token in document["tokens"])
            for token in set(query_tokens)
        }
        ranked = []
        for document in documents:
            score = 0.0
            for token in query_tokens:
                frequency = document["tokens"].get(token, 0)
                if not frequency:
                    continue
                df = document_frequency[token]
                inverse = math.log(1 + (total - df + 0.5) / (df + 0.5))
                denominator = frequency + 1.5 * (0.25 + 0.75 * document["length"] / max(average_length, 1))
                score += inverse * frequency * 2.5 / denominator
            ranked.append((score, document))
        return sorted(ranked, key=lambda item: (-item[0], item[1]["chunk_id"]))

    @staticmethod
    def _clause_covered(clause: str, documents: list[dict[str, Any]]) -> bool:
        meaningful = {
            token
            for token in tokenize(clause)
            if len(token) > 2 and token not in SEARCH_STOP_WORDS
        }
        if not meaningful:
            return False
        corpus_tokens = set().union(*(set(document["tokens"]) for document in documents))
        covered = meaningful & corpus_tokens
        return bool(covered) and len(meaningful - corpus_tokens) < 2

    @staticmethod
    def _has_conflict(documents: list[dict[str, Any]]) -> bool:
        grouped: dict[str, set[str]] = {}
        for document in documents:
            group = document.get("conflict_group")
            stance = document.get("stance")
            if group and stance:
                grouped.setdefault(group, set()).add(stance)
        return any(len(stances) > 1 for stances in grouped.values())

    @staticmethod
    def _numbers_supported(claim: str, excerpts: list[str]) -> bool:
        claim_numbers = set(NUMBER_RE.findall(claim))
        evidence_numbers = set(NUMBER_RE.findall(" ".join(excerpts)))
        return claim_numbers <= evidence_numbers

    @staticmethod
    def _citation(document: dict[str, Any]) -> dict[str, Any]:
        return {
            key: document.get(key)
            for key in (
                "source_id",
                "title",
                "organization",
                "url",
                "document_date",
                "version",
                "status",
                "captured_at",
                "section",
                "page",
                "chunk_id",
                "excerpt",
            )
        }

    @staticmethod
    def _empty(
        query: str,
        status: str,
        summary: str,
        *,
        availability: str = "available",
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "status": status,
            "availability": availability,
            "assistant_summary": summary,
            "claims": [],
            "evidence": [],
            "source_count": 0,
            "warnings": warnings or [],
        }


def search_evidence(query: str, top_k: int = 3) -> dict[str, Any]:
    return EvidenceService().search(query, top_k)

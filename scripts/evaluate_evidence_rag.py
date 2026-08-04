from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.evidence import EvidenceService


QUESTIONS = ROOT / "evaluation" / "evidence_rag_questions.json"
INDEX = ROOT / "resources" / "evidence" / "index.json"


def _conflict_index(base: dict) -> dict:
    index = deepcopy(base)
    common = {
        "source_id": "synthetic-conflict-fixture",
        "title": "Synthetic conflict fixture",
        "organization": "Test fixture only",
        "url": "https://example.invalid/evidence-conflict-fixture",
        "document_date": "2026-08-03",
        "version": "test",
        "status": "current",
        "topics": ["synthetic", "clearance", "conflict"],
        "captured_at": "2026-08-03",
        "content_sha256": "fixture",
        "section": "test fixture",
        "page": None,
        "conflict_group": "synthetic-clearance",
    }
    index["documents"] = [
        {**common, "chunk_id": "fixture:support", "claim": "Synthetic evidence supports the clearance statement.", "excerpt": "Synthetic evidence supports the clearance statement.", "tokens": {"synthetic": 2, "clearance": 2, "conflict": 1, "supports": 2, "statement": 2}, "length": 9, "stance": "support"},
        {**common, "chunk_id": "fixture:oppose", "claim": "Synthetic evidence opposes the clearance statement.", "excerpt": "Synthetic evidence opposes the clearance statement.", "tokens": {"synthetic": 2, "clearance": 2, "conflict": 1, "opposes": 2, "statement": 2}, "length": 9, "stance": "oppose"},
    ]
    return index


def evaluate() -> dict[str, float | int]:
    cases = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    base = json.loads(INDEX.read_text(encoding="utf-8"))
    status_hits = retrieval_hits = citation_hits = 0
    retrieval_cases = 0
    abstention_hits = abstention_cases = 0
    for case in cases:
        service = EvidenceService(index_data=_conflict_index(base) if case.get("fixture") == "conflict" else base)
        result = service.search(case["question"])
        status_hits += result["status"] == case["expected_status"]
        expected_source = case.get("expected_source_id")
        if expected_source:
            retrieval_cases += 1
            retrieval_hits += any(item["source_id"] == expected_source for item in result["evidence"])
        citation_hits += all(claim["evidence"] for claim in result["claims"])
        if case["expected_status"] in {"no_evidence", "prohibited", "stale_only"}:
            abstention_cases += 1
            abstention_hits += not result["claims"]
    total = len(cases)
    return {
        "question_count": total,
        "status_accuracy": status_hits / total,
        "retrieval_relevance": retrieval_hits / max(retrieval_cases, 1),
        "citation_support": citation_hits / total,
        "abstention_accuracy": abstention_hits / max(abstention_cases, 1),
    }


def main() -> int:
    metrics = evaluate()
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0 if metrics["status_accuracy"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

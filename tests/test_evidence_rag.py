from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.guardrails import validate_scientific_output
from app.agent_runtime.tool_service import AgentToolService, ToolExecutionContext
from app.services.evidence import EvidenceService
from scripts.build_evidence_index import DEFAULT_CORPUS, rendered_index
from scripts.evaluate_evidence_rag import evaluate


def test_index_rebuild_is_byte_for_byte_deterministic() -> None:
    first = rendered_index(DEFAULT_CORPUS)
    second = rendered_index(DEFAULT_CORPUS)
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_supported_claim_has_claim_level_provenance_and_numeric_span() -> None:
    result = EvidenceService().search(
        "What does FDA say about human radiolabeled mass balance study design and reporting?"
    )
    assert result["status"] == "supported"
    claim = result["claims"][0]
    citation = claim["evidence"][0]
    assert citation["source_id"] == "fda-mass-balance-2024"
    assert citation["chunk_id"].startswith("fda-mass-balance-2024:")
    assert citation["section"]
    for token in ("1", "2", "3"):
        assert token in citation["excerpt"]


def test_missing_corrupt_prohibited_partial_and_stale_states(tmp_path: Path) -> None:
    missing = EvidenceService(index_path=tmp_path / "missing.json").search("mass balance")
    assert missing["status"] == "no_evidence"
    assert missing["availability"] == "unavailable"

    corrupt_path = tmp_path / "corrupt.json"
    corrupt_path.write_text("not-json", encoding="utf-8")
    corrupt = EvidenceService(index_path=corrupt_path).search("mass balance")
    assert corrupt["status"] == "no_evidence"

    prohibited = EvidenceService().search("What dose should I give my patient?")
    assert prohibited["status"] == "prohibited"
    assert prohibited["claims"] == []

    partial = EvidenceService().search(
        "What does FDA say about human radiolabeled mass balance studies and Martian weather?"
    )
    assert partial["status"] == "partial"

    stale = EvidenceService().search(
        "Show the withdrawn 2020 in vitro drug interaction guidance record."
    )
    assert stale["status"] == "stale_only"
    assert stale["claims"] == []
    assert all(item["status"] == "superseded" for item in stale["evidence"])


def test_source_lifecycle_is_applied_before_ranking_cutoff() -> None:
    current = EvidenceService().search(
        "What FDA guidance covers enzyme and transporter mediated drug interactions?",
        top_k=1,
    )
    historical = EvidenceService().search(
        "Which superseded 2020 record covers CYP450 interactions?",
        top_k=1,
    )

    assert current["evidence"][0]["source_id"] == "fda-m12-2024"
    assert historical["evidence"][0]["source_id"] == "fda-in-vitro-ddi-2020-withdrawn"


def test_agent_tool_emits_strict_evidence_payload(tmp_path: Path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    context = ToolExecutionContext(session["session_id"], repository, 0)
    result = AgentToolService(context).search_adme_evidence(
        "What does FDA M12 say about transporter drug interactions?"
    )
    assert result["status"] == "ok"
    assert result["data"]["status"] == "supported"
    assert context.structured_payloads[0]["type"] == "evidence_answer"


def test_evidence_output_guardrail_rejects_untraced_numbers() -> None:
    payload = EvidenceService().search(
        "What does FDA say about human radiolabeled mass balance studies?"
    )
    structured = [{"type": "evidence_answer", "data": payload}]
    assert validate_scientific_output("The indexed passage lists steps 1, 2, and 3.", structured).allowed
    assert not validate_scientific_output("The answer has 99 percent confidence.", structured).allowed


def test_evaluation_set_passes_all_separate_metrics() -> None:
    metrics = evaluate()
    assert metrics == {
        "question_count": 13,
        "status_accuracy": 1.0,
        "retrieval_relevance": 1.0,
        "citation_support": 1.0,
        "abstention_accuracy": 1.0,
    }


def test_index_contains_permitted_source_manifest() -> None:
    index = json.loads(rendered_index(DEFAULT_CORPUS))
    assert 5 <= index["source_count"] <= 10
    assert index["passage_count"] >= index["source_count"]
    assert all(source["rights_basis"]["policy_url"].startswith("https://www.fda.gov/") for source in index["sources"])

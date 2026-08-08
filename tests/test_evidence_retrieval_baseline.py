from __future__ import annotations

import json

from scripts.evaluate_evidence_rag import evaluate as evaluate_contract
from scripts.evaluate_evidence_retrieval import DEFAULT_CASES, DEFAULT_INDEX, evaluate


def test_retrieval_cases_are_versioned_and_do_not_leak_source_identity() -> None:
    dataset = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
    index = json.loads(DEFAULT_INDEX.read_text(encoding="utf-8"))

    assert dataset["schema_version"] == 1
    assert len(dataset["cases"]) >= 15
    assert {case["category"] for case in dataset["cases"]} == {
        "abbreviation",
        "direct",
        "hard_negative",
        "metadata",
        "paraphrase",
    }
    assert len({case["id"] for case in dataset["cases"]}) == len(dataset["cases"])

    sources = {source["source_id"]: source for source in index["sources"]}
    for case in dataset["cases"]:
        assert case["leakage_rule"] == "no_source_id_or_exact_title_in_query"
        lowered = case["query"].casefold()
        for source_id in case["expected_source_ids"]:
            assert source_id in sources
            assert source_id.casefold() not in lowered
            assert sources[source_id]["title"].casefold() not in lowered


def test_retrieval_quality_is_repeatable_and_keeps_contract_regressions() -> None:
    first = evaluate(measure_latency=False)
    second = evaluate(measure_latency=False)

    assert first["rankings"] == second["rankings"]
    assert first["quality"] == second["quality"]
    assert first["benchmark"]["corpus_sha256"]
    assert first["benchmark"]["new_runtime_dependencies"] == []
    assert first["benchmark"]["query_count"] >= 15
    assert any(
        metrics["mrr"] < 1.0
        for category, metrics in first["quality"]["by_category"].items()
        if category != "hard_negative"
    )
    assert first["quality"]["hard_negative_accuracy"] == 1.0
    assert evaluate_contract() == {
        "question_count": 13,
        "status_accuracy": 1.0,
        "retrieval_relevance": 1.0,
        "citation_support": 1.0,
        "abstention_accuracy": 1.0,
    }

from __future__ import annotations

import json

from scripts.evaluate_evidence_retrieval import DEFAULT_INDEX
from scripts.evaluate_hybrid_retrieval import rank_metadata_lexical, reciprocal_rank_fusion


def test_metadata_ranker_uses_existing_source_fields_and_still_abstains() -> None:
    documents = json.loads(DEFAULT_INDEX.read_text(encoding="utf-8"))["documents"]

    assert rank_metadata_lexical(
        "Which current August 2024 source discusses transporters?", documents
    )[0] == "fda-m12-2024"
    assert rank_metadata_lexical(
        "Which 2016 final guidance concerns toxic metabolites?", documents
    )[0] == "fda-metabolites-2016"
    assert rank_metadata_lexical(
        "What FDA guidance covers enzyme and transporter mediated drug interactions?",
        documents,
    )[0] == "fda-m12-2024"
    assert rank_metadata_lexical(
        "Which superseded 2020 record covers CYP450 interactions?", documents
    )[0] == "fda-in-vitro-ddi-2020-withdrawn"
    assert rank_metadata_lexical(
        "Does this collection cover quantum entanglement in tablet coatings?", documents
    ) == []


def test_reciprocal_rank_fusion_is_deterministic_and_rewards_agreement() -> None:
    rankings = [
        ["source-a", "source-b", "source-c"],
        ["source-b", "source-c", "source-a"],
    ]

    first = reciprocal_rank_fusion(rankings, top_k=3)
    second = reciprocal_rank_fusion(rankings, top_k=3)

    assert first == second
    assert first == ["source-b", "source-a", "source-c"]

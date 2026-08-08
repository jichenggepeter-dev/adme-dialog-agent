from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.evidence import EvidenceService, SEARCH_STOP_WORDS, tokenize
from scripts.evaluate_evidence_retrieval import (
    DEFAULT_CASES,
    DEFAULT_INDEX,
    _case_quality,
    _quality_summary,
    evaluate as evaluate_lexical,
)


MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "826711e54e001c83835913827a843d8dd0a1def9"
MODEL_LICENSE = "Apache-2.0"
DENSE_MINIMUM_SCORE = 0.35
RRF_K = 60
STALE_QUERY_TERMS = ("withdrawn", "superseded", "obsolete")
DEFAULT_JSON_REPORT = ROOT / "evaluation" / "reports" / "hybrid-retrieval-study-v1.json"
DEFAULT_MARKDOWN_REPORT = ROOT / "evaluation" / "reports" / "hybrid-retrieval-study-v1.md"


def _metadata_text(document: dict[str, Any]) -> str:
    date = document["document_date"]
    parts = date.split("-")
    month = calendar.month_name[int(parts[1])] if len(parts) > 1 else ""
    return " ".join(
        [date, parts[0], month, document["version"], document["status"]]
    )


def _lifecycle_match(query: str, document: dict[str, Any]) -> bool:
    wants_stale = any(term in query.lower() for term in STALE_QUERY_TERMS)
    return (document["status"] != "current") == wants_stale


def rank_metadata_lexical(
    query: str,
    documents: list[dict[str, Any]],
    top_k: int = 3,
) -> list[str]:
    query_tokens = [token for token in tokenize(query) if token not in SEARCH_STOP_WORDS]
    if not query_tokens:
        return []

    enriched = []
    for document in documents:
        counts = Counter(document["tokens"])
        counts.update(tokenize(_metadata_text(document)))
        enriched.append({**document, "tokens": dict(counts), "length": sum(counts.values())})

    ranked = EvidenceService._rank(query_tokens, enriched)
    required_overlap = min(2, len(set(query_tokens)))
    sources = []
    for score, document in ranked:
        if not _lifecycle_match(query, document):
            continue
        overlap = len(set(query_tokens) & set(document["tokens"]))
        source_id = document["source_id"]
        if score >= 0.2 and overlap >= required_overlap and source_id not in sources:
            sources.append(source_id)
        if len(sources) == top_k:
            break
    return sources


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    *,
    top_k: int,
    rrf_k: int = RRF_K,
) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, source_id in enumerate(ranking, start=1):
            scores[source_id] += 1 / (rrf_k + rank)
    return [
        source_id
        for source_id, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]
    ]


def _current_lexical(query: str, service: EvidenceService, top_k: int) -> list[str]:
    result = service.search(query, top_k=top_k)
    return list(dict.fromkeys(item["source_id"] for item in result["evidence"]))


def _document_text(document: dict[str, Any]) -> str:
    return "\n".join(
        [
            document["title"],
            "Topics: " + ", ".join(document["topics"]),
            document["section"],
            document["claim"],
            document["excerpt"],
        ]
    )


def _dense_ranker(
    model: Any,
    documents: list[dict[str, Any]],
    document_embeddings: Any,
    *,
    top_k: int,
) -> Callable[[str], list[str]]:
    def rank(query: str) -> list[str]:
        query_embedding = model.encode_query(
            [query], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )[0]
        scores = document_embeddings @ query_embedding
        ordered = sorted(
            zip(scores.tolist(), documents, strict=True),
            key=lambda item: (-item[0], item[1]["chunk_id"]),
        )
        sources = []
        for score, document in ordered:
            if not _lifecycle_match(query, document):
                continue
            source_id = document["source_id"]
            if score >= DENSE_MINIMUM_SCORE and source_id not in sources:
                sources.append(source_id)
            if len(sources) == top_k:
                break
        return sources

    return rank


def _evaluate_method(
    cases: list[dict[str, Any]],
    ranker: Callable[[str], list[str]],
) -> dict[str, Any]:
    rankings = []
    durations = []
    for case in cases:
        started = time.perf_counter_ns()
        retrieved = ranker(case["query"])
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
        rankings.append(
            {
                "id": case["id"],
                "category": case["category"],
                "query": case["query"],
                "expected_source_ids": case["expected_source_ids"],
                "retrieved_source_ids": retrieved,
                "quality": _case_quality(case["expected_source_ids"], retrieved),
            }
        )
    ordered = sorted(durations)
    return {
        "quality": _quality_summary(rankings),
        "latency": {
            "sample_count": len(durations),
            "median_ms": round(statistics.median(durations), 4),
            "p95_ms": round(ordered[math.ceil(len(ordered) * 0.95) - 1], 4),
        },
        "rankings": {item["id"]: item["retrieved_source_ids"] for item in rankings},
        "unexpected_hard_negative_matches": {
            item["id"]: item["retrieved_source_ids"]
            for item in rankings
            if not item["expected_source_ids"] and item["retrieved_source_ids"]
        },
    }


def _model_size(model_id: str, revision: str) -> int:
    from huggingface_hub import snapshot_download

    snapshot = Path(
        snapshot_download(repo_id=model_id, revision=revision, local_files_only=True)
    )
    return sum(path.stat().st_size for path in snapshot.rglob("*") if path.is_file())


def evaluate(*, offline: bool) -> dict[str, Any]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit(
            "Install the locked research extra first: uv sync --extra dev --extra rag-research"
        ) from exc

    dataset_bytes = DEFAULT_CASES.read_bytes()
    dataset = json.loads(dataset_bytes)
    index = json.loads(DEFAULT_INDEX.read_text(encoding="utf-8"))
    documents = index["documents"]
    top_k = dataset["top_k"]

    load_started = time.perf_counter_ns()
    model = SentenceTransformer(
        MODEL_ID,
        revision=MODEL_REVISION,
        device="cpu",
        local_files_only=offline,
    )
    model_load_ms = (time.perf_counter_ns() - load_started) / 1_000_000

    index_started = time.perf_counter_ns()
    document_embeddings = model.encode_document(
        [_document_text(document) for document in documents],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    index_build_ms = (time.perf_counter_ns() - index_started) / 1_000_000

    service = EvidenceService(index_data=index)
    dense = _dense_ranker(model, documents, document_embeddings, top_k=top_k)
    lexical = lambda query: _current_lexical(query, service, top_k)
    metadata = lambda query: rank_metadata_lexical(query, documents, top_k)
    hybrid = lambda query: reciprocal_rank_fusion(
        [lexical(query), dense(query)], top_k=top_k
    )
    hybrid_metadata = lambda query: reciprocal_rank_fusion(
        [metadata(query), dense(query)], top_k=top_k
    )

    methods = {
        "lexical": _evaluate_method(dataset["cases"], lexical),
        "metadata_lexical": _evaluate_method(dataset["cases"], metadata),
        "dense": _evaluate_method(dataset["cases"], dense),
        "hybrid_rrf": _evaluate_method(dataset["cases"], hybrid),
        "hybrid_metadata_rrf": _evaluate_method(dataset["cases"], hybrid_metadata),
    }
    repeated = {
        name: _evaluate_method(dataset["cases"], ranker)["rankings"]
        == methods[name]["rankings"]
        for name, ranker in {
            "lexical": lexical,
            "metadata_lexical": metadata,
            "dense": dense,
            "hybrid_rrf": hybrid,
            "hybrid_metadata_rrf": hybrid_metadata,
        }.items()
    }
    baseline = evaluate_lexical(measure_latency=False)["quality"]
    for method in methods.values():
        quality = method["quality"]
        no_slice_regression = all(
            quality["by_category"][category][metric]
            >= baseline["by_category"][category][metric]
            for category in baseline["by_category"]
            if category != "hard_negative"
            for metric in ("recall_at_3", "mrr")
        )
        gate = {
            "recall_at_3_improved": quality["overall"]["recall_at_3"]
            > baseline["overall"]["recall_at_3"],
            "mrr_improved": quality["overall"]["mrr"] > baseline["overall"]["mrr"],
            "hard_negatives_preserved": quality["hard_negative_accuracy"] == 1.0,
            "no_category_regression": no_slice_regression,
        }
        method["quality_gate"] = {**gate, "passed": all(gate.values())}

    return {
        "experiment": {
            "schema_version": 1,
            "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "corpus_sha256": index["corpus_sha256"],
            "query_count": len(dataset["cases"]),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "offline_mode": offline,
            "top_k": top_k,
            "dense_minimum_score": DENSE_MINIMUM_SCORE,
            "rrf_k": RRF_K,
            "model": {
                "id": MODEL_ID,
                "revision": MODEL_REVISION,
                "license": MODEL_LICENSE,
                "cache_bytes": _model_size(MODEL_ID, MODEL_REVISION),
            },
            "packages": {
                name: version(name)
                for name in (
                    "sentence-transformers",
                    "transformers",
                    "torch",
                    "numpy",
                    "scikit-learn",
                    "huggingface-hub",
                    "tokenizers",
                )
            },
            "model_load_ms": round(model_load_ms, 2),
            "index_build_ms": round(index_build_ms, 2),
            "production_dependency_change": "none; research optional extra only",
            "network_or_provider_required_after_cache": False,
        },
        "repeatable_rankings": repeated,
        "methods": methods,
    }


def render_markdown(report: dict[str, Any]) -> str:
    experiment = report["experiment"]
    lines = [
        "# Hybrid retrieval study v1",
        "",
        "This is a fixed-corpus research comparison for Issue #26. It is not a production rollout or a scientific-validity claim.",
        "",
        "## Experiment identity",
        "",
        f"- Dataset SHA-256: `{experiment['dataset_sha256']}`",
        f"- Corpus SHA-256: `{experiment['corpus_sha256']}`",
        f"- Model: `{experiment['model']['id']}` at `{experiment['model']['revision']}`",
        f"- Model license: `{experiment['model']['license']}`",
        f"- Cached model bytes: `{experiment['model']['cache_bytes']}`",
        f"- Offline replay: `{experiment['offline_mode']}`",
        f"- Model load: `{experiment['model_load_ms']}` ms; nine-passage index build: `{experiment['index_build_ms']}` ms",
        f"- Dense threshold: `{experiment['dense_minimum_score']}`; RRF k: `{experiment['rrf_k']}`",
        "- Production dependency change: none; the model stack is an optional research extra",
        "",
        "## Quality and warm-query latency",
        "",
        "| Method | Recall@1 | Recall@3 | MRR | Hard negatives | Median ms | p95 ms | Quality gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for name, method in report["methods"].items():
        quality = method["quality"]
        latency = method["latency"]
        lines.append(
            f"| {name} | {quality['overall']['recall_at_1']:.3f} | {quality['overall']['recall_at_3']:.3f} | {quality['overall']['mrr']:.3f} | {quality['hard_negative_accuracy']:.3f} | {latency['median_ms']} | {latency['p95_ms']} | {'pass' if method['quality_gate']['passed'] else 'fail'} |"
        )
    lines.extend(
        [
            "",
            "The quality gate requires Recall@3 and MRR to improve overall, hard-negative accuracy to remain 1.0, and no relevant query category to regress on Recall@3 or MRR. Passing this table is necessary but not sufficient for production adoption.",
            "",
            "## Repeatability",
            "",
        ]
    )
    for name, repeatable in report["repeatable_rankings"].items():
        lines.append(f"- `{name}`: `{'identical' if repeatable else 'different'}` rankings on the repeated run")
    lines.extend(
        [
            "",
            "## Locked package versions",
            "",
        ]
    )
    for name, package_version in experiment["packages"].items():
        lines.append(f"- `{name}=={package_version}`")
    lines.extend(
        [
            "",
            "Warm-query timings are local comparison samples on the recorded platform, not production service-level claims. Model download time is excluded; model load and index construction are reported separately.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare fixed-corpus retrieval candidates.")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    args = parser.parse_args()
    report = evaluate(offline=args.offline)
    write_reports(report, args.json_output, args.markdown_output)
    for name, method in report["methods"].items():
        quality = method["quality"]["overall"]
        print(
            f"{name}: Recall@3={quality['recall_at_3']:.3f}, "
            f"MRR={quality['mrr']:.3f}, "
            f"hard-negative={method['quality']['hard_negative_accuracy']:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

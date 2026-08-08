from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.evidence import EvidenceService


DEFAULT_CASES = ROOT / "evaluation" / "evidence_retrieval_cases_v1.json"
DEFAULT_INDEX = ROOT / "resources" / "evidence" / "index.json"
DEFAULT_JSON_REPORT = ROOT / "evaluation" / "reports" / "evidence-retrieval-baseline-v1.json"
DEFAULT_MARKDOWN_REPORT = ROOT / "evaluation" / "reports" / "evidence-retrieval-baseline-v1.md"


def _case_quality(expected: list[str], ranking: list[str]) -> dict[str, float | int | None]:
    if not expected:
        return {"recall_at_1": None, "recall_at_3": None, "reciprocal_rank": None}
    first_rank = next(
        (position for position, source_id in enumerate(ranking, start=1) if source_id in expected),
        None,
    )
    return {
        "recall_at_1": len(set(expected) & set(ranking[:1])) / len(expected),
        "recall_at_3": len(set(expected) & set(ranking[:3])) / len(expected),
        "reciprocal_rank": 0.0 if first_rank is None else 1 / first_rank,
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _quality_summary(rankings: list[dict[str, Any]]) -> dict[str, Any]:
    relevant = [item for item in rankings if item["expected_source_ids"]]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in rankings:
        grouped[item["category"]].append(item)

    def summarize(items: list[dict[str, Any]]) -> dict[str, float | int]:
        scored = [item["quality"] for item in items if item["expected_source_ids"]]
        return {
            "query_count": len(items),
            "recall_at_1": _mean([item["recall_at_1"] for item in scored]),
            "recall_at_3": _mean([item["recall_at_3"] for item in scored]),
            "mrr": _mean([item["reciprocal_rank"] for item in scored]),
        }

    negatives = [item for item in rankings if not item["expected_source_ids"]]
    return {
        "overall": summarize(relevant),
        "by_category": {
            category: summarize(items) for category, items in sorted(grouped.items())
        },
        "hard_negative_accuracy": _mean(
            [1.0 if not item["retrieved_source_ids"] else 0.0 for item in negatives]
        ),
    }


def evaluate(
    cases_path: Path = DEFAULT_CASES,
    index_path: Path = DEFAULT_INDEX,
    *,
    measure_latency: bool = True,
) -> dict[str, Any]:
    dataset = json.loads(cases_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    top_k = dataset["top_k"]
    service = EvidenceService(index_data=index)
    rankings = []
    durations = []

    for case in dataset["cases"]:
        started = time.perf_counter_ns()
        result = service.search(case["query"], top_k=top_k)
        if measure_latency:
            durations.append((time.perf_counter_ns() - started) / 1_000_000)
        retrieved = list(dict.fromkeys(item["source_id"] for item in result["evidence"]))
        rankings.append(
            {
                "id": case["id"],
                "category": case["category"],
                "query": case["query"],
                "expected_source_ids": case["expected_source_ids"],
                "retrieved_source_ids": retrieved,
                "result_status": result["status"],
                "quality": _case_quality(case["expected_source_ids"], retrieved),
            }
        )

    latency = {
        "scope": "Local comparative measurement only; not a production latency claim.",
        "sample_count": len(durations),
        "median_ms": round(statistics.median(durations), 4) if durations else None,
        "p95_ms": round(sorted(durations)[math.ceil(len(durations) * 0.95) - 1], 4)
        if durations
        else None,
    }
    return {
        "benchmark": {
            "schema_version": dataset["schema_version"],
            "dataset_id": dataset["dataset_id"],
            "query_count": len(dataset["cases"]),
            "corpus_sha256": index["corpus_sha256"],
            "python_version": platform.python_version(),
            "retrieval_config": {
                "implementation": "app.services.evidence.EvidenceService.search",
                "method": "deterministic lexical BM25-style scoring",
                "top_k": top_k,
                "minimum_score": 0.2,
                "minimum_query_token_overlap": "min(2, unique query tokens)",
            },
            "new_runtime_dependencies": [],
            "network_access": False,
        },
        "quality": _quality_summary(rankings),
        "latency": latency,
        "rankings": rankings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    benchmark = report["benchmark"]
    overall = report["quality"]["overall"]
    latency = report["latency"]
    lines = [
        "# Evidence retrieval baseline v1",
        "",
        "This report measures the existing deterministic lexical retriever on a fixed corpus. It is a comparison baseline, not evidence of scientific correctness or a production performance claim.",
        "",
        "## Baseline identity",
        "",
        f"- Dataset: `{benchmark['dataset_id']}` ({benchmark['query_count']} queries)",
        f"- Corpus SHA-256: `{benchmark['corpus_sha256']}`",
        f"- Python: `{benchmark['python_version']}`",
        f"- Retrieval: {benchmark['retrieval_config']['method']}, top {benchmark['retrieval_config']['top_k']}",
        "- New runtime dependencies: none",
        "- Network access: none",
        "",
        "## Quality",
        "",
        "| Slice | Queries | Recall@1 | Recall@3 | MRR |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Overall relevant | {overall['query_count']} | {overall['recall_at_1']:.3f} | {overall['recall_at_3']:.3f} | {overall['mrr']:.3f} |",
    ]
    for category, metrics in report["quality"]["by_category"].items():
        if category == "hard_negative":
            continue
        lines.append(
            f"| {category} | {metrics['query_count']} | {metrics['recall_at_1']:.3f} | {metrics['recall_at_3']:.3f} | {metrics['mrr']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"Hard-negative accuracy: `{report['quality']['hard_negative_accuracy']:.3f}`.",
            "",
            "The non-perfect paraphrase and abbreviation slices are intentional: they remove the old evaluation ceiling and give Issue #26 room to demonstrate—or fail to demonstrate—a repeatable improvement.",
            "",
            "## Local latency sample",
            "",
            latency["scope"],
            "",
            f"- Samples: {latency['sample_count']}",
            f"- Median: {latency['median_ms']} ms",
            f"- p95: {latency['p95_ms']} ms",
            "",
            "## Per-query results",
            "",
            "| ID | Category | Expected | Retrieved | Reciprocal rank |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )
    for item in report["rankings"]:
        expected = ", ".join(item["expected_source_ids"]) or "none"
        retrieved = ", ".join(item["retrieved_source_ids"]) or "none"
        reciprocal_rank = item["quality"]["reciprocal_rank"]
        rendered_rank = "n/a" if reciprocal_rank is None else f"{reciprocal_rank:.3f}"
        lines.append(
            f"| `{item['id']}` | {item['category']} | {expected} | {retrieved} | {rendered_rank} |"
        )
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure the fixed Evidence RAG retrieval baseline.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    parser.add_argument("--skip-latency", action="store_true")
    args = parser.parse_args()
    report = evaluate(args.cases, args.index, measure_latency=not args.skip_latency)
    write_reports(report, args.json_output, args.markdown_output)
    print(
        f"Evidence retrieval baseline: Recall@3={report['quality']['overall']['recall_at_3']:.3f}, "
        f"MRR={report['quality']['overall']['mrr']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

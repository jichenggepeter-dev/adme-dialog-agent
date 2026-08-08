from __future__ import annotations

import json
from pathlib import Path

from app.agent_runtime.evaluation import load_dataset, run_evaluation, write_reports


DATASET = Path(__file__).parents[1] / "evaluation" / "agent" / "cases-v1.json"
DETERMINISTIC_MODES = {"deterministic_rules", "mock_provider"}


def test_agent_evaluation_dataset_is_versioned_and_complete() -> None:
    dataset = load_dataset(DATASET)

    assert dataset.schema_version == "1.1"
    assert {case.execution_mode for case in dataset.cases} == {
        "deterministic_rules",
        "mock_provider",
        "real_provider",
    }
    assert all(case.prohibited_language for case in dataset.cases)
    assert all(
        [item.operation for item in case.expected_arguments] == case.expected_tools
        for case in dataset.cases
    )


def test_deterministic_agent_evaluation_passes_and_writes_both_reports(
    tmp_path: Path,
) -> None:
    dataset = load_dataset(DATASET)
    report = run_evaluation(dataset, modes=DETERMINISTIC_MODES)
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"

    write_reports(report, json_path, markdown_path)

    assert report["summary"]["selected"] == 19
    assert report["summary"]["passed"] == 19
    assert report["summary"]["failed"] == 0
    assert len(report["summary"]["quality_metrics"]) == 8
    assert all(
        metric["passed"]
        for metric in report["summary"]["quality_metrics"].values()
    )
    assert json.loads(json_path.read_text())["report_schema_version"] == "1.1"
    assert "19 passed, 0 failed" in markdown_path.read_text()
    assert "Required confirmation compliance | 100% | 100%" in markdown_path.read_text()


def test_agent_evaluation_category_filter_runs_independently() -> None:
    dataset = load_dataset(DATASET)

    report = run_evaluation(
        dataset,
        modes=DETERMINISTIC_MODES,
        categories={"confirmation"},
    )

    assert report["summary"]["selected"] == 1
    assert report["summary"]["failed"] == 0
    assert report["results"][0]["case_id"] == "mock_confirmation_001"

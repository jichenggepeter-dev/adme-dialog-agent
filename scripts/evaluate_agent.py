from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent_runtime.evaluation import load_dataset, run_evaluation, write_reports


DEFAULT_DATASET = ROOT / "evaluation" / "agent" / "cases-v1.json"
DEFAULT_JSON_REPORT = ROOT / "evaluation" / "reports" / "agent-eval-v1.json"
DEFAULT_MARKDOWN_REPORT = ROOT / "evaluation" / "reports" / "agent-eval-v1.md"
DEFAULT_MODES = {"deterministic_rules", "mock_provider"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the versioned Agent evaluation suite.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--mode",
        action="append",
        choices=("deterministic_rules", "mock_provider", "real_provider"),
        help="Execution mode to include. Repeat to select multiple modes.",
    )
    parser.add_argument("--category", action="append", help="Category to include.")
    parser.add_argument("--case-id", action="append", help="Case ID to include.")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    report = run_evaluation(
        dataset,
        modes=set(args.mode or DEFAULT_MODES),
        categories=set(args.category) if args.category else None,
        case_ids=set(args.case_id) if args.case_id else None,
    )
    write_reports(report, args.json_output, args.markdown_output)
    print(
        f"Agent evaluation: {report['summary']['passed']} passed, "
        f"{report['summary']['failed']} failed."
    )
    print(f"JSON report: {args.json_output}")
    print(f"Markdown report: {args.markdown_output}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

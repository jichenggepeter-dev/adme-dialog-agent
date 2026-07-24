from __future__ import annotations

import csv
import io
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.formatter import DISCLAIMER, generate_summary, group_enriched_predictions, group_predictions
from app.tools.admet_predictor import ADMETPredictionError, is_mock_mode, predict_one, predictor_status
from app.tools.smiles import validate_smiles


MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5_000
DATA_ROOT = Path(os.getenv("ADME_DATA_DIR", "data"))
UPLOAD_ROOT = DATA_ROOT / "uploads"
JOB_ROOT = DATA_ROOT / "jobs"
TERMINAL_STATES = {"completed", "completed_with_errors", "failed", "cancelled"}
_LOCK = threading.RLock()


class BatchError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_id(value: str, kind: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError) as exc:
        raise BatchError(f"BATCH_{kind.upper()}_NOT_FOUND", f"Batch {kind} was not found.", 404) from exc


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path, code: str, message: str) -> dict:
    if not path.exists():
        raise BatchError(code, message, 404)
    return json.loads(path.read_text(encoding="utf-8"))


def _file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix not in {"csv", "tsv", "smi"}:
        raise BatchError("INVALID_FILE_TYPE", "Use a CSV, TSV, or SMI file.")
    return suffix


def parse_batch_file(filename: str, content: bytes) -> tuple[list[str], list[dict[str, str]], str]:
    kind = _file_type(filename)
    if not content:
        raise BatchError("EMPTY_FILE", "The selected file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise BatchError("FILE_TOO_LARGE", f"Files must be {MAX_FILE_BYTES // 1024 // 1024} MB or smaller.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BatchError("UNSUPPORTED_FILE_ENCODING", "Use a UTF-8 encoded file.") from exc

    if kind == "smi":
        rows: list[dict[str, str]] = []
        has_name = False
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            row = {"smiles": parts[0], "name": parts[1].strip() if len(parts) > 1 else ""}
            has_name = has_name or bool(row["name"])
            rows.append(row)
        columns = ["smiles", "name"] if has_name else ["smiles"]
        rows = [{key: value for key, value in row.items() if key in columns} for row in rows]
    else:
        delimiter = "," if kind == "csv" else "\t"
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        if not reader.fieldnames:
            raise BatchError("EMPTY_FILE", "The file does not contain a header row.")
        columns = [str(name).strip() for name in reader.fieldnames if name is not None]
        if not columns or any(not name for name in columns):
            raise BatchError("INVALID_FILE", "Every input column must have a name.")
        rows = [{column: str(row.get(column) or "") for column in columns} for row in reader]

    if not rows:
        raise BatchError("EMPTY_FILE", "The file does not contain any compound rows.")
    if len(rows) > MAX_ROWS:
        raise BatchError("TOO_MANY_ROWS", f"Batch files may contain at most {MAX_ROWS} rows.")
    return columns, rows, kind


def _suggest_mapping(columns: list[str]) -> dict[str, str | None]:
    lowered = {column.lower().replace(" ", "_"): column for column in columns}
    def match(*names: str) -> str | None:
        return next((lowered[name] for name in names if name in lowered), None)
    return {
        "smiles": match("smiles", "canonical_smiles", "structure"),
        "compound_id": match("compound_id", "id", "identifier"),
        "compound_name": match("compound_name", "name", "title"),
    }


def create_upload(filename: str, content: bytes) -> dict:
    columns, rows, kind = parse_batch_file(filename, content)
    upload_id = str(uuid4())
    created = _now()
    payload = {
        "upload_id": upload_id,
        "source_filename": Path(filename).name,
        "file_type": kind,
        "file_size": len(content),
        "row_count": len(rows),
        "columns": columns,
        "preview": rows[:10],
        "suggested_mapping": _suggest_mapping(columns),
        "created_at": created,
        "rows": rows,
    }
    _atomic_json(UPLOAD_ROOT / upload_id / "upload.json", payload)
    return {key: value for key, value in payload.items() if key != "rows"}


def get_upload(upload_id: str) -> dict:
    safe = _safe_id(upload_id, "upload")
    return _read_json(UPLOAD_ROOT / safe / "upload.json", "BATCH_UPLOAD_NOT_FOUND", "Batch upload was not found.")


def _validate_mapping(columns: list[str], mapping: dict[str, str | None]) -> None:
    smiles_column = mapping.get("smiles")
    if not smiles_column:
        raise BatchError("MISSING_SMILES_COLUMN", "Select the column containing SMILES values.")
    mapped = [value for value in mapping.values() if value]
    if any(value not in columns for value in mapped) or len(mapped) != len(set(mapped)):
        raise BatchError("INVALID_COLUMN_MAPPING", "Mapped columns must be distinct columns from the uploaded file.")


def create_job(upload_id: str, mapping: dict[str, str | None]) -> dict:
    upload = get_upload(upload_id)
    _validate_mapping(upload["columns"], mapping)
    canonical_groups: dict[str, list[int]] = {}
    rows: list[dict] = []
    for row_number, source in enumerate(upload["rows"], start=1):
        input_smiles = str(source.get(mapping["smiles"] or "", "")).strip()
        row = {
            "row_number": row_number,
            "compound_id": str(source.get(mapping.get("compound_id") or "", "")).strip() or None,
            "compound_name": str(source.get(mapping.get("compound_name") or "", "")).strip() or None,
            "input_smiles": input_smiles,
            "canonical_smiles": None,
            "validation_status": "valid",
            "error_code": None,
            "error_message": None,
            "duplicate_group": None,
            "prediction_status": "not_run",
            "predictions": None,
            "summary": None,
        }
        if not input_smiles:
            row.update(validation_status="missing_smiles", error_code="MISSING_SMILES", error_message="No SMILES value was provided.")
        else:
            validation = validate_smiles(input_smiles)
            if not validation["is_valid"]:
                row.update(validation_status="invalid_smiles", error_code="INVALID_SMILES", error_message=validation["error"])
            else:
                canonical = validation["canonical_smiles"] or input_smiles
                row["canonical_smiles"] = canonical
                canonical_groups.setdefault(canonical, []).append(row_number - 1)
        rows.append(row)

    duplicate_count = 0
    for group_number, indexes in enumerate((indexes for indexes in canonical_groups.values() if len(indexes) > 1), start=1):
        group_id = f"duplicate-{group_number}"
        for duplicate_index, index in enumerate(indexes):
            rows[index]["duplicate_group"] = group_id
            if duplicate_index:
                rows[index]["validation_status"] = "duplicate"
                duplicate_count += 1

    valid_count = sum(row["validation_status"] in {"valid", "duplicate"} for row in rows)
    unique_count = len(canonical_groups)
    summary = {
        "total_rows": len(rows),
        "valid_molecules": valid_count,
        "invalid_smiles": sum(row["validation_status"] == "invalid_smiles" for row in rows),
        "missing_smiles": sum(row["validation_status"] == "missing_smiles" for row in rows),
        "duplicate_molecules": duplicate_count,
        "unique_valid_molecules": unique_count,
    }
    if unique_count == 0:
        raise BatchError("NO_VALID_MOLECULES", "No valid molecules were found in the mapped SMILES column.")

    job_id = str(uuid4())
    now = _now()
    job = {
        "job_id": job_id,
        "source_filename": upload["source_filename"],
        "file_type": upload["file_type"],
        "mapping": mapping,
        "status": "ready",
        "prediction_mode": "mock" if is_mock_mode() else "real",
        "model_name": "ADMET-AI" if not is_mock_mode() else "Deterministic development fixture",
        "model_version": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "summary": summary,
        "progress": {"processed": 0, "total": unique_count, "completed": 0, "failed": 0},
        "rows": rows,
        "disclaimer": DISCLAIMER,
    }
    _atomic_json(JOB_ROOT / job_id / "metadata.json", job)
    return job


def get_job(job_id: str) -> dict:
    safe = _safe_id(job_id, "job")
    return _read_json(JOB_ROOT / safe / "metadata.json", "BATCH_JOB_NOT_FOUND", "Batch job was not found.")


def _save_job(job: dict) -> None:
    job["updated_at"] = _now()
    _atomic_json(JOB_ROOT / job["job_id"] / "metadata.json", job)


def run_job(job_id: str) -> None:
    with _LOCK:
        job = get_job(job_id)
        if job["status"] not in {"ready", "failed"}:
            raise BatchError("BATCH_JOB_NOT_READY", "The batch job is not ready to run.", 409)
        job["status"] = "running"
        for row in job["rows"]:
            if row["validation_status"] in {"valid", "duplicate"}:
                row["prediction_status"] = "pending"
        _save_job(job)

    canonical_results: dict[str, dict] = {}
    canonical_values = list(dict.fromkeys(row["canonical_smiles"] for row in job["rows"] if row["canonical_smiles"]))
    for canonical in canonical_values:
        with _LOCK:
            current = get_job(job_id)
            if current["status"] == "cancelled":
                return
        try:
            raw = predict_one(canonical)
            grouped = group_predictions(raw)
            canonical_results[canonical] = {"predictions": grouped, "enriched_predictions": group_enriched_predictions(raw), "raw_predictions": raw, "summary": generate_summary(grouped), "error": None}
            completed = True
        except ADMETPredictionError as exc:
            canonical_results[canonical] = {"predictions": None, "raw_predictions": None, "summary": None, "error": str(exc)}
            completed = False
        with _LOCK:
            current = get_job(job_id)
            current["progress"]["processed"] += 1
            current["progress"]["completed" if completed else "failed"] += 1
            _save_job(current)

    with _LOCK:
        job = get_job(job_id)
        if job["status"] == "cancelled":
            return
        for row in job["rows"]:
            canonical = row["canonical_smiles"]
            if not canonical:
                continue
            result = canonical_results[canonical]
            if result["error"]:
                row["prediction_status"] = "failed"
                row["error_code"] = "PREDICTION_FAILED"
                row["error_message"] = result["error"]
            else:
                row["prediction_status"] = "completed"
                row["predictions"] = result["predictions"]
                row["enriched_predictions"] = result["enriched_predictions"]
                row["raw_predictions"] = result["raw_predictions"]
                row["summary"] = result["summary"]
        job["status"] = "completed_with_errors" if job["progress"]["failed"] else "completed"
        job["completed_at"] = _now()
        _save_job(job)


def cancel_job(job_id: str) -> dict:
    with _LOCK:
        job = get_job(job_id)
        if job["status"] in TERMINAL_STATES:
            raise BatchError("BATCH_JOB_NOT_CANCELLABLE", "This batch job can no longer be cancelled.", 409)
        job["status"] = "cancelled"
        _save_job(job)
        return job


def run_job_thread(job_id: str) -> dict:
    job = get_job(job_id)
    if job["status"] != "ready":
        raise BatchError("BATCH_JOB_NOT_READY", "The batch job is not ready to run.", 409)
    thread = threading.Thread(target=_run_job_safely, args=(job_id,), daemon=True)
    thread.start()
    return get_job(job_id)


def _run_job_safely(job_id: str) -> None:
    try:
        run_job(job_id)
    except Exception:
        with _LOCK:
            try:
                job = get_job(job_id)
                job["status"] = "failed"
                job["completed_at"] = _now()
                _save_job(job)
            except Exception:
                return


def safe_csv_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def export_job(job_id: str, kind: str, filtered_rows: list[int] | None = None) -> tuple[str, bytes, str]:
    job = get_job(job_id)
    if kind in {"metadata", "json"}:
        payload = job if kind == "json" else {key: value for key, value in job.items() if key != "rows"}
        return f"{job_id}-{kind}.json", json.dumps(payload, indent=2).encode(), "application/json"

    rows = job["rows"]
    if filtered_rows is not None:
        allowed = set(filtered_rows)
        rows = [row for row in rows if row["row_number"] in allowed]
    if kind == "errors":
        rows = [row for row in rows if row["error_code"]]
    if kind not in {"results", "filtered", "errors"}:
        raise BatchError("INVALID_EXPORT_TYPE", "The requested export type is not supported.")

    endpoint_keys = sorted({key for row in rows for category in (row.get("predictions") or {}).values() for key in category})
    fields = ["row_number", "compound_id", "compound_name", "input_smiles", "canonical_smiles", "validation_status", "prediction_status", "error_code", "error_message", *endpoint_keys]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        flat = {field: row.get(field) for field in fields}
        for category in (row.get("predictions") or {}).values():
            flat.update(category)
        writer.writerow({key: safe_csv_cell(value) for key, value in flat.items()})
    filename_kind = "errors" if kind == "errors" else "results"
    return f"{job_id}-{filename_kind}.csv", output.getvalue().encode(), "text/csv"


def batch_capabilities() -> dict:
    return {
        "supported_file_types": ["csv", "tsv", "smi"],
        "maximum_file_bytes": MAX_FILE_BYTES,
        "maximum_rows": MAX_ROWS,
        "storage": "local_files",
        "worker": "in_process_thread",
        "predictor": predictor_status(),
    }

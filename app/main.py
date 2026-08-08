from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.agent import handle_chat_message, predict_adme
from app.formatter import DISCLAIMER, generate_summary, group_predictions
from app.schemas import BatchFilteredExportRequest, BatchJobCreateRequest, BatchPredictRequest, ChatRequest, ChatResponse, CompoundResolveRequest, CompoundResponse, PredictRequest, PredictionResponse, StatusResponse
from app.tools.batch import BatchError, batch_capabilities, cancel_job, create_job, create_upload, export_job, get_job, run_job_thread
from app.tools.compound import CompoundResolutionError, resolve_compound
from app.tools.endpoints import get_endpoint, list_endpoints, registry_coverage, registry_document
from app.tools.admet_predictor import ADMETPredictionError, is_mock_mode, predict_many, predictor_status
from app.tools.smiles import validate_smiles
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.routes import router as agent_router


BACKEND_VERSION = "0.1.0"
logger = logging.getLogger(__name__)

app = FastAPI(title="ADME Dialog Agent", version=BACKEND_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://(?:localhost|127\.0\.0\.1):\d+",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Correlation-ID"],
)
app.include_router(agent_router)


def _error_response(status_code: int, code: str, message: str, details: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def _deletion_response_headers(request: Request) -> dict[str, str]:
    if request.url.path.startswith("/agent/sessions/") and "/deletions" in request.url.path:
        return {"Cache-Control": "no-store, max-age=0"}
    return {}


@app.exception_handler(ADMETPredictionError)
async def prediction_error_handler(request: Request, exc: ADMETPredictionError) -> JSONResponse:
    logger.exception("ADMET prediction request failed", exc_info=exc)
    return _error_response(
        503,
        exc.code,
        str(exc),
        "Check the backend terminal for diagnostic information.",
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        headers=_deletion_response_headers(request),
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": "The request body is invalid.",
                "details": "Check the submitted fields.",
                "retryable": False,
                "correlation_id": request.headers.get("X-Correlation-ID") or uuid4().hex,
            }
        },
    )


@app.exception_handler(CompoundResolutionError)
async def compound_error_handler(request: Request, exc: CompoundResolutionError) -> JSONResponse:
    logger.warning("Compound resolution failed: %s", exc.code)
    return _error_response(exc.status_code, exc.code, str(exc))


@app.exception_handler(BatchError)
async def batch_error_handler(request: Request, exc: BatchError) -> JSONResponse:
    logger.warning("Batch request failed: %s", exc.code)
    return _error_response(exc.status_code, exc.code, str(exc))


@app.exception_handler(AgentCoreError)
async def agent_core_error_handler(request: Request, exc: AgentCoreError) -> JSONResponse:
    logger.warning("Agent request failed: %s", exc.code)
    return JSONResponse(
        status_code=exc.status_code,
        headers=_deletion_response_headers(request),
        content={"error": {"code": exc.code, "message": str(exc), "details": None,
                           "retryable": exc.retryable,
                           "correlation_id": request.headers.get("X-Correlation-ID") or uuid4().hex}},
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/status", response_model=StatusResponse)
def status() -> dict:
    return {"status": "ok", "backend_version": BACKEND_VERSION, **predictor_status()}


@app.post("/compound/resolve", response_model=CompoundResponse)
def compound_resolve(request: CompoundResolveRequest) -> dict:
    return resolve_compound(request.query)


@app.get("/endpoints")
def endpoints() -> dict:
    return registry_document()


@app.get("/endpoints/coverage")
def endpoint_coverage() -> dict:
    observed_keys = list(list_endpoints())
    return registry_coverage(observed_keys)


@app.get("/endpoints/{raw_key}")
def endpoint_detail(raw_key: str) -> dict:
    endpoint = get_endpoint(raw_key)
    if endpoint is None:
        return _error_response(404, "ENDPOINT_NOT_FOUND", "Endpoint metadata was not found.")
    return endpoint


@app.get("/batch/capabilities")
def batch_capability_route() -> dict:
    return batch_capabilities()


@app.post("/batch/upload")
async def batch_upload(file: UploadFile = File(...)) -> dict:
    return create_upload(file.filename or "upload", await file.read())


@app.post("/batch/jobs")
def batch_create_job(request: BatchJobCreateRequest) -> dict:
    return create_job(request.upload_id, request.mapping.model_dump())


@app.get("/batch/jobs/{job_id}")
def batch_get_job(job_id: str) -> dict:
    return get_job(job_id)


@app.get("/batch/jobs/{job_id}/results")
def batch_results(job_id: str) -> dict:
    return get_job(job_id)


@app.post("/batch/jobs/{job_id}/run")
def batch_run(job_id: str) -> dict:
    return run_job_thread(job_id)


@app.post("/batch/jobs/{job_id}/cancel")
def batch_cancel(job_id: str) -> dict:
    return cancel_job(job_id)


def _export_response(job_id: str, kind: str, filtered_rows: list[int] | None = None) -> Response:
    filename, content, media_type = export_job(job_id, kind, filtered_rows)
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/batch/jobs/{job_id}/export")
def batch_export(job_id: str, kind: str = "results") -> Response:
    return _export_response(job_id, kind)


@app.post("/batch/jobs/{job_id}/export/filtered")
def batch_filtered_export(job_id: str, request: BatchFilteredExportRequest) -> Response:
    return _export_response(job_id, "filtered", request.row_numbers)


@app.get("/batch/jobs/{job_id}/errors")
def batch_error_export(job_id: str) -> Response:
    return _export_response(job_id, "errors")


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictRequest) -> dict:
    result = predict_adme(request.smiles)

    if "error" in result:
        return _error_response(400, "INVALID_SMILES", result["error"])

    return result


@app.post("/predict/batch")
def predict_batch(request: BatchPredictRequest) -> dict:
    results: list[dict] = []
    valid_entries: list[tuple[int, dict]] = []
    valid_smiles: list[str] = []

    for index, smiles in enumerate(request.smiles_list):
        validation = validate_smiles(smiles)
        if not validation["is_valid"]:
            results.append(
                {
                    "input_smiles": smiles,
                    "canonical_smiles": None,
                    "error": validation["error"] or "Invalid SMILES string.",
                }
            )
            continue

        results.append({})
        valid_entries.append((index, validation))
        valid_smiles.append(validation["canonical_smiles"] or validation["input_smiles"].strip())

    if valid_smiles:
        try:
            predictions = predict_many(valid_smiles)
        except ADMETPredictionError as exc:
            for index, validation in valid_entries:
                results[index] = {
                    "input_smiles": validation["input_smiles"],
                    "canonical_smiles": validation["canonical_smiles"],
                    "error": str(exc),
                }
        else:
            for (index, validation), raw_prediction in zip(valid_entries, predictions, strict=False):
                grouped = group_predictions(raw_prediction)
                results[index] = {
                    "input_smiles": validation["input_smiles"],
                    "canonical_smiles": validation["canonical_smiles"],
                    "predictions": grouped,
                    "summary": generate_summary(grouped),
                    "disclaimer": DISCLAIMER,
                    "prediction_mode": "mock" if is_mock_mode() else "real",
                }

    return {"results": results}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> dict:
    return handle_chat_message(request.message)

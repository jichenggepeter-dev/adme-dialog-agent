from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class PredictRequest(BaseModel):
    smiles: str


class BatchPredictRequest(BaseModel):
    smiles_list: list[str]


class ChatRequest(BaseModel):
    message: str


class SmilesValidationResult(BaseModel):
    is_valid: bool
    input_smiles: str
    canonical_smiles: str | None = None
    error: str | None = None


class PredictionResponse(BaseModel):
    input_smiles: str
    canonical_smiles: str | None
    predictions: dict[str, Any]
    enriched_predictions: dict[str, list[dict[str, Any]]]
    summary: str
    disclaimer: str
    prediction_mode: Literal["mock", "real"]


class ChatResponse(BaseModel):
    message: str
    detected_smiles: str | None
    result: PredictionResponse | None = None


class StatusResponse(BaseModel):
    status: Literal["ok"]
    prediction_mode: Literal["mock", "real"]
    model_loaded: bool
    predictor_available: bool
    backend_version: str
    model_name: str
    model_version: str | None = None
    last_initialized: str | None = None
    execution_environment: str
    input_type: str


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: str | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


class CompoundResolveRequest(BaseModel):
    query: str


class CompoundResponse(BaseModel):
    input_query: str
    preferred_name: str
    pubchem_cid: int | None = None
    molecular_formula: str
    molecular_weight: float
    canonical_smiles: str
    isomeric_smiles: str | None = None
    data_source: str
    depiction_svg: str
    warnings: list[str]


class BatchColumnMapping(BaseModel):
    smiles: str
    compound_id: str | None = None
    compound_name: str | None = None


class BatchJobCreateRequest(BaseModel):
    upload_id: str
    mapping: BatchColumnMapping


class BatchFilteredExportRequest(BaseModel):
    row_numbers: list[int]

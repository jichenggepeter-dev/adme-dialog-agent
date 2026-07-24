export type PredictionMode = "mock" | "real";
export type PredictionCategoryName =
  | "absorption"
  | "distribution"
  | "metabolism"
  | "excretion"
  | "toxicity"
  | "physicochemical"
  | "drug_likeness"
  | "benchmark"
  | "other";

export type EndpointOutputType = "classification_probability" | "classification_label" | "regression" | "descriptor" | "percentile" | "count" | "rule_based" | "derived" | "categorical" | "unknown";

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
export type PredictionGroups = Record<PredictionCategoryName, Record<string, JsonValue>>;

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: string | null;
  };
}

export interface PredictionResponse {
  input_smiles: string;
  canonical_smiles: string | null;
  predictions: PredictionGroups;
  summary: string;
  disclaimer: string;
  prediction_mode: PredictionMode;
  enriched_predictions: Partial<Record<PredictionCategoryName, EnrichedEndpoint[]>>;
}

export interface ChatResponse {
  message: string;
  detected_smiles: string | null;
  result: PredictionResponse | null;
}

export interface StatusResponse {
  status: "ok";
  prediction_mode: PredictionMode;
  model_loaded: boolean;
  predictor_available: boolean;
  backend_version: string;
  model_name: string;
  model_version: string | null;
  last_initialized: string | null;
  execution_environment: string;
  input_type: string;
}

export interface CompoundResponse {
  input_query: string;
  preferred_name: string;
  pubchem_cid: number | null;
  molecular_formula: string;
  molecular_weight: number;
  canonical_smiles: string;
  isomeric_smiles: string | null;
  data_source: string;
  depiction_svg: string;
  warnings: string[];
}

export interface EndpointMetadata {
  raw_name: string;
  raw_key: string;
  display_name: string;
  aliases: string[];
  category: PredictionCategoryName;
  output_type: EndpointOutputType;
  output_type_label: string;
  prediction_type: EndpointOutputType;
  prediction_task: string | null;
  positive_class: string | null;
  unit: string | null;
  unit_verified: boolean;
  description: string | null;
  interpretation_note: string;
  interpretation_limitations: string;
  directionality: string;
  metadata_verified: boolean;
  metadata_status: "verified" | "partial" | "unverified" | "unknown";
  source: { name: string; reference: string | null; version: string | null } | null;
  supports_probability_language: boolean;
  supports_directional_language: boolean;
  compatible_admet_ai_versions: string[];
  experimental_validation_note: string;
}

export interface EnrichedEndpoint extends EndpointMetadata { value: JsonValue; match_type: "exact" | "alias" | "normalized" | "unmatched"; }

export interface EndpointRegistryResponse {
  registry_schema_version: string;
  compatible_admet_ai_versions: string[];
  last_updated: string;
  running_admet_ai_version: string | null;
  compatibility_warning: string | null;
  endpoints: Record<string, EndpointMetadata>;
}

export interface ClientError {
  code: string;
  message: string;
  details?: string;
}

export type BatchFileType = "csv" | "tsv" | "smi";
export type BatchValidationStatus = "valid" | "missing_smiles" | "invalid_smiles" | "duplicate" | "unsupported";
export type BatchPredictionStatus = "not_run" | "pending" | "completed" | "failed";
export type BatchJobStatus = "uploaded" | "validating" | "ready" | "running" | "completed" | "completed_with_errors" | "failed" | "cancelled";

export interface BatchColumnMapping { smiles: string; compound_id: string | null; compound_name: string | null; }
export interface BatchUploadResponse {
  upload_id: string; source_filename: string; file_type: BatchFileType; file_size: number; row_count: number;
  columns: string[]; preview: Record<string, string>[]; suggested_mapping: BatchColumnMapping; created_at: string;
}
export interface BatchValidationSummary {
  total_rows: number; valid_molecules: number; invalid_smiles: number; missing_smiles: number;
  duplicate_molecules: number; unique_valid_molecules: number;
}
export interface BatchProgress { processed: number; total: number; completed: number; failed: number; }
export interface BatchResultRow {
  row_number: number; compound_id: string | null; compound_name: string | null; input_smiles: string;
  canonical_smiles: string | null; validation_status: BatchValidationStatus; error_code: string | null;
  error_message: string | null; duplicate_group: string | null; prediction_status: BatchPredictionStatus;
  predictions: PredictionGroups | null; raw_predictions?: Record<string, JsonValue> | null; summary: string | null;
}
export interface BatchJob {
  job_id: string; source_filename: string; file_type: BatchFileType; mapping: BatchColumnMapping;
  status: BatchJobStatus; prediction_mode: PredictionMode; model_name: string; model_version: string | null;
  created_at: string; updated_at: string; completed_at: string | null; summary: BatchValidationSummary;
  progress: BatchProgress; rows: BatchResultRow[]; disclaimer: string;
}
export interface BatchCapabilities {
  supported_file_types: BatchFileType[]; maximum_file_bytes: number; maximum_rows: number;
  storage: string; worker: string; predictor: Omit<StatusResponse, "status" | "backend_version">;
}

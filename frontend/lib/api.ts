import { API_BASE_URL, REQUEST_TIMEOUT_MS } from "./constants";
import type { ApiError, BatchCapabilities, BatchColumnMapping, BatchJob, BatchUploadResponse, ChatResponse, ClientError, CompoundResponse, EndpointRegistryResponse, PredictionResponse, StatusResponse } from "./types";

export class ApiClientError extends Error implements ClientError {
  code: string;
  details?: string;

  constructor(code: string, message: string, details?: string) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: init?.body instanceof FormData ? init?.headers : { "Content-Type": "application/json", ...init?.headers },
      signal: controller.signal,
    });
    const payload = (await response.json()) as T | ApiError;
    if (!response.ok) {
      if (isApiError(payload)) {
        throw new ApiClientError(payload.error.code, payload.error.message, payload.error.details ?? undefined);
      }
      throw new ApiClientError("INTERNAL_ERROR", "The backend returned an unexpected error.");
    }
    return payload as T;
  } catch (error) {
    if (error instanceof ApiClientError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiClientError("REQUEST_TIMEOUT", "The request timed out.");
    }
    throw new ApiClientError("BACKEND_UNAVAILABLE", "The backend is not reachable.");
  } finally {
    window.clearTimeout(timeout);
  }
}

function isApiError(value: unknown): value is ApiError {
  return typeof value === "object" && value !== null && "error" in value;
}

export function fetchStatus(): Promise<StatusResponse> {
  return request<StatusResponse>("/status", undefined, 5_000);
}

export function predictSmiles(smiles: string): Promise<PredictionResponse> {
  return request<PredictionResponse>("/predict", {
    method: "POST",
    body: JSON.stringify({ smiles }),
  });
}

export function resolveCompound(query: string): Promise<CompoundResponse> {
  return request<CompoundResponse>("/compound/resolve", {
    method: "POST",
    body: JSON.stringify({ query }),
  }, 20_000);
}

export function fetchEndpoints(): Promise<EndpointRegistryResponse> {
  return request<EndpointRegistryResponse>("/endpoints", undefined, 5_000);
}

export function submitChat(message: string): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function fetchBatchCapabilities(): Promise<BatchCapabilities> { return request<BatchCapabilities>("/batch/capabilities", undefined, 5_000); }
export function uploadBatch(file: File): Promise<BatchUploadResponse> {
  const body = new FormData(); body.append("file", file);
  return request<BatchUploadResponse>("/batch/upload", { method: "POST", body }, 30_000);
}
export function createBatchJob(uploadId: string, mapping: BatchColumnMapping): Promise<BatchJob> {
  return request<BatchJob>("/batch/jobs", { method: "POST", body: JSON.stringify({ upload_id: uploadId, mapping }) }, 30_000);
}
export function fetchBatchJob(jobId: string): Promise<BatchJob> { return request<BatchJob>(`/batch/jobs/${jobId}`, undefined, 10_000); }
export function runBatchJob(jobId: string): Promise<BatchJob> { return request<BatchJob>(`/batch/jobs/${jobId}/run`, { method: "POST" }, 10_000); }
export function cancelBatchJob(jobId: string): Promise<BatchJob> { return request<BatchJob>(`/batch/jobs/${jobId}/cancel`, { method: "POST" }, 10_000); }

export async function downloadBatchExport(jobId: string, kind: "results" | "errors" | "metadata" | "json"): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/batch/jobs/${jobId}/${kind === "errors" ? "errors" : `export?kind=${kind}`}`);
  if (!response.ok) throw new ApiClientError("EXPORT_FAILED", "The export could not be generated.");
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? `batch-${jobId}.${kind === "metadata" || kind === "json" ? "json" : "csv"}`;
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}

export async function downloadFilteredBatchExport(jobId: string, rowNumbers: number[]): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/batch/jobs/${jobId}/export/filtered`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ row_numbers: rowNumbers }) });
  if (!response.ok) throw new ApiClientError("EXPORT_FAILED", "The filtered export could not be generated.");
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? `batch-${jobId}-filtered.csv`;
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}

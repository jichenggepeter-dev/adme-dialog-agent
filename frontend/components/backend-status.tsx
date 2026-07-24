import type { StatusResponse } from "@/lib/types";

interface BackendStatusProps {
  status: StatusResponse | null;
  unavailable: boolean;
  onRefresh: () => void;
}

export function BackendStatus({ status, unavailable, onRefresh }: BackendStatusProps) {
  const label = unavailable
    ? "Backend unavailable"
    : status?.prediction_mode === "mock"
      ? "Mock predictions"
      : status?.predictor_available
        ? "Real ADMET-AI"
        : "Model unavailable";

  const tone = unavailable || !status?.predictor_available ? "error" : status.prediction_mode === "mock" ? "warning" : "success";

  return (
    <div className="status-row" aria-live="polite">
      <div className={`status-badge status-${tone}`}>
        <span className="status-dot" aria-hidden="true" />
        <span>{label}</span>
      </div>
      <span className="status-detail">
        {status ? `Backend ${status.backend_version} · Model ${status.model_loaded ? "ready" : "not initialized"}` : "Status not available"}
      </span>
      <button className="text-button" type="button" onClick={onRefresh}>Refresh status</button>
    </div>
  );
}

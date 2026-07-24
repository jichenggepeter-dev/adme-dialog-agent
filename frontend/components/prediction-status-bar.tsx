import { CheckCircle, Clock, Cpu } from "@phosphor-icons/react";
import type { StatusResponse } from "@/lib/types";

export function PredictionStatusBar({ status, lastPrediction }: { status: StatusResponse | null; lastPrediction: Date | null }) {
  const mode = status?.prediction_mode === "mock" ? "Mock predictions" : status ? "Real ADMET-AI" : "Unknown";
  const readiness = status?.predictor_available ? status.model_loaded ? "Model ready" : "Model not initialized" : "Model unavailable";
  return (
    <section className="prediction-status-bar" aria-label="Prediction status">
      <div><Cpu size={24} weight="duotone" aria-hidden="true" /><span><b>Prediction Mode</b>{mode}</span></div>
      <div><CheckCircle size={24} weight="duotone" aria-hidden="true" /><span><b>Readiness</b>{readiness}</span></div>
      <div><Clock size={24} weight="duotone" aria-hidden="true" /><span><b>Last Prediction</b>{lastPrediction ? lastPrediction.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "None this session"}</span></div>
    </section>
  );
}

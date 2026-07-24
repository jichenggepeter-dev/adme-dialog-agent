"use client";
import { CheckCircle, Flask, Info, WarningCircle } from "@phosphor-icons/react";
import { useState } from "react";
import type { Confirmation, PendingAction, StructuredPayload } from "@/lib/agent-types";

const label: Record<string, string> = { prediction: "Prediction summary", endpoint_explanation: "Endpoint details", batch_summary: "Batch summary", batch_errors: "Batch issues", comparison: "Compound comparison", model_information: "Model information", resource: "Scientific resource", error: "Assistant notice", out_of_scope: "Scope boundary" };
const primitive = (value: unknown) => typeof value === "string" || typeof value === "number" || typeof value === "boolean" ? String(value) : null;
export function StructuredCard({ payload }: { payload: StructuredPayload }) {
  const [expanded, setExpanded] = useState(false);
  if (payload.type === "compound_confirmation" || payload.type === "none") return null;
  if (payload.type === "batch_errors" && Array.isArray(payload.data.errors)) {
    const errors = payload.data.errors as Record<string, unknown>[];
    const visible = expanded ? errors : errors.slice(0, 10);
    return <section className="assistant-card assistant-card-batch_errors"><header><WarningCircle size={18} /><strong>Batch issues</strong><span className="assistant-count">{String(payload.data.error_count ?? errors.length)}</span></header><div className="assistant-compact-table">{visible.map((error, index) => <div key={`${String(error.row_number)}-${index}`}><b>Row {String(error.row_number ?? "—")}</b><span>{String(error.compound_name ?? error.compound_id ?? "Unnamed compound")}</span><code>{String(error.error_code ?? "Issue")}</code></div>)}</div>{errors.length > 10 ? <button className="assistant-see-more" onClick={() => setExpanded((value) => !value)}>{expanded ? "Show less" : `See ${errors.length - 10} more`}</button> : null}</section>;
  }
  if (payload.type === "comparison" && Array.isArray(payload.data.matrix)) {
    const matrix = payload.data.matrix as Record<string, unknown>[];
    const visible = expanded ? matrix : matrix.slice(0, 10);
    return <section className="assistant-card assistant-card-comparison"><header><Flask size={18} /><strong>Neutral comparison</strong></header><div className="assistant-compact-table comparison">{visible.map((row) => <div key={String(row.endpoint)}><b>{String(row.endpoint)}</b><span>{Array.isArray(row.values) ? `${row.values.length} compounds` : "No values"}</span></div>)}</div>{matrix.length > 10 ? <button className="assistant-see-more" onClick={() => setExpanded((value) => !value)}>{expanded ? "Show less" : `See ${matrix.length - 10} more`}</button> : null}<small><Info size={13} /> No overall ranking or winner is applied.</small></section>;
  }
  const entries = Object.entries(payload.data).filter(([, value]) => primitive(value) !== null).slice(0, 8);
  const mode = payload.data.prediction_mode;
  return <section className={`assistant-card assistant-card-${payload.type}`}><header>{payload.type === "error" ? <WarningCircle size={18} /> : <Flask size={18} />}<strong>{label[payload.type] ?? "Scientific result"}</strong>{mode === "mock" ? <span className="assistant-mode mock">Mock</span> : mode === "real" ? <span className="assistant-mode real">Real ADMET-AI</span> : null}</header>{entries.length ? <dl>{entries.map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd className={key.includes("smiles") ? "mono" : ""}>{String(value)}</dd></div>)}</dl> : <p>Structured details are available from the linked workspace resource.</p>}</section>;
}
export function ConfirmationCard({ confirmation, loading, onDecision }: { confirmation: Confirmation; loading: boolean; onDecision: (value: "approve" | "reject") => void }) {
  const data = confirmation.payload;
  return <section className="assistant-card confirmation-card"><header><CheckCircle size={19} /><strong>Confirm molecular structure</strong></header><p>Review the resolved structure before any prediction runs.</p><dl>{[["Name", data.preferred_name], ["PubChem CID", data.pubchem_cid], ["Formula", data.molecular_formula], ["Molecular weight", data.molecular_weight], ["Canonical SMILES", confirmation.canonical_smiles]].map(([key, value]) => value != null ? <div key={String(key)}><dt>{String(key)}</dt><dd className={String(key) === "Canonical SMILES" ? "mono" : ""}>{String(value)}</dd></div> : null)}</dl><div className="confirmation-actions"><button className="primary-action" disabled={loading} onClick={() => onDecision("approve")}>Confirm structure</button><button className="secondary-action" disabled={loading} onClick={() => onDecision("reject")}>Change input</button></div><small><Info size={13} /> Computational prediction begins only after confirmation.</small></section>;
}

export function PendingActionCard({ action, loading, onDecision }: { action: PendingAction; loading: boolean; onDecision: (value: "approve" | "reject") => void }) {
  const run = action.action_type === "run_batch_job";
  return <section className="assistant-card confirmation-card batch-action-card"><header><WarningCircle size={19} /><strong>{run ? "Confirm batch prediction" : "Confirm batch cancellation"}</strong></header><p>{run ? "This starts ADMET prediction for the validated unique molecules in this job." : "This stops the current batch job. Completed row results are retained."}</p><dl><div><dt>Job</dt><dd className="mono">{String(action.payload.job_id ?? "Unknown")}</dd></div><div><dt>Current status</dt><dd>{String(action.payload.status_at_proposal ?? "Unknown")}</dd></div></dl><div className="confirmation-actions"><button className={run ? "primary-action" : "primary-action danger-action"} disabled={loading} onClick={() => onDecision("approve")}>{loading ? "Applying…" : run ? "Confirm & Start" : "Confirm cancellation"}</button><button className="secondary-action" disabled={loading} onClick={() => onDecision("reject")}>Keep current state</button></div><small><Info size={13} /> This request expires and can be used only once.</small></section>;
}

"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createBatchJob, fetchBatchCapabilities, runBatchJob, uploadBatch, ApiClientError } from "@/lib/api";
import type { BatchCapabilities, BatchColumnMapping, BatchJob, BatchUploadResponse } from "@/lib/types";
import { BatchUploadPanel } from "./batch-upload-panel";
import { ColumnMappingPanel } from "./column-mapping-panel";
import { ValidationSummary } from "./validation-summary";
import { WorkflowStepper } from "./workflow-stepper";
import { useOptionalAssistant } from "@/contexts/assistant-provider";
import { publishAssistantPageContext } from "@/lib/assistant-page-state";
import { registerAssistantCapabilities } from "@/lib/assistant-capabilities";
import type { UIAction } from "@/lib/agent-types";
import { clearHighlight } from "./assistant/assistant-action-transition";

export function BatchWorkspace() {
  const assistant = useOptionalAssistant();
  const router = useRouter();
  const [capabilities, setCapabilities] = useState<BatchCapabilities | null>(null);
  const [upload, setUpload] = useState<BatchUploadResponse | null>(null);
  const [mapping, setMapping] = useState<BatchColumnMapping>({ smiles: "", compound_id: null, compound_name: null });
  const [job, setJob] = useState<BatchJob | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null);
  const [highlightedTarget, setHighlightedTarget] = useState<string | null>(null);
  const chooseButtonRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { fetchBatchCapabilities().then(setCapabilities).catch(() => setError("The backend is unavailable. Start it and try again.")); }, []);
  useEffect(() => publishAssistantPageContext({
    page: "batch",
    batch_job_id: job?.job_id ?? null,
    selected_compound_ids: [],
    selected_row_numbers: [],
    selected_endpoints: [],
    active_view: job ? "validation" : "upload",
    total_row_count: job?.rows.length ?? upload?.row_count ?? null,
    filtered_row_count: job?.rows.length ?? null,
    visible_row_numbers: job?.rows.slice(0, 20).map((row) => row.row_number) ?? [],
  }), [job, upload?.row_count]);
  useEffect(() => registerAssistantCapabilities("/batch", { execute(action: UIAction) {
    if (action.type !== "FOCUS_BATCH_UPLOAD") throw new Error("unsupported batch setup action");
    if (job || upload) throw new Error("upload workflow already started");
    setHighlightedTarget("batch-upload"); chooseButtonRef.current?.focus(); clearHighlight(setHighlightedTarget);
    return { targetId: "batch-upload", message: "Batch file chooser focused" };
  }}), [job, upload]);

  async function handleFile(file: File) {
    setBusy(true); setError(null); setJob(null);
    try { const result = await uploadBatch(file); setUpload(result); setMapping(result.suggested_mapping); }
    catch (caught) { setError(caught instanceof ApiClientError ? caught.message : "The file could not be uploaded."); }
    finally { setBusy(false); }
  }
  async function validate() {
    if (!upload) return; setBusy(true); setError(null);
    try { setJob(await createBatchJob(upload.upload_id, mapping)); }
    catch (caught) { setError(caught instanceof ApiClientError ? caught.message : "Dataset validation did not complete."); }
    finally { setBusy(false); }
  }
  async function run() {
    if (!job) return; setBusy(true); setError(null);
    try { await runBatchJob(job.job_id); router.push(`/batch/${job.job_id}`); }
    catch (caught) { setError(caught instanceof ApiClientError ? caught.message : "The batch job could not start."); setBusy(false); }
  }
  const step = job ? 3 : upload ? 2 : 1;
  return <div className={`batch-workspace ${assistant?.open && !assistant.closing ? "has-docked-assistant" : ""}`}>
    <WorkflowStepper current={step} />
    {!upload ? <BatchUploadPanel capabilities={capabilities} busy={busy} error={error} highlighted={highlightedTarget === "batch-upload"} chooseButtonRef={chooseButtonRef} onFile={(file) => void handleFile(file)} /> : !job ? <ColumnMappingPanel upload={upload} mapping={mapping} error={error} busy={busy} onChange={setMapping} onContinue={() => void validate()} onReplace={() => { setUpload(null); setError(null); }} /> : <section className="batch-stage-panel validation-stage" aria-labelledby="validation-title">
      <header><div><span className="stage-kicker">Step 3</span><h2 id="validation-title">Review validation</h2><p>Confirm the row-level results before starting prediction.</p></div></header>
      <ValidationSummary summary={job.summary} />
      <div className="table-scroll validation-preview"><table><thead><tr><th>Row</th><th>Compound ID</th><th>Name</th><th>Input SMILES</th><th>Canonical SMILES</th><th>Validation status</th><th>Issue</th></tr></thead><tbody>{job.rows.slice(0, 20).map((row) => <tr key={row.row_number}><td>{row.row_number}</td><td>{row.compound_id ?? "—"}</td><td>{row.compound_name ?? "—"}</td><td><code>{row.input_smiles || "—"}</code></td><td><code>{row.canonical_smiles ?? "—"}</code></td><td><span className={`app-status status-${row.validation_status}`}>{row.validation_status.replaceAll("_", " ")}</span></td><td>{row.error_message ?? (row.duplicate_group ? `Retained in ${row.duplicate_group}` : "—")}</td></tr>)}</tbody></table></div>
      {error ? <p className="batch-inline-error" role="alert">{error}</p> : null}
      <div className="stage-actions"><button className="secondary-action" onClick={() => { setJob(null); setUpload(null); }}>Replace file</button><button className="primary-action" disabled={busy} onClick={() => void run()}>{busy ? "Starting prediction..." : "Run Batch Prediction"}</button></div>
    </section>}
  </div>;
}

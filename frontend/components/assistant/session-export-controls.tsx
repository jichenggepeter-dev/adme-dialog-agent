"use client";

import { DownloadSimple, ShieldCheck } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

import {
  AgentApiError,
  decideSessionExport,
  prepareSessionExport,
} from "@/lib/agent-api";
import type {
  SessionExportFormat,
  SessionExportProposal,
  SessionExportResult,
} from "@/lib/agent-types";


type Props = {
  sessionId: string | null;
  stateVersion: number;
  disabled?: boolean;
};

export function SessionExportControls({ sessionId, stateVersion, disabled = false }: Props) {
  const [format, setFormat] = useState<SessionExportFormat>("json");
  const [proposal, setProposal] = useState<SessionExportProposal | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (proposal && dialog && !dialog.open) dialog.showModal();
    return () => {
      if (dialog?.open) dialog.close();
    };
  }, [proposal]);

  useEffect(() => {
    if (proposal && proposal.action.session_id !== sessionId) {
      queueMicrotask(() => {
        setProposal(null);
        setError("The active session changed. Create a new export proposal.");
        triggerRef.current?.focus();
      });
    }
  }, [proposal, sessionId]);

  useEffect(() => {
    if (proposal && error) errorRef.current?.focus();
  }, [error, proposal]);

  async function prepare() {
    if (!sessionId || busy) return;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      setProposal(await prepareSessionExport(sessionId, format, stateVersion));
    } catch (caught) {
      setError(exportErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function decide(decision: "approve" | "reject") {
    if (!sessionId || !proposal || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await decideSessionExport(
        sessionId,
        proposal.action.action_id,
        decision,
        stateVersion,
      );
      if (decision === "approve") downloadExport(result);
      setProposal(null);
      setNotice(decision === "approve" ? "Session export generated; download initiated." : "Session export cancelled.");
      queueMicrotask(() => triggerRef.current?.focus());
    } catch (caught) {
      setError(exportErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="session-export-controls">
      <label>
        <span className="visually-hidden">Session export format</span>
        <select
          aria-label="Session export format"
          value={format}
          onChange={(event) => setFormat(event.target.value as SessionExportFormat)}
          disabled={disabled || busy || Boolean(proposal)}
        >
          <option value="json">JSON</option>
          <option value="markdown">Markdown</option>
        </select>
      </label>
      <button
        type="button"
        ref={triggerRef}
        className="session-export-button"
        onClick={() => void prepare()}
        disabled={disabled || busy || !sessionId || Boolean(proposal)}
      >
        <DownloadSimple size={14} /> Export
      </button>
      <span className="visually-hidden" role="status" aria-live="polite">{notice}</span>
      {error && !proposal ? <span className="session-export-error" role="alert">{error}</span> : null}

      {proposal ? (
        <dialog
          ref={dialogRef}
          className="session-export-dialog"
          aria-labelledby="session-export-title"
          aria-describedby="session-export-description"
          aria-modal="true"
          aria-busy={busy}
          onCancel={(event) => {
            event.preventDefault();
            if (!busy) void decide("reject");
          }}
        >
          <div className="session-export-dialog-heading">
            <ShieldCheck size={24} weight="fill" />
            <div>
              <h2 id="session-export-title">Confirm session export</h2>
              <p id="session-export-description">
                Review this one-time, current-session-only export before downloading.
              </p>
            </div>
          </div>
          <dl className="session-export-summary">
            <div><dt>Format</dt><dd>{format === "json" ? "JSON" : "Markdown"}</dd></div>
            <div><dt>Snapshot</dt><dd>{new Date(proposal.snapshot_taken_at).toLocaleString()}</dd></div>
            <div><dt>Messages</dt><dd>{proposal.counts.messages}</dd></div>
            <div><dt>Confirmations</dt><dd>{proposal.counts.confirmations}</dd></div>
            <div><dt>Activity events</dt><dd>{proposal.counts.activities}</dd></div>
            <div><dt>Selected resources</dt><dd>{proposal.counts.selected_resources} compound/prediction</dd></div>
          </dl>
          <div className="session-export-scope">
            <section>
              <h3>Included</h3>
              <ul>{proposal.included.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>
            <section>
              <h3>Excluded</h3>
              <ul>{proposal.excluded.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>
          </div>
          <p className="session-export-limit">
            Maximum file size: {(proposal.max_export_bytes / 1_000_000).toFixed(1)} MB.
            Credential-like values may be redacted. If this session changed, you will be asked to review a new export.
          </p>
          {error ? <p ref={errorRef} tabIndex={-1} className="session-export-dialog-error" role="alert">{error} Create a new export proposal if this action was consumed.</p> : null}
          <div className="session-export-dialog-actions">
            <button type="button" onClick={() => void decide("reject")} disabled={busy} autoFocus>
              Cancel
            </button>
            <button type="button" className="primary-action" onClick={() => void decide("approve")} disabled={busy}>
              {busy ? "Preparing…" : `Download ${format === "json" ? "JSON" : "Markdown"}`}
            </button>
          </div>
        </dialog>
      ) : null}
    </div>
  );
}

function exportErrorMessage(caught: unknown): string {
  if (caught instanceof AgentApiError) return caught.message;
  return "The session export could not be completed.";
}

function downloadExport(result: SessionExportResult) {
  if (
    result.status !== "succeeded" ||
    !result.content ||
    !result.filename ||
    !result.media_type
  ) {
    throw new AgentApiError(
      "AGENT_RESPONSE_INVALID",
      "The Agent did not return a complete session export.",
    );
  }
  const url = URL.createObjectURL(new Blob([result.content], { type: result.media_type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = result.filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

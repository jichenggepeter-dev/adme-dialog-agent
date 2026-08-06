"use client";

import { Trash, WarningOctagon } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

import {
  AgentApiError,
  decideSessionDeletion,
  prepareSessionDeletion,
} from "@/lib/agent-api";
import type { SessionDeletionProposal, SessionDeletionResult } from "@/lib/agent-types";


type Props = {
  sessionId: string | null;
  stateVersion: number;
  disabled?: boolean;
  onDelete: (actionId: string) => Promise<SessionDeletionResult>;
};

export function SessionDeletionControls({
  sessionId,
  stateVersion,
  disabled = false,
  onDelete,
}: Props) {
  const [proposal, setProposal] = useState<SessionDeletionProposal | null>(null);
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
    if (proposal && (
      proposal.action.session_id !== sessionId
      || proposal.action.expected_state_version !== stateVersion
    )) {
      queueMicrotask(() => {
        setProposal(null);
        setError("The active session changed. Create a new deletion request.");
        triggerRef.current?.focus();
      });
    }
  }, [proposal, sessionId, stateVersion]);

  useEffect(() => {
    if (proposal && error) errorRef.current?.focus();
  }, [error, proposal]);

  async function prepare() {
    if (!sessionId || busy) return;
    setBusy(true); setError(null); setNotice("");
    try {
      setProposal(await prepareSessionDeletion(sessionId, stateVersion));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally { setBusy(false); }
  }

  async function reject() {
    if (!sessionId || !proposal || busy) return;
    setBusy(true); setError(null);
    try {
      await decideSessionDeletion(
        sessionId,
        proposal.action.action_id,
        "reject",
        stateVersion,
      );
      setProposal(null); setNotice("Session deletion cancelled.");
      queueMicrotask(() => triggerRef.current?.focus());
    } catch (caught) {
      setError(errorMessage(caught));
    } finally { setBusy(false); }
  }

  async function approve() {
    if (!proposal || busy) return;
    setBusy(true); setError(null);
    try {
      await onDelete(proposal.action.action_id);
      setProposal(null); setNotice("Old session deleted.");
      queueMicrotask(() => triggerRef.current?.focus());
    } catch (caught) {
      setError(errorMessage(caught));
    } finally { setBusy(false); }
  }

  return (
    <div className="session-deletion-controls">
      <button
        ref={triggerRef}
        type="button"
        className="session-delete-button"
        onClick={() => void prepare()}
        disabled={disabled || busy || !sessionId || Boolean(proposal)}
      >
        <Trash size={14} /> Delete session
      </button>
      <span className="visually-hidden" role="status" aria-live="polite">{notice}</span>
      {error && !proposal ? <span className="session-delete-error" role="alert">{error}</span> : null}

      {proposal ? (
        <dialog
          ref={dialogRef}
          className="session-delete-dialog"
          aria-labelledby="session-delete-title"
          aria-describedby="session-delete-description"
          aria-modal="true"
          aria-busy={busy}
          onCancel={(event) => {
            event.preventDefault();
            if (!busy) void reject();
          }}
        >
          <div className="session-delete-dialog-heading">
            <WarningOctagon size={26} weight="fill" />
            <div>
              <h2 id="session-delete-title">Delete this Assistant session?</h2>
              <p id="session-delete-description">
                This permanently removes only the current session’s private Agent data.
              </p>
            </div>
          </div>
          <dl className="session-delete-counts">
            <div><dt>Messages</dt><dd>{proposal.counts.messages}</dd></div>
            <div><dt>Confirmations</dt><dd>{proposal.counts.confirmations}</dd></div>
            <div><dt>Pending actions</dt><dd>{proposal.counts.pending_actions}</dd></div>
            <div><dt>Resources</dt><dd>{proposal.counts.resources}</dd></div>
          </dl>
          <div className="session-delete-scope">
            <section>
              <h3>Permanently deleted</h3>
              <ul>{proposal.deleted.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>
            <section>
              <h3>Retained</h3>
              <ul>{proposal.retained.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>
          </div>
          <p className="session-delete-warning">
            Shared Batch uploads and jobs are retained because this version cannot prove they belong only to this session. This action cannot be undone.
          </p>
          {error ? (
            <p ref={errorRef} tabIndex={-1} className="session-delete-dialog-error" role="alert">
              {error} Review a new deletion request if the session changed.
            </p>
          ) : null}
          <div className="session-delete-dialog-actions">
            <button type="button" onClick={() => void reject()} disabled={busy} autoFocus>
              Cancel
            </button>
            <button type="button" className="destructive-action" onClick={() => void approve()} disabled={busy}>
              {busy ? "Deleting…" : "Delete session"}
            </button>
          </div>
        </dialog>
      ) : null}
    </div>
  );
}

function errorMessage(caught: unknown): string {
  if (caught instanceof AgentApiError) return caught.message;
  return "The session deletion could not be completed.";
}

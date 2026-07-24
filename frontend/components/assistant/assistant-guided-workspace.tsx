"use client";

import { ArrowLeft, ArrowRight, BracketsCurly, ChatCircleDots, FileCsv, Flask, WarningCircle } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { useAssistant } from "@/contexts/assistant-provider";
import { downloadPrediction } from "@/components/export-actions";
import { AssistantMarkdown } from "./assistant-markdown";

export function isExplicitConfirmation(value: string, preferredName?: string): boolean {
  const normalized = value.trim().replace(/[。.!！]+$/u, "").trim().toLocaleLowerCase();
  if (["确认", "确认结构", "同意", "是的", "confirm", "confirmed", "yes", "yes confirm"].includes(normalized)) return true;
  if (!preferredName) return false;
  const names = [preferredName, preferredName.split(",")[0]].map((name) => name.trim().toLocaleLowerCase()).filter(Boolean);
  return names.some((name) => normalized === `确认 ${name}` || normalized === `确认${name}` || normalized === `confirm ${name}`);
}

export function AssistantGuidedWorkspace() {
  const { messages, pending, loading, error, guidedPrediction, send, decide, exitGuidedMode } = useAssistant();
  const [draft, setDraft] = useState("");
  const confirmationRef = useRef<HTMLElement>(null);
  const recent = messages.slice(pending ? -2 : -4);
  const compound = pending?.payload ?? null;
  const preferredName = typeof compound?.preferred_name === "string" ? compound.preferred_name : undefined;
  useEffect(() => { if (pending) confirmationRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [pending]);
  function submit(event: React.FormEvent) {
    event.preventDefault(); const value = draft.trim(); if (!value) return; setDraft("");
    if (pending && isExplicitConfirmation(value, preferredName)) { void decide("approve"); return; }
    void send(value);
  }

  return <section className="assistant-guided-workspace" aria-label="Assistant guided analysis">
    <header className="guided-header"><div><span className="assistant-mark"><ChatCircleDots size={20} weight="fill" /></span><div><span className="stage-kicker">Assistant guided analysis</span><h2>Single molecule workflow</h2></div></div><button className="guided-back" onClick={exitGuidedMode}><ArrowLeft size={15} />Manual input</button></header>
    <div className="guided-thread" aria-live="polite">
      {recent.map((message) => <article key={message.message_id} className={`guided-message ${message.role}`}><span>{message.role === "user" ? "You" : "ADME Assistant"}</span><AssistantMarkdown>{message.content}</AssistantMarkdown></article>)}
      {compound && pending ? <section ref={confirmationRef} className="guided-compound-card" aria-labelledby="guided-compound-title">
        <header><div><span className="stage-kicker">Structure confirmation</span><h3 id="guided-compound-title">{String(compound.preferred_name ?? "Resolved compound")}</h3></div><span className="app-status status-pending">Awaiting confirmation</span></header>
        <div className="guided-confirm-actions"><button className="primary-action" disabled={loading} onClick={() => void decide("approve")}>{loading ? "Running prediction…" : "Confirm & Run Prediction"}</button><button className="secondary-action" disabled={loading} onClick={() => void decide("reject")}>Change compound</button></div>
        {typeof compound.depiction_svg === "string" ? <div className="guided-structure" role="img" aria-label={`2D molecular structure for ${String(compound.preferred_name ?? "resolved compound")}`} dangerouslySetInnerHTML={{ __html: compound.depiction_svg }} /> : <div className="guided-structure"><Flask size={34} /><span>Structure preview unavailable</span></div>}
        <dl>{[["Compound name", compound.preferred_name], ["PubChem CID", compound.pubchem_cid], ["Molecular formula", compound.molecular_formula], ["Molecular weight", compound.molecular_weight], ["Canonical SMILES", pending.canonical_smiles]].map(([label, value]) => value != null ? <div key={String(label)}><dt>{String(label)}</dt><dd className={label === "Canonical SMILES" ? "mono" : ""}>{String(value)}</dd></div> : null)}</dl>
        {Array.isArray((compound.input_quality as Record<string, unknown> | undefined)?.warnings) && ((compound.input_quality as Record<string, unknown>).warnings as unknown[]).length ? <p className="guided-quality-warning"><WarningCircle size={15} />Review the input-quality warnings before confirmation.</p> : null}
      </section> : null}
      {guidedPrediction ? <div className="guided-ready"><Flask size={18} /><div className="guided-ready-copy"><strong>Prediction ready</strong><span>Full computational results are displayed in the workspace.</span></div><div className="guided-downloads" aria-label="Download current prediction"><button type="button" onClick={() => downloadPrediction(guidedPrediction, "csv")}><FileCsv size={15} />CSV</button><button type="button" onClick={() => downloadPrediction(guidedPrediction, "json")}><BracketsCurly size={15} />JSON</button></div></div> : null}
      {error ? <div className="assistant-error" role="alert"><strong>Guided workflow unavailable</strong><p>{error.message}</p></div> : null}
    </div>
    <form className="guided-composer" onSubmit={submit}><label className="visually-hidden" htmlFor="guided-message">Continue guided analysis</label><textarea id="guided-message" rows={2} maxLength={8000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={pending ? "Type 确认 or use the confirmation button above…" : "Ask a follow-up about this molecule…"} disabled={loading} /><button aria-label="Send guided message" disabled={!draft.trim() || loading}><ArrowRight size={18} /></button></form>
  </section>;
}

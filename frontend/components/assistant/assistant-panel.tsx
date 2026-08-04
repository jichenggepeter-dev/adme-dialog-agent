"use client";
import { ArrowClockwise, ArrowRight, BracketsCurly, ChatCircleDots, CheckCircle, FileCsv, X } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useAssistant } from "@/contexts/assistant-provider";
import { AssistantLauncher } from "./assistant-launcher";
import { ConfirmationCard, PendingActionCard, StructuredCard } from "./cards/structured-card";
import { AssistantMarkdown } from "./assistant-markdown";
import { downloadPrediction } from "@/components/export-actions";

const TOOL_LABELS: Record<string, string> = { resolve_compound: "Resolved compound", get_compound_context: "Checked structure", predict_single_compound: "Ran ADME prediction", explain_endpoint: "Loaded endpoint metadata", get_model_information: "Read model information", get_batch_job_status: "Read batch status", get_batch_errors: "Checked batch issues", summarize_batch_results: "Summarized batch results", get_batch_rows: "Read batch rows", compare_batch_rows: "Compared batch rows", prepare_batch_action: "Prepared batch action", compare_compounds: "Compared selected compounds" };
const STREAM_LABELS = { idle: "", connecting: "Connecting…", generating: "Generating response…", tool: "Using an approved scientific tool…", waiting_confirmation: "Waiting for your confirmation", completed: "Response complete", failed: "Response stopped" } as const;

export function AssistantPanel() {
  const { open, closing, setOpen, ready, loading, messages, pending, pendingAction, error, streamStatus, actionPhase, actionResult, guidedPrediction, send, cancelStream, decide, decideAction, clearError } = useAssistant();
  const [draft, setDraft] = useState(""); const end = useRef<HTMLDivElement>(null); const pathname = usePathname();
  const batch = pathname.startsWith("/batch");
  useEffect(() => { if (open) end.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, open, pending, pendingAction]);
  function submit(event: React.FormEvent) { event.preventDefault(); const value = draft.trim(); if (!value) return; setDraft(""); void send(value); }
  return <><AssistantLauncher />{open ? <aside className={`assistant-panel assistant-panel-docked ${closing ? "is-closing" : ""} action-${actionPhase}`} aria-label="ADME Assistant" role="complementary">
    <header className="assistant-header"><div><span className="assistant-mark"><ChatCircleDots size={20} weight="fill" /></span><div><strong>ADME Assistant</strong><small><i /> Scientific workspace copilot</small></div></div><button className="icon-button" aria-label="Close Assistant" onClick={() => setOpen(false)}><X size={19} /></button></header>
    <div className="assistant-context"><span>Current context</span><strong>{batch ? "Batch Screening" : pathname.startsWith("/about") ? "Model Information" : "Single Molecule"}</strong></div>
    <div className="assistant-messages" aria-live="polite">
      {!messages.length && ready ? <div className="assistant-welcome"><ChatCircleDots size={27} /><h2>How can I help?</h2><p>{batch ? "Ask for batch upload guidance, status, issues, filters, endpoint columns, or a neutral comparison." : "Ask about a compound, endpoint, model limitation, or the current batch. Structures require confirmation before prediction."}</p><div>{batch ? <><button onClick={() => setDraft(pathname === "/batch" ? "帮我上传并分析一个 Batch 文件。" : "总结当前批次状态和数据质量。")}>{pathname === "/batch" ? "Upload a batch" : "Summarize this batch"}</button><button onClick={() => setDraft("只显示预测失败的分子，并选中第一条。")}>Find failed rows</button></> : <><button onClick={() => setDraft("Explain the current prediction model and its limitations.")}>Explain this model</button><button onClick={() => setDraft("Help me evaluate a small molecule.")}>Evaluate a molecule</button></>}</div></div> : null}
      {messages.map((message) => <article className={`assistant-message ${message.role}`} key={message.message_id}><div className="message-role">{message.role === "user" ? "You" : "ADME Assistant"}</div><AssistantMarkdown>{message.content}</AssistantMarkdown>{message.tools?.length ? <div className="tool-activity">{message.tools.map((tool, index) => <span key={`${tool.tool_name}-${index}`}><CheckCircle size={14} />{TOOL_LABELS[tool.tool_name] ?? "Scientific tool completed"}</span>)}</div> : null}{message.payloads?.map((payload, index) => <StructuredCard key={`${payload.type}-${index}`} payload={payload} />)}</article>)}
      {pending ? <ConfirmationCard confirmation={pending} loading={loading} onDecision={(value) => void decide(value)} /> : null}
      {pendingAction ? <PendingActionCard action={pendingAction} loading={loading} onDecision={(value) => void decideAction(value)} /> : null}
      {streamStatus !== "idle" ? <div className="assistant-thinking" role="status" aria-live="polite">{loading ? <><i /><i /><i /></> : null}<span>{STREAM_LABELS[streamStatus]}</span>{loading ? <button type="button" onClick={cancelStream}>Stop waiting</button> : null}</div> : null}
      {actionResult && !actionResult.ok ? <div className="assistant-error" role="alert"><strong>Could not apply this action</strong><p>{actionResult.message}</p><small>{actionResult.code}</small></div> : null}
      {error ? <div className="assistant-error" role="alert"><strong>{error.code === "AGENT_DISABLED" ? "Assistant is disabled" : "Assistant unavailable"}</strong><p>{error.message}</p>{error.correlationId ? <small>Correlation: {error.correlationId}</small> : null}<button onClick={clearError}><ArrowClockwise size={14} />Dismiss</button></div> : null}<div ref={end} />
    </div>
    {guidedPrediction ? <div className="assistant-result-downloads"><span>Current prediction</span><button type="button" onClick={() => downloadPrediction(guidedPrediction, "csv")}><FileCsv size={14} />CSV</button><button type="button" onClick={() => downloadPrediction(guidedPrediction, "json")}><BracketsCurly size={14} />JSON</button></div> : null}
    <form className="assistant-composer" onSubmit={submit}><label className="visually-hidden" htmlFor="assistant-message">Message ADME Assistant</label><textarea id="assistant-message" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={batch ? "Ask about this batch…" : "Ask about a compound or endpoint..."} maxLength={8000} rows={3} disabled={!ready || loading} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><div><small>Computational guidance only</small><button aria-label="Send message" disabled={!draft.trim() || loading}><ArrowRight size={18} weight="bold" /></button></div></form>
  </aside> : null}</>;
}

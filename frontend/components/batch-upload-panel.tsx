"use client";

import { DownloadSimple, FileArrowUp } from "@phosphor-icons/react";
import { useRef, useState, type DragEvent, type RefObject } from "react";
import type { BatchCapabilities } from "@/lib/types";

export function BatchUploadPanel({ capabilities, busy, error, highlighted = false, chooseButtonRef, onFile }: { capabilities: BatchCapabilities | null; busy: boolean; error: string | null; highlighted?: boolean; chooseButtonRef?: RefObject<HTMLButtonElement | null>; onFile: (file: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null); const [dragging, setDragging] = useState(false);
  function accept(files: FileList | null) { const file = files?.[0]; if (file) onFile(file); }
  function drop(event: DragEvent<HTMLDivElement>) { event.preventDefault(); setDragging(false); accept(event.dataTransfer.files); }
  return <section className={`batch-stage-panel ${highlighted ? "assistant-target-highlight" : ""}`} aria-labelledby="upload-title" data-assistant-target="batch-upload">
    <header><div><span className="stage-kicker">Step 1</span><h2 id="upload-title">Upload compound file</h2></div></header>
    <div className={`batch-dropzone ${dragging ? "is-dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={drop}>
      <FileArrowUp size={42} weight="duotone" aria-hidden="true" />
      <strong>Drop a CSV, TSV, or SMI file here</strong>
      <p>UTF-8, up to {capabilities ? Math.round(capabilities.maximum_file_bytes / 1024 / 1024) : 5} MB and {capabilities?.maximum_rows.toLocaleString() ?? "5,000"} rows.</p>
      <button ref={chooseButtonRef} className="primary-action" type="button" disabled={busy} onClick={() => inputRef.current?.click()}>{busy ? "Reading file..." : "Choose file"}</button>
      <input ref={inputRef} className="visually-hidden" type="file" accept=".csv,.tsv,.smi,text/csv,text/tab-separated-values" onChange={(event) => accept(event.target.files)} aria-label="Choose batch compound file" />
    </div>
    {error ? <p className="batch-inline-error" role="alert">{error}</p> : null}
    <a className="secondary-action download-template" href="/batch-template.csv" download><DownloadSimple size={17} aria-hidden="true" /> Download CSV template</a>
  </section>;
}

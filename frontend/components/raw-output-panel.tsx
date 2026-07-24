"use client";

import { Check, Copy } from "@phosphor-icons/react";
import { useState } from "react";
import type { PredictionResponse } from "@/lib/types";

export function RawOutputPanel({ result }: { result: PredictionResponse }) {
  const [copied, setCopied] = useState(false);
  const raw = JSON.stringify(result, null, 2);
  async function copyRaw() {
    await navigator.clipboard.writeText(raw);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }
  return (
    <details className="raw-response-panel">
      <summary>View Raw Model Response</summary>
      <div className="raw-response-toolbar"><span>Exact backend response</span><button type="button" onClick={copyRaw}>{copied ? <Check size={16} /> : <Copy size={16} />} {copied ? "Copied" : "Copy JSON"}</button></div>
      <pre tabIndex={0}><code>{raw}</code></pre>
    </details>
  );
}

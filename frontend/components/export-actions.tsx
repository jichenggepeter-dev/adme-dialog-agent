"use client";

import { BracketsCurly, Check, Copy, FileCsv } from "@phosphor-icons/react";
import { useState } from "react";
import type { PredictionResponse } from "@/lib/types";

export type PredictionExportFormat = "json" | "csv";

export function predictionCsv(result: PredictionResponse): string {
  const rows = [["category", "endpoint", "value"]];
  Object.entries(result.predictions).forEach(([category, endpoints]) => {
    Object.entries(endpoints).forEach(([endpoint, value]) => rows.push([category, endpoint, typeof value === "object" ? JSON.stringify(value) : String(value)]));
  });
  return rows.map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(",")).join("\n");
}

export function downloadPrediction(result: PredictionResponse, format: PredictionExportFormat): string {
  const json = format === "json";
  const filename = json ? "admet-prediction.json" : "admet-prediction.csv";
  const content = json ? JSON.stringify(result, null, 2) : predictionCsv(result);
  const url = URL.createObjectURL(new Blob([content], { type: json ? "application/json" : "text/csv" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
  return filename;
}

export function ExportActions({ result }: { result: PredictionResponse }) {
  const [feedback, setFeedback] = useState("");
  const raw = JSON.stringify(result, null, 2);

  async function copy(value: string, message: string) {
    await navigator.clipboard.writeText(value);
    setFeedback(message);
    window.setTimeout(() => setFeedback(""), 1800);
  }

  return (
    <div className="export-region">
      <div className="export-actions" aria-label="Export prediction">
        <button type="button" onClick={() => setFeedback(`${downloadPrediction(result, "json")} downloaded.`)}><BracketsCurly size={18} aria-hidden="true" />Download JSON</button>
        <button type="button" onClick={() => setFeedback(`${downloadPrediction(result, "csv")} downloaded.`)}><FileCsv size={18} aria-hidden="true" />Download CSV</button>
        <button type="button" onClick={() => void copy(result.canonical_smiles ?? result.input_smiles, "Canonical SMILES copied.")}><Copy size={18} aria-hidden="true" />Copy Canonical SMILES</button>
        <button type="button" onClick={() => void copy(raw, "Raw output copied.")}><Copy size={18} aria-hidden="true" />Copy Raw Output</button>
      </div>
      <p className="export-feedback" aria-live="polite">{feedback ? <><Check size={16} aria-hidden="true" />{feedback}</> : ""}</p>
    </div>
  );
}

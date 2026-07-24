"use client";

import { Check, Copy, Warning } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import type { CompoundResponse } from "@/lib/types";

interface CompoundConfirmationCardProps {
  compound: CompoundResponse;
  predicting: boolean;
  onPredict: () => void;
  onChangeCompound: () => void;
}

export function CompoundConfirmationCard({ compound, predicting, onPredict, onChangeCompound }: CompoundConfirmationCardProps) {
  const [copied, setCopied] = useState(false);
  const cardRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (typeof window.matchMedia !== "function" || !window.matchMedia("(min-width: 821px)").matches) return;
    const frame = window.requestAnimationFrame(() => cardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    return () => window.cancelAnimationFrame(frame);
  }, [compound.canonical_smiles]);

  async function copySmiles() {
    await navigator.clipboard.writeText(compound.canonical_smiles);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <section ref={cardRef} className="scientific-panel compound-card" aria-labelledby="resolved-heading">
      <h2 id="resolved-heading">Resolved Compound: {compound.preferred_name}</h2>
      <div className="compound-actions compound-actions-prominent">
        <button className="primary-action" type="button" onClick={onPredict} disabled={predicting}>{predicting ? "Running prediction…" : "Confirm Structure & Run Prediction"}</button>
        <button className="secondary-action" type="button" onClick={onChangeCompound} disabled={predicting}>Change Compound</button>
      </div>
      <div className="structure-figure" role="img" aria-label={`2D molecular structure for ${compound.preferred_name}`} dangerouslySetInnerHTML={{ __html: compound.depiction_svg }} />
      <dl className="compound-metadata">
        <div><dt>Compound Name</dt><dd>{compound.preferred_name}</dd></div>
        <div><dt>PubChem CID</dt><dd>{compound.pubchem_cid ?? "Not available"}</dd></div>
        <div><dt>Molecular Formula</dt><dd>{compound.molecular_formula}</dd></div>
        <div><dt>Molecular Weight</dt><dd>{compound.molecular_weight.toLocaleString(undefined, { maximumFractionDigits: 4 })} g/mol</dd></div>
        <div className="smiles-row"><dt>Canonical SMILES</dt><dd><code>{compound.canonical_smiles}</code><button type="button" className="icon-button" onClick={copySmiles} aria-label="Copy canonical SMILES">{copied ? <Check size={17} /> : <Copy size={17} />}</button></dd></div>
        {compound.isomeric_smiles && compound.isomeric_smiles !== compound.canonical_smiles ? <div><dt>Isomeric SMILES</dt><dd><code>{compound.isomeric_smiles}</code></dd></div> : null}
        <div><dt>Data Source</dt><dd>{compound.data_source}</dd></div>
      </dl>
      {compound.warnings.length ? <div className="resolution-warning"><Warning size={17} aria-hidden="true" />{compound.warnings.join(" ")}</div> : null}
      <p className="copy-feedback" aria-live="polite">{copied ? "Canonical SMILES copied." : ""}</p>
    </section>
  );
}

import type { PredictionResponse } from "@/lib/types";

export function PredictionSummary({ result }: { result: PredictionResponse }) {
  return (
    <section className="summary-panel" aria-labelledby="summary-heading">
      <div>
        <p className="section-index">Computational summary</p>
        <h2 id="summary-heading">Model output overview</h2>
      </div>
      <p className="summary-copy">{result.summary}</p>
      <dl className="molecule-identity">
        <div><dt>Submitted</dt><dd>{result.input_smiles}</dd></div>
        <div><dt>Canonical</dt><dd>{result.canonical_smiles ?? "Not available"}</dd></div>
      </dl>
    </section>
  );
}

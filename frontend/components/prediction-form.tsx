import type { FormEvent } from "react";
import { ExampleMolecules } from "./example-molecules";
import { ValidationMessage } from "./validation-message";

interface PredictionFormProps {
  mode: "smiles" | "natural-language";
  value: string;
  loading: boolean;
  error: string | null;
  onModeChange: (mode: "smiles" | "natural-language") => void;
  onValueChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function PredictionForm({ mode, value, loading, error, onModeChange, onValueChange, onSubmit }: PredictionFormProps) {
  const isChat = mode === "natural-language";
  return (
    <section className="input-panel" aria-labelledby="input-heading">
      <div className="panel-heading">
        <div>
          <p className="section-index">01 / Input</p>
          <h2 id="input-heading">Describe the molecule</h2>
        </div>
        <div className="mode-switch" role="group" aria-label="Input mode">
          <button type="button" aria-pressed={!isChat} onClick={() => onModeChange("smiles")}>SMILES</button>
          <button type="button" aria-pressed={isChat} onClick={() => onModeChange("natural-language")}>Natural-language input</button>
        </div>
      </div>

      <form onSubmit={onSubmit} aria-busy={loading}>
        <label htmlFor="molecule-input">{isChat ? "Request containing a SMILES string" : "SMILES string"}</label>
        <p id="input-help" className="field-help">
          {isChat ? "Include the molecular SMILES in a short sentence. This mode uses rule-based extraction." : "Paste one small-molecule SMILES. The backend validates and canonicalizes it."}
        </p>
        <textarea
          id="molecule-input"
          name="molecule"
          rows={isChat ? 4 : 3}
          autoComplete="off"
          spellCheck={false}
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          placeholder={isChat ? "Predict ADME for aspirin: CC(=O)OC1=CC=CC=C1C(=O)O" : "CC(=O)OC1=CC=CC=C1C(=O)O"}
          aria-describedby={`input-help${error ? " prediction-error" : ""}`}
          aria-invalid={Boolean(error)}
        />
        {error ? <ValidationMessage message={error} /> : null}
        {!isChat ? <ExampleMolecules onSelect={onValueChange} /> : null}
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={loading || !value.trim()}>
            {loading ? "Running prediction…" : "Run prediction"}
          </button>
          {loading ? <p role="status">The first real prediction may initialize the model and take longer.</p> : null}
        </div>
      </form>
    </section>
  );
}

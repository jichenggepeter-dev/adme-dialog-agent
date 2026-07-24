import type { FormEvent, RefObject } from "react";
import { EXAMPLE_MOLECULES } from "@/lib/constants";

interface CompoundSearchFormProps {
  value: string;
  loading: boolean;
  error: string | null;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  inputRef?: RefObject<HTMLInputElement | null>;
  highlighted?: boolean;
}

export function CompoundSearchForm({ value, loading, error, onChange, onSubmit, inputRef, highlighted }: CompoundSearchFormProps) {
  return (
    <section className={`scientific-panel search-panel ${highlighted ? "assistant-target-highlight" : ""}`} aria-labelledby="identify-heading" data-assistant-target="compound-input">
      <h2 id="identify-heading">Identify a compound</h2>
      <form onSubmit={onSubmit} aria-busy={loading}>
        <label htmlFor="compound-query">Compound name, PubChem CID, or SMILES</label>
        <input
          id="compound-query"
          ref={inputRef}
          name="compound-query"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Aspirin, CID 2244, or CC(=O)OC1=CC=CC=C1C(=O)O"
          autoComplete="off"
          spellCheck={false}
          aria-describedby={`compound-help${error ? " compound-error" : ""}`}
          aria-invalid={Boolean(error)}
        />
        <p id="compound-help" className="field-note">Enter a common compound name, PubChem CID, or valid SMILES string.</p>
        {error ? <p id="compound-error" className="inline-error" role="alert">{error}</p> : null}
        <button className="primary-action" type="submit" disabled={loading || !value.trim()}>{loading ? "Resolving compound…" : "Resolve Compound"}</button>
      </form>
      <div className="compound-examples" aria-label="Example compounds">
        {EXAMPLE_MOLECULES.map((example) => <button key={example.name} type="button" onClick={() => onChange(example.name)}>{example.name}</button>)}
      </div>
    </section>
  );
}

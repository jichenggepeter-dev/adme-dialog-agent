import { EXAMPLE_MOLECULES } from "@/lib/constants";

export function ExampleMolecules({ onSelect }: { onSelect: (smiles: string) => void }) {
  return (
    <div className="example-group" aria-label="Example molecules">
      <span className="example-label">Examples</span>
      <div className="example-actions">
        {EXAMPLE_MOLECULES.map((molecule) => (
          <button key={molecule.name} type="button" className="example-button" onClick={() => onSelect(molecule.smiles)}>
            {molecule.name}
          </button>
        ))}
      </div>
    </div>
  );
}

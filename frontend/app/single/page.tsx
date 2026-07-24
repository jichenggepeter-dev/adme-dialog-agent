import { SingleMoleculeWorkspace } from "@/components/single-molecule-workspace";

export default function SingleMoleculePage() {
  return (
    <main id="main-content" className="route-main">
      <header className="page-heading">
        <h1>Single Molecule Analysis</h1>
        <p>Resolve a compound, confirm its molecular structure, and generate computational ADME/ADMET predictions.</p>
      </header>
      <SingleMoleculeWorkspace />
    </main>
  );
}

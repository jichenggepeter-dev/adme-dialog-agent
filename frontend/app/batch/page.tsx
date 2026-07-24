import { BatchWorkspace } from "@/components/batch-workspace";

export default function BatchPage() {
  return (
    <main id="main-content" className="route-main secondary-route">
      <header className="page-heading"><h1>Batch Screening</h1><p>Validate, screen, and compare multiple compounds through a structured ADME/ADMET workflow.</p></header>
      <BatchWorkspace />
    </main>
  );
}

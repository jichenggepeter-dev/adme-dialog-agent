import { ModelInformationWorkspace } from "@/components/model-information-workspace";

export default function AboutPage() {
  return (
    <main id="main-content" className="route-main secondary-route">
      <header className="page-heading"><h1>Model Information</h1><p>Understand the prediction backend, endpoint metadata, data sources, and scientific limitations.</p></header>
      <ModelInformationWorkspace />
    </main>
  );
}

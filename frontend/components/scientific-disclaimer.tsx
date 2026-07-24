import { API_BASE_URL } from "@/lib/constants";

export function ScientificDisclaimer() {
  return (
    <footer className="scientific-footer">
      <p><strong>Research-use notice.</strong> These are computational predictions, not experimental measurements. Do not use them as clinical, regulatory, or definitive safety conclusions.</p>
      <p>Local API: <code>{API_BASE_URL}</code></p>
    </footer>
  );
}

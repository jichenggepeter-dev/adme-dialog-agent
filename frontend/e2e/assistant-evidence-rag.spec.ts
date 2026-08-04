import { expect, test } from "@playwright/test";

test("renders a claim-linked evidence card from the typed assistant stream", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/agent/chat/stream", async (route) => {
    const request = route.request();
    const body = request.postDataJSON();
    const common = { version: 1, session_id: body.session_id, message_id: "msg_evidence", correlation_id: request.headers()["x-correlation-id"] };
    const citation = { source_id: "fda-m12-2024", title: "M12 Drug Interaction Studies", organization: "U.S. Food and Drug Administration", url: "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/m12-drug-interaction-studies", document_date: "2024-08", version: "Final Level 1 Guidance", status: "current", captured_at: "2026-08-03", section: "Guidance summary", page: null, chunk_id: "fda-m12-2024:fixture", excerpt: "The guidance provides recommendations on evaluating drug-drug interaction potential." };
    const payload = { type: "evidence_answer", data: { query: body.message, status: "supported", availability: "available", assistant_summary: "Current indexed FDA evidence supports the bounded claims below.", claims: [{ text: citation.excerpt, evidence: [citation] }], evidence: [citation], source_count: 1, warnings: [] } };
    const events = [
      { ...common, type: "message_delta", sequence: 0, delta: "I found current indexed FDA evidence." },
      { ...common, type: "response_completed", sequence: 1, structured_payloads: [payload], pending_confirmation: null, pending_action: null, tool_activity: [{ tool_name: "search_adme_evidence", status: "completed", error_code: null, resource_id: null }], ui_action_proposals: [], warnings: [], state_version: body.expected_state_version },
    ];
    await route.fulfill({ status: 200, contentType: "application/x-ndjson", body: events.map((event) => JSON.stringify(event)).join("\n") + "\n" });
  });

  await page.goto("/single");
  await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await page.getByLabel("Message ADME Assistant").fill("What does M12 say about drug interactions?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByRole("region", { name: "ADME evidence answer" })).toBeVisible();
  await expect(page.getByText("Supported")).toBeVisible();
  await expect(page.getByRole("link", { name: "M12 Drug Interaction Studies" })).toHaveAttribute("href", /fda\.gov/);
  await expect(page.getByText("fda-m12-2024:fixture")).toBeVisible();
});

import { expect, test } from "@playwright/test";

test("streams one assistant message and completes without a duplicate", async ({ page }) => {
  let requestCount = 0;
  await page.route("http://127.0.0.1:8000/agent/chat/stream", async (route) => {
    requestCount += 1;
    const request = route.request();
    const body = request.postDataJSON();
    const common = { version: 1, session_id: body.session_id, message_id: "msg_streamed", correlation_id: request.headers()["x-correlation-id"] };
    const events = [
      { ...common, type: "heartbeat", sequence: 0 },
      { ...common, type: "message_delta", sequence: 1, delta: "Streamed " },
      { ...common, type: "message_delta", sequence: 2, delta: "answer." },
      { ...common, type: "response_completed", sequence: 3, structured_payloads: [], pending_confirmation: null, pending_action: null, tool_activity: [], ui_action_proposals: [], warnings: [], state_version: body.expected_state_version },
    ];
    await route.fulfill({ status: 200, contentType: "application/x-ndjson", body: events.map((event) => JSON.stringify(event)).join("\n") + "\n" });
  });

  await page.goto("/single");
  await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await page.getByLabel("Message ADME Assistant").fill("Stream this response");
  await page.getByRole("button", { name: "Send message" }).click();

  await expect(page.getByRole("status").filter({ hasText: "Response complete" })).toBeVisible();
  await expect(page.locator(".assistant-message.assistant")).toHaveCount(1);
  await expect(page.locator(".assistant-message.assistant")).toContainText("Streamed answer.");
  expect(requestCount).toBe(1);
});

test("surfaces stale state without automatically resending", async ({ page }) => {
  let requestCount = 0;
  await page.route("http://127.0.0.1:8000/agent/chat/stream", async (route) => {
    requestCount += 1;
    const correlationId = route.request().headers()["x-correlation-id"];
    await route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "ACTION_STALE", message: "The session changed. Review it before sending again.", details: null, retryable: true, correlation_id: correlationId } }),
    });
  });

  await page.goto("/single");
  await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await page.getByLabel("Message ADME Assistant").fill("Do this once");
  await page.getByRole("button", { name: "Send message" }).click();

  await expect(page.getByText("The session changed. Review it before sending again.")).toBeVisible();
  expect(requestCount).toBe(1);
});

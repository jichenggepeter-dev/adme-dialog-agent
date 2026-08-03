import path from "node:path";
import { expect, test } from "@playwright/test";

const samples = path.resolve(process.cwd(), "../examples/batch");

async function openAssistant(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await expect(page.getByRole("complementary", { name: "ADME Assistant" })).toBeVisible();
}

test("fills ibuprofen without resolve or prediction and collapses", async ({ page }) => {
  let resolveCount = 0; let predictionCount = 0;
  page.on("request", (request) => { if (request.url().endsWith("/compound/resolve")) resolveCount += 1; if (request.url().endsWith("/predict")) predictionCount += 1; });
  await page.goto("/single"); await openAssistant(page);
  await page.getByLabel("Message ADME Assistant").fill("把 ibuprofen 填入输入框，但先不要运行。");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByLabel("Compound name, PubChem CID, or SMILES")).toHaveValue("ibuprofen");
  await expect(page.locator('[data-assistant-target="compound-input"]')).toHaveClass(/assistant-target-highlight/);
  await expect(page.getByRole("button", { name: /Input updated|Open ADME Assistant/ })).toBeVisible();
  expect(resolveCount).toBe(0); expect(predictionCount).toBe(0);
});

test("opens DILI model information and preserves the session", async ({ page }) => {
  await page.goto("/single"); await openAssistant(page);
  await page.getByLabel("Message ADME Assistant").fill("带我去看 DILI 的模型信息。");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(page.locator('[data-assistant-target="endpoint-DILI"]')).toHaveClass(/assistant-target-highlight/);
  await page.getByRole("button", { name: /Opened DILI metadata|Open ADME Assistant/ }).click();
  await expect(page.getByText("带我去看 DILI 的模型信息。")).toBeVisible();
});

test("applies failed batch filter once", async ({ page }) => {
  await page.goto("/batch");
  await page.getByLabel("Choose batch compound file").setInputFiles(path.join(samples, "sample_mixed.csv"));
  await page.getByRole("button", { name: "Validate dataset" }).click();
  await page.getByRole("button", { name: "Run Batch Prediction" }).click({ force: true });
  await expect(page).toHaveURL(/\/batch\/[0-9a-f-]+/); await openAssistant(page);
  await page.getByLabel("Message ADME Assistant").fill("只显示失败的分子。");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByLabel("Filter prediction status")).toHaveValue("failed");
  await expect(page.locator('[data-assistant-target="batch-results"]')).toHaveClass(/assistant-target-highlight/);
});

test("renders Chinese markdown without raw stars and rejects unknown action", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/agent/chat/stream", async (route) => {
    const request = route.request().postDataJSON();
    const invalid = request.message === "测试未知动作";
    const correlationId = route.request().headers()["x-correlation-id"];
    const common = { version: 1, session_id: request.session_id, message_id: invalid ? "msg_bad" : "msg_markdown", correlation_id: correlationId };
    const events = [
      { ...common, type: "heartbeat", sequence: 0 },
      { ...common, type: "message_delta", sequence: 1, delta: "下面是 **DILI 模型信息**：\n\n- 元数据部分验证" },
      { ...common, type: "response_completed", sequence: 2, structured_payloads: [], pending_confirmation: null, pending_action: null, tool_activity: [], ui_action_proposals: invalid ? [{ type: "EVAL_JAVASCRIPT", action_id: "bad", session_id: request.session_id, target_route: "/single", expected_state_version: request.expected_state_version, payload: {} }] : [], warnings: [], state_version: request.expected_state_version },
    ];
    await route.fulfill({ status: 200, contentType: "application/x-ndjson", body: events.map((event) => JSON.stringify(event)).join("\n") + "\n" });
  });
  await page.goto("/single"); await openAssistant(page);
  await page.getByLabel("Message ADME Assistant").fill("测试格式"); await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator("strong", { hasText: "DILI 模型信息" })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "ADME Assistant" })).not.toContainText("**");
  await page.getByLabel("Message ADME Assistant").fill("测试未知动作"); await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText("The Assistant stream contained an invalid or unknown event.")).toBeVisible();
});

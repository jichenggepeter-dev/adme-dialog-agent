import { expect, test } from "@playwright/test";

test("runs the keyless Mock Agent review flow against the real local API", async ({ page }) => {
  await page.goto("/single");

  await expect(page.getByText("PR Preview · Mock Agent v1")).toBeVisible();
  await expect(page.getByText(/temporary synthetic state/i)).toBeVisible();
  await expect(page.getByText("revision local-e2e")).toBeVisible();

  await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await expect(page.getByLabel("Test scenario")).toHaveValue("success");
  await expect(page.getByText(/message is recorded but does not change/i)).toBeVisible();

  await page.getByLabel("Message ADME Assistant").fill("Show the selected review behavior.");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText(/Mock Agent v1: The deterministic model-information tool completed/)).toBeVisible();
  await expect(page.getByText("Read model information")).toBeVisible();

  await page.getByLabel("Test scenario").selectOption("timeout");
  await page.getByLabel("Message ADME Assistant").fill("Exercise the timeout state.");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText("The local Agent model timed out.")).toBeVisible();
  await page.getByRole("button", { name: "Dismiss" }).click();

  await page.getByLabel("Test scenario").selectOption("confirmation");
  await page.getByLabel("Message ADME Assistant").fill("Exercise the confirmation state.");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByRole("region", { name: "Assistant guided analysis" })).toBeVisible();
  await expect(page.getByText("Resolved SMILES compound")).toBeVisible();
  await page.getByRole("button", { name: "Confirm & Run Prediction" }).click();
  await expect(page.getByRole("heading", { name: "Computational Summary" })).toBeVisible();
  await expect(page.getByText("Mock Predictions")).toBeVisible();
});

import { expect, test, type Page } from "@playwright/test";

const ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O";

async function installAspirinNameResolution(page: Page) {
  const response = await page.request.post("http://127.0.0.1:8000/compound/resolve", { data: { query: ASPIRIN } });
  const compound = await response.json();
  await page.route("http://127.0.0.1:8000/compound/resolve", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ ...compound, input_query: "Aspirin", preferred_name: "Aspirin" }),
  }));
}

async function installDelayedPrediction(page: Page) {
  const response = await page.request.post("http://127.0.0.1:8000/predict", { data: { smiles: ASPIRIN } });
  const prediction = await response.json();
  await page.route("http://127.0.0.1:8000/predict", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 300));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(prediction) });
  });
}

test("resolve, confirm, predict, inspect, export, and navigate", async ({ page }) => {
  await installAspirinNameResolution(page);
  await installDelayedPrediction(page);
  await page.goto("/single");
  await expect(page.getByText("Mock Predictions", { exact: true })).toBeVisible();
  await page.getByLabel("Compound name, PubChem CID, or SMILES").fill("Aspirin");
  await page.getByRole("button", { name: "Resolve Compound" }).click();
  await expect(page.getByRole("heading", { name: "Resolved Compound: Aspirin" })).toBeVisible();
  await expect(page.getByRole("img", { name: "2D molecular structure for Aspirin" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Computational Summary" })).toHaveCount(0);
  await page.getByRole("button", { name: "Confirm Structure & Run Prediction" }).click();
  await expect(page.getByText("Running ADME/ADMET prediction")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Computational Summary" })).toBeVisible();
  await expect(page.getByText(/Development mode/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Absorption" })).toBeVisible();
  await page.getByText("View Raw Model Response").click();
  await expect(page.getByText("Exact backend response")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download JSON" }).click();
  await downloadPromise;
  await page.getByRole("link", { name: "Batch Screening" }).click();
  await expect(page).toHaveURL(/\/batch$/);
  await expect(page.getByRole("link", { name: "Batch Screening" })).toHaveAttribute("aria-current", "page");
  await page.getByRole("link", { name: "Model Information" }).click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(page.getByRole("link", { name: "Model Information" })).toHaveAttribute("aria-current", "page");
});

test("CID and SMILES resolution render confirmation", async ({ page }) => {
  await page.goto("/single");
  await page.getByLabel("Compound name, PubChem CID, or SMILES").fill(ASPIRIN);
  await page.getByRole("button", { name: "Resolve Compound" }).click();
  await expect(page.getByText("Local RDKit")).toBeVisible();
  await page.getByRole("button", { name: "Change Compound" }).click();
  await expect(page.getByRole("heading", { name: "Resolved Compound: Resolved SMILES compound" })).toHaveCount(0);
});

test("resolution error preserves input", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/compound/resolve", (route) => route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { code: "COMPOUND_NOT_FOUND", message: "No match" } }) }));
  await page.goto("/single");
  await page.getByLabel("Compound name, PubChem CID, or SMILES").fill("Unknown compound name");
  await page.getByRole("button", { name: "Resolve Compound" }).click();
  await expect(page.locator("#compound-error")).toContainText("No matching compound was found");
  await expect(page.getByLabel("Compound name, PubChem CID, or SMILES")).toHaveValue("Unknown compound name");
});

test("backend unavailable keeps resolution input usable", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/**", (route) => route.abort());
  await page.goto("/single");
  await expect(page.getByText("Backend Unavailable", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Compound name, PubChem CID, or SMILES")).toBeEnabled();
});

test("mobile single page has no horizontal overflow", async ({ page }) => {
  await page.goto("/single");
  await page.getByLabel("Compound name, PubChem CID, or SMILES").fill(ASPIRIN);
  await page.getByRole("button", { name: "Resolve Compound" }).click();
  await page.getByRole("button", { name: "Confirm Structure & Run Prediction" }).click();
  await expect(page.getByRole("heading", { name: "Computational Summary" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});

test("keyboard submits resolution and opens raw disclosure", async ({ page }) => {
  await page.goto("/single");
  const input = page.getByLabel("Compound name, PubChem CID, or SMILES");
  await input.fill(ASPIRIN);
  await input.press("Enter");
  await expect(page.getByRole("heading", { name: "Resolved Compound: Resolved SMILES compound" })).toBeVisible();
  await page.getByRole("button", { name: "Confirm Structure & Run Prediction" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Computational Summary" })).toBeVisible();
  await page.getByText("View Raw Model Response").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Exact backend response")).toBeVisible();
});

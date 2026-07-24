import path from "node:path";
import { expect, test } from "@playwright/test";

const samples = path.resolve(process.cwd(), "../examples/batch");

test("batch mock success from upload through review and export", async ({ page }) => {
  await page.goto("/batch");
  await expect(page.getByRole("heading", { name: "Upload compound file" })).toBeVisible();
  await page.getByLabel("Choose batch compound file").setInputFiles(path.join(samples, "sample_valid.csv"));
  await expect(page.getByRole("heading", { name: "Map source columns" })).toBeVisible();
  await page.getByRole("button", { name: "Validate dataset" }).click();
  await expect(page.getByRole("heading", { name: "Review validation" })).toBeVisible();
  await expect(page.getByText("Unique valid molecules").locator("..").getByText("3")).toBeVisible();
  await page.getByRole("button", { name: "Run Batch Prediction" }).click({ force: true });
  await expect(page).toHaveURL(/\/batch\/[0-9a-f-]+/);
  await expect(page.getByText("completed", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Development mode/)).toBeVisible();
  await page.getByPlaceholder("Search compounds").fill("Ethanol");
  await expect(page.getByRole("cell", { name: "Ethanol" })).toBeVisible();
  await page.getByPlaceholder("Search compounds").fill("");
  await page.getByLabel("Compare row 1").check(); await page.getByLabel("Compare row 2").check();
  await page.getByRole("button", { name: /Compare \(2\)/ }).click();
  await expect(page.getByRole("heading", { name: "Selected compounds" })).toBeVisible();
  await page.getByRole("button", { name: "Open full detail" }).click();
  await expect(page.getByText("Raw row output")).toBeVisible();
  const download = page.waitForEvent("download"); await page.getByRole("button", { name: "Results", exact: true }).click(); await download;
});

test("mixed input keeps invalid, missing, and duplicate rows", async ({ page }) => {
  await page.goto("/batch");
  await page.getByLabel("Choose batch compound file").setInputFiles(path.join(samples, "sample_mixed.csv"));
  await page.getByRole("button", { name: "Validate dataset" }).click();
  await expect(page.getByText("invalid smiles", { exact: true })).toBeVisible();
  await expect(page.getByText("missing smiles", { exact: true })).toBeVisible();
  await expect(page.getByText("duplicate", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Run Batch Prediction" }).click({ force: true });
  await expect(page.getByText("completed", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("invalid smiles", { exact: true })).toBeVisible();
  const download = page.waitForEvent("download"); await page.getByRole("button", { name: "Errors", exact: true }).click(); await download;
});

test("about exposes actual model and filterable endpoint metadata", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByRole("heading", { name: "Model Overview" })).toBeVisible();
  await expect(page.getByText("Deterministic development fixture")).toBeVisible();
  await page.getByPlaceholder("Search endpoints").fill("BBB");
  await expect(page.getByText("BBB_Martins").first()).toBeVisible();
  await page.getByRole("button", { name: "Details" }).first().click();
  await expect(page.getByText("Blood-Brain Barrier Penetration", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Not clinical conclusions")).toBeVisible();
  await expect(page.getByText(/Partial metadata does not imply/)).toBeVisible();
  await page.getByRole("link", { name: "Batch Screening" }).click();
  await expect(page.getByRole("link", { name: "Batch Screening" })).toHaveAttribute("aria-current", "page");
});

test("batch and about do not overflow the page viewport", async ({ page }) => {
  for (const route of ["/batch", "/about"]) {
    await page.goto(route);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  }
});

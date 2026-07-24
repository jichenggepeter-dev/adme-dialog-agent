import { test } from "@playwright/test";
import path from "node:path";

test("capture routed single-molecule states", async ({ browser }) => {
  const desktop = await browser.newPage({ viewport: { width: 1584, height: 994 } });
  await desktop.goto("http://localhost:3000/single");
  await desktop.getByLabel("Compound name, PubChem CID, or SMILES").fill("Aspirin");
  await desktop.getByRole("button", { name: "Resolve Compound" }).click();
  await desktop.getByRole("button", { name: "Confirm Structure & Run Prediction" }).click();
  await desktop.getByRole("heading", { name: "Computational Summary" }).waitFor();
  await desktop.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await desktop.screenshot({ path: "../docs/images/single-reference-desktop.png", fullPage: true });

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
  await mobile.goto("http://localhost:3000/single");
  await mobile.getByLabel("Compound name, PubChem CID, or SMILES").fill("Aspirin");
  await mobile.getByRole("button", { name: "Resolve Compound" }).click();
  await mobile.getByRole("button", { name: "Confirm Structure & Run Prediction" }).click();
  await mobile.getByRole("heading", { name: "Computational Summary" }).waitFor();
  await mobile.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await mobile.screenshot({ path: "../docs/images/single-reference-mobile.png", fullPage: true });
});

test("capture batch and model information states", async ({ browser }) => {
  for (const viewport of [{ name: "desktop", width: 1584, height: 994 }, { name: "mobile", width: 390, height: 844 }]) {
    const about = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, isMobile: viewport.name === "mobile" });
    await about.goto("http://localhost:3000/about");
    await about.getByRole("heading", { name: "Endpoint Catalog" }).waitFor();
    await about.screenshot({ path: `../docs/images/about-reference-${viewport.name}.png`, fullPage: true });
    await about.close();

    const batch = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, isMobile: viewport.name === "mobile" });
    await batch.goto("http://localhost:3000/batch");
    await batch.getByLabel("Choose batch compound file").setInputFiles(path.resolve(process.cwd(), "../examples/batch/sample_mixed.csv"));
    await batch.getByRole("button", { name: "Validate dataset" }).click({ force: true });
    await batch.getByRole("button", { name: "Run Batch Prediction" }).click({ force: true });
    await batch.waitForURL(/\/batch\/[0-9a-f-]+/);
    await batch.getByText("completed", { exact: true }).first().waitFor();
    await batch.locator(".batch-structure svg").waitFor();
    await batch.screenshot({ path: `../docs/images/batch-reference-${viewport.name}.png`, fullPage: true });
    await batch.close();
  }
});

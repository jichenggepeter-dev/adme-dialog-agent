import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function expectNoSevereViolations(page: Page, testInfo: TestInfo, label: string) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  await testInfo.attach(`axe-${label}`, {
    body: JSON.stringify(results, null, 2),
    contentType: "application/json",
  });
  expect(results.violations.filter((violation) => ["critical", "serious"].includes(violation.impact ?? ""))).toEqual([]);
}

test("core pages have no severe automated WCAG violations", async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const route of ["single", "batch", "about"]) {
    await page.goto(`/${route}`);
    await expect(page.locator("#main-content")).toBeVisible();
    await expect(page.getByText("Backend Connected", { exact: true })).toBeVisible();
    await expect(page.getByText("Mock Predictions", { exact: true })).toBeVisible();
    await expectNoSevereViolations(page, testInfo, route);
  }
});

test("Assistant evidence and streaming status remain accessible", async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/single");
  const launcher = page.getByRole("button", { name: "Open ADME Assistant" });
  await launcher.focus();
  await launcher.press("Enter");
  await expect(page.getByRole("button", { name: "Close Assistant" })).toBeFocused();

  const scenario = page.getByLabel("Test scenario");
  const composer = page.getByLabel("Message ADME Assistant");
  await scenario.selectOption("success");
  await composer.fill("Show the fixed evidence scenario");
  await composer.press("Enter");
  const evidence = page.getByRole("region", { name: "ADME evidence answer" });
  await expect(evidence).toBeVisible();
  await expect(evidence.getByText("Supported", { exact: true })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Response complete" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Assistant conversation" })).not.toHaveAttribute("aria-live");
  await expectNoSevereViolations(page, testInfo, "assistant-evidence");

  const close = page.getByRole("button", { name: "Close Assistant" });
  await close.focus();
  await close.press("Enter");
  await expect(page.getByRole("button", { name: "Open ADME Assistant" })).toBeFocused();
});

test("Assistant confirmation is named and keyboard ordered", async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/single");
  await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await page.getByLabel("Test scenario").selectOption("confirmation");
  const composer = page.getByLabel("Message ADME Assistant");
  await composer.fill("Prepare the fixed confirmation scenario");
  await composer.press("Enter");
  const confirmation = page.getByRole("region", { name: "Resolved SMILES compound" });
  await expect(confirmation).toBeVisible();
  await expect(confirmation.getByText("Awaiting confirmation", { exact: true })).toBeVisible();
  const confirm = confirmation.getByRole("button", { name: "Confirm & Run Prediction" });
  const change = confirmation.getByRole("button", { name: "Change compound" });
  await confirm.focus();
  await page.keyboard.press("Tab");
  await expect(change).toBeFocused();
  await expectNoSevereViolations(page, testInfo, "assistant-confirmation");
});

test("Assistant error is announced and dismissible by keyboard", async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/single");
  await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await page.getByLabel("Test scenario").selectOption("timeout");
  const composer = page.getByLabel("Message ADME Assistant");
  await composer.fill("Run the fixed timeout scenario");
  await composer.press("Enter");
  const alert = page.getByRole("alert").filter({ hasText: "Assistant unavailable" });
  await expect(alert).toBeVisible();
  await expectNoSevereViolations(page, testInfo, "assistant-error");
  const dismiss = alert.getByRole("button", { name: "Dismiss" });
  await dismiss.focus();
  await dismiss.press("Enter");
  await expect(alert).toHaveCount(0);
});

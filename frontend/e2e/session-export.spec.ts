import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";


test("reviews and downloads the current session as versioned JSON", async ({ page }) => {
  await page.goto("/single");
  await page.getByRole("button", { name: "Open ADME Assistant" }).click();

  await page.getByRole("button", { name: "Export" }).click();
  const dialog = page.getByRole("dialog", { name: "Confirm session export" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("conversation messages");
  await expect(dialog).toContainText("internal and system prompts");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    dialog.getByRole("button", { name: "Download JSON" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("adme-session-export.json");
  const path = await download.path();
  expect(path).not.toBeNull();
  const document = JSON.parse(await readFile(path!, "utf8"));
  expect(document.export_schema_version).toBe("1.0");
  expect(document.prediction_mode).toBe("unknown");
  expect(document.session).not.toHaveProperty("session_id");
  expect(document.excluded_fields).toContain("internal and system prompts");
  expect(document).not.toHaveProperty("api_key");
  await expect(dialog).not.toBeVisible();
});

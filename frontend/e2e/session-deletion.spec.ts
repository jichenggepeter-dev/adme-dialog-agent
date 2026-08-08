import { expect, test } from "@playwright/test";


test("deletes only the current session and starts a clean replacement", async ({ page, request }) => {
  const preparedSessions: string[] = [];
  page.on("request", (outgoing) => {
    const match = outgoing.url().match(/\/agent\/sessions\/([^/]+)\/deletions$/);
    if (match && outgoing.method() === "POST") preparedSessions.push(decodeURIComponent(match[1]));
  });

  await page.goto("/single");
  await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await page.getByLabel("Message ADME Assistant").fill("Create private session history.");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText("Create private session history.")).toBeVisible();
  await expect(page.getByText(/Mock Agent v1:/)).toBeVisible();

  await page.getByRole("button", { name: "Delete session" }).click();
  const dialog = page.getByRole("dialog", { name: "Delete this Assistant session?" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("shared Batch uploads and jobs");
  await expect(dialog).toContainText("This action cannot be undone");
  await dialog.getByRole("button", { name: "Delete session" }).click();

  await expect(dialog).not.toBeVisible();
  await expect(page.getByText("Create private session history.")).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "How can I help?" })).toBeVisible();
  expect(preparedSessions).toHaveLength(1);
  const deleted = await request.get(
    `http://127.0.0.1:8000/agent/sessions/${encodeURIComponent(preparedSessions[0])}`,
  );
  expect(deleted.status()).toBe(404);

  await page.getByRole("button", { name: "Delete session" }).click();
  const replacementDialog = page.getByRole("dialog", { name: "Delete this Assistant session?" });
  await expect(replacementDialog).toBeVisible();
  await expect(replacementDialog.locator(".session-delete-counts")).toContainText(/Messages\s*0/);
  await replacementDialog.getByRole("button", { name: "Cancel" }).click();
  await expect(replacementDialog).not.toBeVisible();
});

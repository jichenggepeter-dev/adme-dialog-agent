import { expect, test } from "@playwright/test";

const compound = {
  compound_id: "compound_guided", input_query: "ibuprofen", preferred_name: "Ibuprofen",
  pubchem_cid: 3672, molecular_formula: "C13H18O2", molecular_weight: 206.28,
  canonical_smiles: "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", isomeric_smiles: null,
  data_source: "PubChem", depiction_svg: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 160'><path d='M25 90 L70 60 L115 90 L160 60 L210 90' fill='none' stroke='black' stroke-width='4'/></svg>",
  warnings: [], input_quality: { warnings: [] },
};
const predictions = {
  absorption: { Caco2_Wang: 0.71, HIA_Hou: 0.89, Bioavailability_Ma: 0.56 },
  distribution: { BBB_Martins: 0.34, PPBR_AZ: 0.72 }, metabolism: { CYP2D6_Substrate: 0.12, CYP3A4_Inhibitor: 0.22 },
  excretion: { Clearance_Hepatocyte_AZ: 5.3, Half_Life: 2.8 }, toxicity: { hERG: 0.21, DILI: 0.31, AMES: 0.15 },
  physicochemical: {}, drug_likeness: {}, benchmark: {}, other: {},
};

test("assistant-guided compound confirmation docks left and renders results right", async ({ page }) => {
  let chatCount = 0;
  await page.route("http://127.0.0.1:8000/agent/chat", async (route) => {
    chatCount += 1;
    const body = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message_id: `msg_${chatCount}`, text: "请确认 Ibuprofen 的结构，确认后我会运行计算预测。", structured_payloads: [{ type: "compound_confirmation", data: compound }], pending_confirmation: { confirmation_id: "confirm_guided", session_id: body.session_id, type: "compound_structure", status: "awaiting_confirmation", payload: compound, payload_hash: "hash", canonical_smiles: compound.canonical_smiles, expected_state_version: body.expected_state_version, created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 60_000).toISOString(), version: 0, result_resource_id: null, error_code: null }, tool_activity: [{ tool_name: "resolve_compound", status: "completed", error_code: null, resource_id: "resource_compound" }], ui_action_proposals: [], warnings: [], state_version: body.expected_state_version }) });
  });
  await page.route("http://127.0.0.1:8000/agent/confirm", async (route) => {
    const body = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message_id: "msg_prediction", text: "Ibuprofen 的计算预测已经完成。", structured_payloads: [{ type: "prediction", data: { prediction_resource_id: "resource_prediction", prediction_mode: "mock" } }], pending_confirmation: null, tool_activity: [{ tool_name: "predict_single_compound", status: "completed", error_code: null, resource_id: "resource_prediction" }], ui_action_proposals: [], warnings: [], state_version: body.expected_state_version + 2 }) });
  });
  await page.route(/http:\/\/127\.0\.0\.1:8000\/agent\/resources\/resource_prediction.*/, async (route) => {
    const sessionId = new URL(route.request().url()).searchParams.get("session_id");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ resource_id: "resource_prediction", session_id: sessionId, resource_type: "prediction", content_hash: "hash", size_bytes: 100, created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 60_000).toISOString(), data: { input_smiles: compound.canonical_smiles, canonical_smiles: compound.canonical_smiles, predictions, enriched_predictions: {}, summary: "Computational prediction summary.", disclaimer: "Computational predictions only.", prediction_mode: "mock" } }) });
  });

  await page.goto("/single"); await page.getByRole("button", { name: "Open ADME Assistant" }).click();
  await page.getByLabel("Message ADME Assistant").fill("帮我预测 ibuprofen"); await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByRole("region", { name: "Assistant guided analysis" })).toBeVisible();
  await expect(page.getByRole("img", { name: "2D molecular structure for Ibuprofen" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirm & Run Prediction" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Identify a compound" })).toHaveCount(0);
  await page.getByLabel("Continue guided analysis").fill("确认");
  await page.getByRole("button", { name: "Send guided message" }).click();
  await expect(page.getByRole("heading", { name: "Computational Summary" })).toBeVisible();
  await expect(page.locator(".endpoint-row")).toHaveCount(10);
  await expect(page.getByRole("button", { name: "See 2 more" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open ADME Assistant" })).toHaveCount(0);
});

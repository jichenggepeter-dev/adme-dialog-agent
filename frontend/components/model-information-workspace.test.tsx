import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ModelInformationWorkspace } from "./model-information-workspace";
import * as api from "@/lib/api";
import type { EndpointMetadata } from "@/lib/types";

vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchStatus: vi.fn(), fetchEndpoints: vi.fn() }));

const endpoint: EndpointMetadata = {
  raw_name: "molecular_weight", raw_key: "molecular_weight", display_name: "Molecular Weight", aliases: ["Molecular Weight"],
  category: "physicochemical", output_type: "descriptor", output_type_label: "Molecular descriptor", prediction_type: "descriptor",
  prediction_task: "rdkit_calculation", positive_class: null, unit: "Da", unit_verified: true,
  description: "Calculated molecular property.", interpretation_note: "Not experimental.", interpretation_limitations: "Not experimental.",
  directionality: "context_dependent", metadata_verified: true, metadata_status: "verified",
  source: { name: "ADMET-AI bundled endpoint metadata", reference: "https://www.rdkit.org/", version: "2.0.1" },
  supports_probability_language: false, supports_directional_language: false, compatible_admet_ai_versions: ["2.x"], experimental_validation_note: "Validate experimentally.",
};

describe("ModelInformationWorkspace", () => {
  beforeEach(() => {
    vi.mocked(api.fetchStatus).mockResolvedValue({ status: "ok", prediction_mode: "mock", model_loaded: false, predictor_available: true, backend_version: "test", model_name: "Fixture", model_version: null, last_initialized: null, execution_environment: "local", input_type: "small-molecule SMILES" });
    vi.mocked(api.fetchEndpoints).mockResolvedValue({ registry_schema_version: "2.0", compatible_admet_ai_versions: ["2.x"], last_updated: "2026-07-11", running_admet_ai_version: "2.0.1", compatibility_warning: null, endpoints: { molecular_weight: endpoint } });
  });

  it("shows output type, verified unit, provenance, and scientific boundaries", async () => {
    render(<ModelInformationWorkspace />);
    expect(await screen.findByText("Fixture")).toBeInTheDocument();
    expect(screen.getAllByText("Molecular descriptor").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Da").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ADMET-AI bundled endpoint metadata/).length).toBeGreaterThan(0);
    expect(screen.getByText("Model probabilities are not clinical risks.")).toBeInTheDocument();
  });

  it("filters endpoint search and output metadata", async () => {
    render(<ModelInformationWorkspace />); await screen.findAllByText("molecular_weight");
    await userEvent.type(screen.getByPlaceholderText("Search endpoints"), "missing");
    await waitFor(() => expect(screen.getByText("Showing 0 of 0 endpoints")).toBeInTheDocument());
  });
});

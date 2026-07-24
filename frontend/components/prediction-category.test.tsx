import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PredictionCategory } from "./prediction-category";

describe("PredictionCategory", () => {
  it("renders category values and count", () => {
    render(<PredictionCategory category="absorption" values={{ Caco2_Wang: 0.71 }} />);
    expect(screen.getByRole("heading", { name: "Absorption" })).toBeInTheDocument();
    expect(screen.getByText("1 endpoint")).toBeInTheDocument();
    expect(screen.getByText("0.71")).toBeInTheDocument();
  });

  it("renders an explicit empty category", () => {
    render(<PredictionCategory category="distribution" values={{}} />);
    expect(screen.getByText("No endpoints returned in this category.")).toBeInTheDocument();
  });

  it("renders an unknown endpoint without interpretation", () => {
    render(<PredictionCategory category="other" values={{ New_Endpoint: 3.2 }} />);
    expect(screen.getByText("New Endpoint")).toBeInTheDocument();
    expect(screen.getAllByText("Metadata not verified").length).toBeGreaterThan(0);
  });

  it("renders precise non-model output badges", () => {
    const base = { raw_name: "molecular_weight", raw_key: "molecular_weight", display_name: "Molecular Weight", aliases: [], category: "physicochemical" as const, output_type: "descriptor" as const, output_type_label: "Molecular descriptor", prediction_type: "descriptor" as const, prediction_task: "rdkit_calculation", positive_class: null, unit: "Da", unit_verified: true, description: "Calculated descriptor.", interpretation_note: "Calculated.", interpretation_limitations: "Not experimental.", directionality: "context_dependent", metadata_verified: true, metadata_status: "verified" as const, source: { name: "RDKit", reference: null, version: "test" }, supports_probability_language: false, supports_directional_language: false, compatible_admet_ai_versions: ["2.x"], experimental_validation_note: "Validate." };
    render(<PredictionCategory category="physicochemical" values={{ molecular_weight: 180.16 }} endpointRegistry={{ molecular_weight: base }} />);
    expect(screen.getByRole("heading", { name: "Physicochemical" })).toBeInTheDocument();
    expect(screen.getAllByText("Molecular descriptor").length).toBeGreaterThan(0);
    expect(screen.getByText("180.16 Da")).toBeInTheDocument();
  });
});

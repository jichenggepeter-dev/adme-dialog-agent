import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CompoundConfirmationCard } from "./compound-confirmation-card";

describe("CompoundConfirmationCard", () => {
  it("renders backend compound metadata and structure", () => {
    render(<CompoundConfirmationCard compound={{
      input_query: "CCO",
      preferred_name: "Resolved SMILES compound",
      pubchem_cid: null,
      molecular_formula: "C2H6O",
      molecular_weight: 46.069,
      canonical_smiles: "CCO",
      isomeric_smiles: "CCO",
      data_source: "Local RDKit",
      depiction_svg: '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
      warnings: [],
    }} predicting={false} onPredict={vi.fn()} onChangeCompound={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Resolved Compound: Resolved SMILES compound" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "2D molecular structure for Resolved SMILES compound" })).toBeInTheDocument();
    expect(screen.getByText("C2H6O")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm Structure & Run Prediction" })).toBeEnabled();
  });
});

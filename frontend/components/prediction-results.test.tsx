import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import userEvent from "@testing-library/user-event";
import type { PredictionResponse } from "@/lib/types";
import { PredictionResults } from "./prediction-results";

const result: PredictionResponse = {
  input_smiles: "CCO",
  canonical_smiles: "CCO",
  prediction_mode: "mock",
  enriched_predictions: {},
  summary: "Computational summary text.",
  disclaimer: "Disclaimer",
  predictions: {
    absorption: { Caco2_Wang: 0.71 }, distribution: {}, metabolism: {},
    excretion: {}, toxicity: {}, physicochemical: {}, drug_likeness: {}, benchmark: {}, other: {},
  },
};

describe("PredictionResults", () => {
  it("makes mock mode obvious and renders all categories", () => {
    render(<PredictionResults result={result} />);
    expect(screen.getByText(/Development mode/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Absorption" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Distribution" })).not.toBeInTheDocument();
  });

  it("shows a uniform ten-row preview and expands the remaining endpoints", async () => {
    const user = userEvent.setup();
    const expanded: PredictionResponse = { ...result, predictions: { ...result.predictions,
      absorption: Object.fromEntries(Array.from({ length: 6 }, (_, index) => [`Abs_${index}`, index])),
      distribution: Object.fromEntries(Array.from({ length: 6 }, (_, index) => [`Dist_${index}`, index])),
    } };
    const { container } = render(<PredictionResults result={expanded} />);
    expect(container.querySelectorAll(".endpoint-row")).toHaveLength(10);
    expect(screen.getByText("Showing 10 of 12 endpoints")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "See 2 more" }));
    expect(container.querySelectorAll(".endpoint-row")).toHaveLength(12);
    expect(screen.getByText("Showing 12 of 12 endpoints")).toBeInTheDocument();
  });
});

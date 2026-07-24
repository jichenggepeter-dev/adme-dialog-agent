import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PredictionForm } from "./prediction-form";

describe("PredictionForm", () => {
  it("disables submit for empty input", () => {
    render(<PredictionForm mode="smiles" value="" loading={false} error={null} onModeChange={vi.fn()} onValueChange={vi.fn()} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Run prediction" })).toBeDisabled();
  });

  it("retains and displays input with an error", () => {
    render(<PredictionForm mode="smiles" value="bad-input" loading={false} error="Invalid SMILES" onModeChange={vi.fn()} onValueChange={vi.fn()} onSubmit={vi.fn()} />);
    expect(screen.getByLabelText("SMILES string")).toHaveValue("bad-input");
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid SMILES");
  });

  it("populates an example without submitting", async () => {
    const onValueChange = vi.fn();
    const onSubmit = vi.fn();
    render(<PredictionForm mode="smiles" value="" loading={false} error={null} onModeChange={vi.fn()} onValueChange={onValueChange} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole("button", { name: "Aspirin" }));
    expect(onValueChange).toHaveBeenCalledWith("CC(=O)OC1=CC=CC=C1C(=O)O");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StructuredCard } from "./structured-card";

describe("Batch structured cards", () => {
  it("shows ten issues before progressive expansion", () => {
    const errors = Array.from({ length: 13 }, (_, index) => ({ row_number: index + 1, compound_name: `Compound ${index + 1}`, error_code: "PREDICTION_FAILED" }));
    render(<StructuredCard payload={{ type: "batch_errors", data: { error_count: errors.length, errors } }} />);
    expect(screen.getByText("Row 10")).toBeInTheDocument();
    expect(screen.queryByText("Row 11")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "See 3 more" }));
    expect(screen.getByText("Row 13")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show less" }));
    expect(screen.queryByText("Row 13")).not.toBeInTheDocument();
  });
});

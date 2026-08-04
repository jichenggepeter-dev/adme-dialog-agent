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

  it("renders claim-linked ADME evidence and stale boundaries", () => {
    render(<StructuredCard payload={{ type: "evidence_answer", data: {
      query: "mass balance",
      status: "supported",
      availability: "available",
      assistant_summary: "Current indexed FDA evidence supports the bounded claims below.",
      claims: [{ text: "The guidance covers study design and reporting.", evidence: [{
        source_id: "fda-mass-balance-2024", title: "Human Radiolabeled Mass Balance Studies",
        organization: "U.S. Food and Drug Administration", url: "https://www.fda.gov/example",
        document_date: "2024-09", version: "Final", status: "current", captured_at: "2026-08-03",
        section: "Guidance summary", page: null, chunk_id: "fda-mass-balance-2024:abc",
        excerpt: "The guidance covers study design and reporting.",
      }] }],
      evidence: [], source_count: 1, warnings: [],
    } }} />);
    expect(screen.getByRole("region", { name: "ADME evidence answer" })).toBeInTheDocument();
    expect(screen.getByText("Supported")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Human Radiolabeled Mass Balance Studies" })).toHaveAttribute("href", "https://www.fda.gov/example");
    expect(screen.getByText("fda-mass-balance-2024:abc")).toBeInTheDocument();
    expect(screen.getByText(/not clinical advice/i)).toBeInTheDocument();
  });
});

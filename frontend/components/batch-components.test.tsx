import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BatchUploadPanel } from "./batch-upload-panel";
import { ColumnMappingPanel } from "./column-mapping-panel";
import { ValidationSummary } from "./validation-summary";

describe("batch workflow components", () => {
  it("provides a keyboard-accessible file input and format guidance", async () => {
    const onFile = vi.fn(); render(<BatchUploadPanel capabilities={null} busy={false} error={null} onFile={onFile} />);
    const input = screen.getByLabelText("Choose batch compound file");
    await userEvent.upload(input, new File(["smiles\nCCO"], "sample.csv", { type: "text/csv" }));
    expect(onFile).toHaveBeenCalledOnce(); expect(screen.getByText(/CSV, TSV, or SMI/)).toBeInTheDocument();
  });

  it("maps columns and prevents continuing without SMILES", () => {
    const upload = { upload_id: "u", source_filename: "sample.csv", file_type: "csv" as const, file_size: 20, row_count: 1, columns: ["id", "smiles"], preview: [{ id: "1", smiles: "CCO" }], suggested_mapping: { smiles: "smiles", compound_id: "id", compound_name: null }, created_at: "now" };
    render(<ColumnMappingPanel upload={upload} mapping={{ smiles: "", compound_id: null, compound_name: null }} error={null} busy={false} onChange={vi.fn()} onContinue={vi.fn()} onReplace={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Validate dataset" })).toBeDisabled(); expect(screen.getByText("Uploaded data preview")).toBeInTheDocument();
  });

  it("renders actual validation counts", () => {
    render(<ValidationSummary summary={{ total_rows: 5, valid_molecules: 3, invalid_smiles: 1, missing_smiles: 1, duplicate_molecules: 1, unique_valid_molecules: 2 }} />);
    expect(screen.getByText("Unique valid molecules").nextSibling).toHaveTextContent("2"); expect(screen.getByText("Invalid SMILES").nextSibling).toHaveTextContent("1");
  });
});

import { describe, expect, it } from "vitest";
import { getAssistantPageContext, publishAssistantPageContext } from "./assistant-page-state";

describe("Assistant page context", () => {
  it("does not let an empty Batch snapshot erase the job ID derived from the route", () => {
    const clear = publishAssistantPageContext({ page: "batch", batch_job_id: null, selected_compound_ids: [], selected_row_numbers: [], selected_endpoints: [] });
    expect(getAssistantPageContext({ page: "batch", batch_job_id: "job_route_123", selected_compound_ids: [], selected_row_numbers: [], selected_endpoints: [] })).toMatchObject({ batch_job_id: "job_route_123" });
    clear();
  });

  it("keeps the richer live Batch selection while retaining the route job ID", () => {
    const clear = publishAssistantPageContext({ page: "batch", selected_compound_ids: ["CMP-1", "CMP-2"], selected_row_numbers: [6, 10], selected_endpoints: ["hERG"], batch_job_id: null, active_view: "comparison", comparison_open: true });
    expect(getAssistantPageContext({ page: "batch", batch_job_id: "job_route_456", selected_compound_ids: [], selected_row_numbers: [], selected_endpoints: [] })).toMatchObject({ batch_job_id: "job_route_456", selected_row_numbers: [6, 10], selected_endpoints: ["hERG"], active_view: "comparison", comparison_open: true });
    clear();
  });
});

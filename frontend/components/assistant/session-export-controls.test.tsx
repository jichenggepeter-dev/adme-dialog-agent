import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionExportControls } from "./session-export-controls";
import { decideSessionExport, prepareSessionExport } from "@/lib/agent-api";


vi.mock("@/lib/agent-api", () => ({
  AgentApiError: class AgentApiError extends Error {},
  prepareSessionExport: vi.fn(),
  decideSessionExport: vi.fn(),
}));

const proposal = {
  action: {
    action_id: "action_export",
    session_id: "session_owner",
    action_type: "session_export_v1" as const,
    status: "awaiting_confirmation",
    payload: {},
    expected_state_version: 2,
    created_at: "2026-08-06T12:00:00Z",
    expires_at: "2026-08-06T12:15:00Z",
    consumed_at: null,
  },
  schema_version: "1.0" as const,
  included: ["conversation messages", "confirmation summaries"],
  excluded: ["credential fields", "internal prompts"],
  max_export_bytes: 1_000_000,
  snapshot_taken_at: "2026-08-06T12:00:00Z",
  counts: {
    messages: 2,
    confirmations: 1,
    activities: 3,
    resources: 1,
    selected_resources: 0,
  },
};

describe("SessionExportControls", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    HTMLDialogElement.prototype.showModal = function () {
      this.setAttribute("open", "");
    };
    HTMLDialogElement.prototype.close = function () {
      this.removeAttribute("open");
    };
    vi.mocked(prepareSessionExport).mockResolvedValue(proposal);
  });

  it("shows the exact scope and records cancellation before exporting", async () => {
    vi.mocked(decideSessionExport).mockResolvedValue({
      status: "rejected",
      filename: null,
      media_type: null,
      content: null,
      size_bytes: null,
      schema_version: "1.0",
    });
    render(<SessionExportControls sessionId="session_owner" stateVersion={2} />);

    fireEvent.click(screen.getByRole("button", { name: "Export" }));
    const dialog = await screen.findByRole("dialog", { name: "Confirm session export" });
    expect(dialog).toHaveTextContent("conversation messages");
    expect(dialog).toHaveTextContent("credential fields");
    expect(dialog).toHaveTextContent("Maximum file size: 1.0 MB");
    expect(dialog).toHaveTextContent("current-session-only");
    expect(dialog).toHaveTextContent(/Messages\s*2/);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(decideSessionExport).toHaveBeenCalledWith(
      "session_owner", "action_export", "reject", 2,
    ));
    expect(await screen.findByText("Session export cancelled.")).toBeInTheDocument();
  });

  it("downloads Markdown only after approval", async () => {
    vi.mocked(decideSessionExport).mockResolvedValue({
      status: "succeeded",
      filename: "adme-session-export.md",
      media_type: "text/markdown",
      content: "# Export\n",
      size_bytes: 9,
      schema_version: "1.0",
    });
    const createObjectURL = vi.fn(() => "blob:export");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    render(<SessionExportControls sessionId="session_owner" stateVersion={2} />);

    fireEvent.change(screen.getByRole("combobox", { name: "Session export format" }), {
      target: { value: "markdown" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Export" }));
    fireEvent.click(await screen.findByRole("button", { name: "Download Markdown" }));

    await waitFor(() => expect(decideSessionExport).toHaveBeenCalledWith(
      "session_owner", "action_export", "approve", 2,
    ));
    expect(prepareSessionExport).toHaveBeenCalledWith("session_owner", "markdown", 2);
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:export");
  });

  it("invalidates an open proposal when the active session changes", async () => {
    const { rerender } = render(
      <SessionExportControls sessionId="session_owner" stateVersion={2} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Export" }));
    await screen.findByRole("dialog", { name: "Confirm session export" });

    rerender(<SessionExportControls sessionId="session_new" stateVersion={0} />);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The active session changed. Create a new export proposal.",
    );
    expect(decideSessionExport).not.toHaveBeenCalled();
  });
});

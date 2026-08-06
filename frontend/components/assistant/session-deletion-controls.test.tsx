import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionDeletionControls } from "./session-deletion-controls";
import { decideSessionDeletion, prepareSessionDeletion } from "@/lib/agent-api";


vi.mock("@/lib/agent-api", () => ({
  AgentApiError: class AgentApiError extends Error {},
  prepareSessionDeletion: vi.fn(),
  decideSessionDeletion: vi.fn(),
}));

const proposal = {
  action: {
    action_id: "action_delete",
    session_id: "session_owner",
    action_type: "delete_session_v1" as const,
    status: "awaiting_confirmation" as const,
    payload: {},
    expected_state_version: 2,
    created_at: "2026-08-06T12:00:00Z",
    expires_at: "2026-08-06T12:15:00Z",
    consumed_at: null,
  },
  counts: {
    sessions: 1,
    messages: 2,
    business_state: 1,
    confirmations: 1,
    pending_actions: 2,
    resources: 3,
    audit_events: 4,
  },
  deleted: ["conversation messages", "session-owned Agent resources"],
  retained: ["shared Batch uploads and jobs", "minimal hashed deletion receipt"],
};

describe("SessionDeletionControls", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
    HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
    vi.mocked(prepareSessionDeletion).mockResolvedValue(proposal);
  });

  it("shows exact scope and rejection changes no provider state", async () => {
    vi.mocked(decideSessionDeletion).mockResolvedValue({
      status: "rejected",
      deleted_at: null,
      counts: null,
      retained: proposal.retained,
    });
    const onDelete = vi.fn();
    render(
      <SessionDeletionControls
        sessionId="session_owner"
        stateVersion={2}
        onDelete={onDelete}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete session" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete this Assistant session?" });
    expect(dialog).toHaveTextContent(/Messages\s*2/);
    expect(dialog).toHaveTextContent("shared Batch uploads and jobs");
    expect(dialog).toHaveTextContent("cannot be undone");

    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(decideSessionDeletion).toHaveBeenCalledWith(
      "session_owner", "action_delete", "reject", 2,
    ));
    expect(onDelete).not.toHaveBeenCalled();
  });

  it("uses the provider-owned destructive transition only after approval", async () => {
    const onDelete = vi.fn().mockResolvedValue({
      status: "deleted",
      deleted_at: "2026-08-06T12:01:00Z",
      counts: proposal.counts,
      retained: proposal.retained,
    });
    render(
      <SessionDeletionControls
        sessionId="session_owner"
        stateVersion={2}
        onDelete={onDelete}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete session" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete this Assistant session?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete session" }));

    await waitFor(() => expect(onDelete).toHaveBeenCalledWith("action_delete"));
    expect(await screen.findByText("Old session deleted.")).toBeInTheDocument();
  });

  it("invalidates an open request when the provider changes sessions", async () => {
    const { rerender } = render(
      <SessionDeletionControls
        sessionId="session_owner"
        stateVersion={2}
        onDelete={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete session" }));
    await screen.findByRole("dialog", { name: "Delete this Assistant session?" });
    rerender(
      <SessionDeletionControls
        sessionId="session_new"
        stateVersion={0}
        onDelete={vi.fn()}
      />,
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The active session changed. Create a new deletion request.",
    );
  });

  it("invalidates an open request when the session state version changes", async () => {
    const { rerender } = render(
      <SessionDeletionControls
        sessionId="session_owner"
        stateVersion={2}
        onDelete={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete session" }));
    await screen.findByRole("dialog", { name: "Delete this Assistant session?" });
    rerender(
      <SessionDeletionControls
        sessionId="session_owner"
        stateVersion={3}
        onDelete={vi.fn()}
      />,
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The active session changed. Create a new deletion request.",
    );
  });
});

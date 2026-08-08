import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AgentActivityItem } from "@/lib/agent-types";
import { ActivityTrace } from "./activity-trace";

const items: AgentActivityItem[] = [
  {
    id: "corr:0:tool:search",
    kind: "tool",
    status: "completed",
    occurred_at: "2026-08-06T12:00:00.000Z",
    correlation_id: "corr_public_1",
    sequence: 0,
    tool_name: "search_adme_evidence",
    duration_ms: 18,
  },
  {
    id: "corr:1:evidence:source",
    kind: "evidence",
    status: "supported",
    occurred_at: "2026-08-06T12:00:01.000Z",
    correlation_id: "corr_public_1",
    sequence: 1,
    source_title: "FDA M12 guidance",
    source_url: "https://www.fda.gov/m12",
    chunk_id: "fda-m12:fixture",
  },
  {
    id: "corr:2:error:timeout",
    kind: "error",
    status: "error",
    occurred_at: "2026-08-06T12:00:02.000Z",
    correlation_id: "corr_public_1",
    sequence: 2,
    error_code: "AGENT_TIMEOUT",
    recovery: "edit_and_retry",
  },
];

describe("ActivityTrace", () => {
  it("uses a keyboard-operable disclosure with visible status, timing, evidence, and recovery", async () => {
    const user = userEvent.setup();
    const onReturnToComposer = vi.fn(() => document.getElementById("test-composer")?.focus());
    render(<><ActivityTrace items={items} onReturnToComposer={onReturnToComposer} /><textarea id="test-composer" aria-label="Test message box" /></>);

    const summary = screen.getByText("Activity & evidence trace");
    await user.click(summary);

    expect(screen.getByRole("list", { name: "Agent activity trace" })).toBeVisible();
    expect(screen.getByText("Completed")).toBeVisible();
    expect(screen.getByText("18 ms")).toBeVisible();
    expect(screen.getByText("corr_public_1")).toBeVisible();
    expect(screen.getByRole("link", { name: "Open source: FDA M12 guidance (opens in new tab)" })).toHaveAttribute("href", "https://www.fda.gov/m12");
    expect(screen.getByText("Next: Edit your request and try again.")).toBeVisible();
    expect(document.querySelector("time")).toHaveAttribute("datetime", "2026-08-06T12:00:00.000Z");
    await user.click(screen.getByRole("button", { name: "Return to message box" }));
    expect(onReturnToComposer).toHaveBeenCalledOnce();
    expect(screen.getByRole("textbox", { name: "Test message box" })).toHaveFocus();
  });

  it("does not make an unsafe evidence URL interactive", async () => {
    const user = userEvent.setup();
    render(<ActivityTrace items={[{ ...items[1], source_url: "javascript:alert(1)" }]} />);
    await user.click(screen.getByText("Activity & evidence trace"));
    expect(screen.getByText("FDA M12 guidance")).toBeVisible();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});

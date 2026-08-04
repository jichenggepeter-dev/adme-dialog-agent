import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReviewModeBanner } from "./review-mode-banner";

describe("ReviewModeBanner", () => {
  it("shows the review boundary and source revision", () => {
    render(<ReviewModeBanner enabled revision="abc123" />);

    expect(screen.getByText("PR Preview · Mock Agent v1")).toBeInTheDocument();
    expect(screen.getByText(/temporary synthetic state/i)).toBeInTheDocument();
    expect(screen.getByText("revision abc123")).toBeInTheDocument();
  });

  it("stays absent outside review mode", () => {
    const { container } = render(<ReviewModeBanner enabled={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});

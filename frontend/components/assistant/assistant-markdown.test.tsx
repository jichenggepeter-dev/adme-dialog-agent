import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AssistantMarkdown } from "./assistant-markdown";

describe("AssistantMarkdown", () => {
  it("renders Chinese bold and lists without raw marker text", () => {
    const { container } = render(<AssistantMarkdown>{"下面是 **DILI 模型信息**：\n\n- 元数据部分验证\n- 需要实验确认"}</AssistantMarkdown>);
    expect(screen.getByText("DILI 模型信息").tagName).toBe("STRONG");
    expect(container.textContent).not.toContain("**");
    expect(container.querySelectorAll("li")).toHaveLength(2);
  });
  it("does not render raw HTML", () => {
    const { container } = render(<AssistantMarkdown>{'<img src=x onerror="alert(1)">safe'}</AssistantMarkdown>);
    expect(container.querySelector("img")).toBeNull(); expect(container.textContent).toContain("safe");
  });
  it("renders GFM tables inside a scroll container", () => {
    const { container } = render(<AssistantMarkdown>{"| Endpoint | Result |\n|---|---:|\n| hERG | 0.21 |"}</AssistantMarkdown>);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Endpoint" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "hERG" })).toBeInTheDocument();
    expect(container.querySelector(".assistant-table-scroll")).toBeInTheDocument();
  });
});

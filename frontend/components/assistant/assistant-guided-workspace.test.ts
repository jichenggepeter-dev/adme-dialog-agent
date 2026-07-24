import { describe, expect, it } from "vitest";
import { isExplicitConfirmation } from "./assistant-guided-workspace";

describe("isExplicitConfirmation", () => {
  it.each(["确认", "确认。", "确认结构", "confirm", "yes"])("accepts the explicit affirmation %s", (value) => {
    expect(isExplicitConfirmation(value, "Ibuprofen, (+-)-")).toBe(true);
  });

  it.each(["确认 Ibuprofen", "确认ibuprofen", "confirm ibuprofen"])("accepts a matching compound name in %s", (value) => {
    expect(isExplicitConfirmation(value, "Ibuprofen, (+-)-")).toBe(true);
  });

  it.each(["我还没确认", "确认一下这是什么", "不要确认", "确认 Aspirin"])("rejects ambiguous or mismatched text %s", (value) => {
    expect(isExplicitConfirmation(value, "Ibuprofen, (+-)-")).toBe(false);
  });
});

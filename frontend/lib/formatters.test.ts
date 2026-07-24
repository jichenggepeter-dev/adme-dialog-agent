import { describe, expect, it } from "vitest";
import { formatPropertyName, formatValue, messageForError } from "./formatters";

describe("property formatting", () => {
  it("formats numeric and empty values", () => {
    expect(formatValue(0.123456)).toBe("0.12346");
    expect(formatValue(null)).toBe("Not available");
    expect(formatValue(true)).toBe("True");
  });

  it("makes raw endpoint keys readable", () => {
    expect(formatPropertyName("CYP2D6_Substrate")).toBe("CYP2D6 Substrate");
  });

  it("maps stable backend error codes", () => {
    expect(messageForError({ code: "MODEL_LOAD_FAILED", message: "raw" })).toContain("could not be initialized");
    expect(messageForError({ code: "UNKNOWN", message: "Fallback message" })).toBe("Fallback message");
  });
});

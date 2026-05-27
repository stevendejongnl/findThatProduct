import { describe, it, expect } from "vitest";
import { renderAlternativesList } from "./AlternativesList";
import { AlternativeResult } from "../domain/AlternativeResult";

function makeAlt(overrides: Partial<AlternativeResult> = {}): AlternativeResult {
  return {
    title: "Sony WF-1000XM5",
    reason: "Great ANC",
    price: 149.0,
    currency: "EUR",
    url: "https://bol.com/sony",
    source: "openai",
    ...overrides,
  };
}

describe("renderAlternativesList", () => {
  it("returns null when alternatives is empty", () => {
    expect(renderAlternativesList([])).toBeNull();
  });

  it("renders section with heading", () => {
    const el = renderAlternativesList([makeAlt()]);
    expect(el).not.toBeNull();
    expect(el?.querySelector(".alternatives-list__heading")?.textContent).toContain("Alternative");
  });

  it("renders one card per alternative", () => {
    const el = renderAlternativesList([makeAlt(), makeAlt({ title: "Bose QC45" })]);
    expect(el?.querySelectorAll(".alternative-card").length).toBe(2);
  });
});

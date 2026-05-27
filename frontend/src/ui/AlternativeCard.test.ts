import { describe, it, expect } from "vitest";
import { renderAlternativeCard } from "./AlternativeCard";
import { AlternativeResult } from "../domain/AlternativeResult";

function makeAlt(overrides: Partial<AlternativeResult> = {}): AlternativeResult {
  return {
    title: "Sony WF-1000XM5",
    reason: "Similar ANC at lower price",
    price: 149.0,
    currency: "EUR",
    url: "https://bol.com/sony",
    source: "openai",
    ...overrides,
  };
}

describe("renderAlternativeCard", () => {
  it("renders title", () => {
    const el = renderAlternativeCard(makeAlt());
    expect(el.querySelector(".alternative-card__title")?.textContent).toBe("Sony WF-1000XM5");
  });

  it("renders reason", () => {
    const el = renderAlternativeCard(makeAlt());
    expect(el.querySelector(".alternative-card__reason")?.textContent).toContain("Similar ANC");
  });

  it("renders price formatted", () => {
    const el = renderAlternativeCard(makeAlt({ price: 149.0, currency: "EUR" }));
    expect(el.querySelector(".alternative-card__price")?.textContent).toContain("149.00");
  });

  it("renders 'price unknown' when price is null", () => {
    const el = renderAlternativeCard(makeAlt({ price: null }));
    expect(el.querySelector(".alternative-card__price")?.textContent?.toLowerCase()).toContain("unknown");
  });

  it("renders link to url", () => {
    const el = renderAlternativeCard(makeAlt());
    const link = el.querySelector("a");
    expect(link?.getAttribute("href")).toBe("https://bol.com/sony");
  });
});

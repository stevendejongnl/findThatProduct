import { describe, it, expect } from "vitest";
import { renderResultsList } from "./ResultsList";
import { ProductResult } from "../domain/ProductResult";
import { AlternativeResult } from "../domain/AlternativeResult";

function makeResult(title: string, price: number | null, ean?: string): ProductResult {
  return { title, price, currency: "EUR", url: "https://example.com", source: "test", image_url: null, ean: ean ?? null };
}

const noOp = () => {};
const emptySet = new Set<string>();

describe("renderResultsList", () => {
  it("renders a card per grouped product", () => {
    // Two results with different EANs → two cards
    const el = renderResultsList(
      [makeResult("A", 4.99, "111"), makeResult("B", 6.00, "222")],
      [], [], "test", emptySet, noOp,
    );
    expect(el.querySelectorAll(".result-card").length).toBe(2);
  });

  it("groups results with same EAN into one card", () => {
    const el = renderResultsList(
      [makeResult("Product A", 4.99, "111"), makeResult("Product A", 5.50, "111")],
      [], [], "test", emptySet, noOp,
    );
    expect(el.querySelectorAll(".result-card").length).toBe(1);
  });

  it("renders empty state when no results", () => {
    const el = renderResultsList([], [], [], "nothing", emptySet, noOp);
    expect(el.querySelector(".results-empty")).not.toBeNull();
  });

  it("renders warnings banner when warnings present", () => {
    const el = renderResultsList(
      [makeResult("A", 4.99, "111")],
      [], ["Budget exceeded"], "test", emptySet, noOp,
    );
    expect(el.querySelector(".results-warning")).not.toBeNull();
    expect(el.querySelector(".results-warning")?.textContent).toContain("Budget exceeded");
  });

  it("does not render warnings when none", () => {
    const el = renderResultsList(
      [makeResult("A", 4.99, "111")],
      [], [], "test", emptySet, noOp,
    );
    expect(el.querySelector(".results-warning")).toBeNull();
  });

  it("sorts cards by best price ascending", () => {
    const el = renderResultsList(
      [makeResult("Expensive", 9.99, "222"), makeResult("Cheap", 2.99, "111")],
      [], [], "test", emptySet, noOp,
    );
    const titles = [...el.querySelectorAll(".result-card__title")].map((t) => t.textContent);
    expect(titles[0]).toBe("Cheap");
    expect(titles[1]).toBe("Expensive");
  });
});

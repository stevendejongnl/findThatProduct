import { describe, it, expect } from "vitest";
import { renderResultsList } from "./ResultsList";
import { ProductResult } from "../domain/ProductResult";

function makeResult(title: string, price: number | null): ProductResult {
  return { title, price, currency: "EUR", url: "https://example.com", source: "test", image_url: null, ean: null };
}

describe("renderResultsList", () => {
  it("renders a card per result", () => {
    const el = renderResultsList([makeResult("A", 4.99), makeResult("B", 6.00)]);
    expect(el.querySelectorAll(".result-card").length).toBe(2);
  });

  it("renders empty state when no results", () => {
    const el = renderResultsList([]);
    expect(el.querySelector(".results-list__empty")).not.toBeNull();
  });

  it("renders results in given order", () => {
    const el = renderResultsList([makeResult("First", 2.99), makeResult("Second", 9.99)]);
    const titles = [...el.querySelectorAll(".result-card__title")].map((t) => t.textContent);
    expect(titles).toEqual(["First", "Second"]);
  });
});

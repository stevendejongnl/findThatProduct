import { describe, it, expect } from "vitest";
import { renderResultCard } from "./ResultCard";
import { ProductResult } from "../domain/ProductResult";

function makeResult(overrides: Partial<ProductResult> = {}): ProductResult {
  return {
    title: "Peanut Butter",
    price: 4.99,
    currency: "EUR",
    url: "https://example.com/product",
    source: "open_food_facts",
    image_url: null,
    ean: "8710447308431",
    ...overrides,
  };
}

describe("renderResultCard", () => {
  it("renders title", () => {
    const el = renderResultCard(makeResult());
    expect(el.querySelector(".result-card__title")?.textContent).toBe("Peanut Butter");
  });

  it("renders price formatted", () => {
    const el = renderResultCard(makeResult({ price: 4.99, currency: "EUR" }));
    expect(el.querySelector(".result-card__price")?.textContent).toContain("4.99");
  });

  it("renders 'price unknown' when price is null", () => {
    const el = renderResultCard(makeResult({ price: null }));
    expect(el.querySelector(".result-card__price")?.textContent?.toLowerCase()).toContain("unknown");
  });

  it("renders source", () => {
    const el = renderResultCard(makeResult());
    expect(el.querySelector(".result-card__source")?.textContent).toContain("open_food_facts");
  });

  it("renders link to product url", () => {
    const el = renderResultCard(makeResult());
    const link = el.querySelector("a");
    expect(link?.getAttribute("href")).toBe("https://example.com/product");
  });

  it("renders image when image_url present", () => {
    const el = renderResultCard(makeResult({ image_url: "https://example.com/img.jpg" }));
    const img = el.querySelector("img");
    expect(img?.getAttribute("src")).toBe("https://example.com/img.jpg");
  });

  it("renders no image when image_url is null", () => {
    const el = renderResultCard(makeResult({ image_url: null }));
    expect(el.querySelector("img")).toBeNull();
  });
});

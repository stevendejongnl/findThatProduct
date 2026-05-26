import { describe, it, expect } from "vitest";
import { isProductResult } from "./ProductResult";

describe("isProductResult", () => {
  it("returns true for valid result", () => {
    expect(
      isProductResult({
        title: "Test",
        price: 4.99,
        currency: "EUR",
        url: "https://example.com",
        source: "test",
        image_url: null,
        ean: null,
      })
    ).toBe(true);
  });

  it("returns false when title missing", () => {
    expect(isProductResult({ price: 4.99, url: "https://example.com", source: "test" })).toBe(false);
  });

  it("returns false for non-object", () => {
    expect(isProductResult(null)).toBe(false);
    expect(isProductResult("string")).toBe(false);
  });
});

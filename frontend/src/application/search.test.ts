import { describe, it, expect, vi, beforeEach } from "vitest";
import { searchProducts } from "./search";
import * as apiClient from "../infrastructure/apiClient";

describe("searchProducts", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("calls POST /api/search and returns results", async () => {
    const mockResults = [
      { title: "Product", price: 4.99, currency: "EUR", url: "https://example.com", source: "test", image_url: null, ean: null },
    ];
    vi.spyOn(apiClient, "post").mockResolvedValue({ query: "test", query_type: "text", results: mockResults });

    const results = await searchProducts("peanut butter");
    expect(results).toEqual(mockResults);
    expect(apiClient.post).toHaveBeenCalledWith("/api/search", { query: "peanut butter" });
  });

  it("throws on short query", async () => {
    await expect(searchProducts("a")).rejects.toThrow("Query too short");
  });

  it("returns empty array on API error", async () => {
    vi.spyOn(apiClient, "post").mockRejectedValue(new Error("422"));
    const results = await searchProducts("peanut butter");
    expect(results).toEqual([]);
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { searchProducts } from "./search";
import * as apiClient from "../infrastructure/apiClient";

describe("searchProducts", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("calls POST /api/search and returns SearchResponse", async () => {
    const mockResponse = {
      query: "peanut butter",
      query_type: "text",
      results: [{ title: "Product", price: 4.99, currency: "EUR", url: "https://example.com", source: "test", image_url: null, ean: null }],
      alternatives: [],
      enriched: false,
      warnings: [],
    };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const response = await searchProducts("peanut butter");
    expect(response).toEqual(mockResponse);
    expect(apiClient.post).toHaveBeenCalledWith("/api/search", { query: "peanut butter" });
  });

  it("throws on short query", async () => {
    await expect(searchProducts("a")).rejects.toThrow("Query too short");
  });

  it("throws on API error", async () => {
    vi.spyOn(apiClient, "post").mockRejectedValue(new Error("422"));
    await expect(searchProducts("peanut butter")).rejects.toThrow("422");
  });
});

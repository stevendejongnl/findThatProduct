import { describe, it, expect, vi, beforeEach } from "vitest";
import { post } from "./apiClient";

describe("post", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sends POST with JSON body and returns parsed response", async () => {
    const mockResponse = { results: [] };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })
    );
    const result = await post("/api/search", { query: "test" });
    expect(result).toEqual(mockResponse);
    expect(fetch).toHaveBeenCalledWith("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "test" }),
    });
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: () => Promise.resolve({ detail: "Query too short" }),
      })
    );
    await expect(post("/api/search", { query: "a" })).rejects.toThrow("422");
  });

  it("throws on network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));
    await expect(post("/api/search", {})).rejects.toThrow("Network error");
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { searchProducts } from "./search";

const mockResponse = {
  query: "peanut butter",
  query_type: "text",
  results: [{ title: "Product", price: 4.99, currency: "EUR", url: "https://example.com", source: "test", image_url: null, ean: null }],
  alternatives: [],
  enriched: false,
  warnings: [],
};

function makeSseStream(events: Array<{ event: string; data: unknown }>): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const chunks = events.map(
    ({ event, data }) => encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
  );
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < chunks.length) controller.enqueue(chunks[i++]);
      else controller.close();
    },
  });
}

describe("searchProducts", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns SearchResponse on result event", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      body: makeSseStream([{ event: "result", data: mockResponse }]),
    }));

    const response = await searchProducts("peanut butter");
    expect(response).toEqual(mockResponse);
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/search/stream?q=peanut%20butter"));
  });

  it("calls onQueuePosition for queued events", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      body: makeSseStream([
        { event: "queued", data: { position: 2 } },
        { event: "result", data: mockResponse },
      ]),
    }));

    const onQueuePosition = vi.fn();
    await searchProducts("peanut butter", onQueuePosition);
    expect(onQueuePosition).toHaveBeenCalledWith(2);
  });

  it("throws on short query", async () => {
    await expect(searchProducts("a")).rejects.toThrow("Query too short");
  });

  it("throws on HTTP error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422, body: null }));
    await expect(searchProducts("peanut butter")).rejects.toThrow("Search failed (422)");
  });

  it("throws when stream ends without result", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      body: makeSseStream([]),
    }));
    await expect(searchProducts("peanut butter")).rejects.toThrow("Search stream ended without a result");
  });
});

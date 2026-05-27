import { ProductResult } from "../domain/ProductResult";
import { AlternativeResult } from "../domain/AlternativeResult";
import { createSearchQuery } from "../domain/SearchQuery";

export interface SearchResponse {
  query: string;
  query_type: string;
  results: ProductResult[];
  alternatives: AlternativeResult[];
  enriched: boolean;
  warnings: string[];
}

export async function searchProducts(
  raw: string,
  onQueuePosition?: (position: number) => void,
): Promise<SearchResponse> {
  const query = createSearchQuery(raw);
  const url = `/api/search/stream?q=${encodeURIComponent(query.raw)}`;
  const response = await fetch(url);
  if (!response.ok || !response.body) {
    throw new Error(`Search failed (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const lines = block.split("\n");
      let event = "";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data = line.slice(5).trim();
      }
      if (event === "queued" && onQueuePosition) {
        const parsed = JSON.parse(data) as { position: number };
        onQueuePosition(parsed.position);
      } else if (event === "result") {
        return JSON.parse(data) as SearchResponse;
      }
    }
  }

  throw new Error("Search stream ended without a result");
}

import { post } from "../infrastructure/apiClient";
import { ProductResult } from "../domain/ProductResult";
import { createSearchQuery } from "../domain/SearchQuery";

interface SearchResponse {
  query: string;
  query_type: string;
  results: ProductResult[];
}

export async function searchProducts(raw: string): Promise<ProductResult[]> {
  const query = createSearchQuery(raw);
  try {
    const response = await post<SearchResponse>("/api/search", { query: query.raw });
    return response.results;
  } catch (e) {
    if (e instanceof Error && e.message === "Query too short") throw e;
    console.error("Search failed:", e);
    return [];
  }
}

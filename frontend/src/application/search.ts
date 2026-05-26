import { post } from "../infrastructure/apiClient";
import { ProductResult } from "../domain/ProductResult";
import { createSearchQuery } from "../domain/SearchQuery";

export interface SearchResponse {
  query: string;
  query_type: string;
  results: ProductResult[];
}

export async function searchProducts(raw: string): Promise<SearchResponse> {
  const query = createSearchQuery(raw);
  const response = await post<SearchResponse>("/api/search", { query: query.raw });
  return response;
}

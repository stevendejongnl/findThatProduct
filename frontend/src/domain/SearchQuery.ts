export enum QueryType {
  EAN = "ean",
  TEXT = "text",
}

export interface SearchQuery {
  raw: string;
  type: QueryType;
}

export function createSearchQuery(raw: string): SearchQuery {
  const trimmed = raw.trim();
  if (trimmed.length < 2) throw new Error("Query too short");
  if (/^\d{8}$|^\d{13}$/.test(trimmed)) return { raw: trimmed, type: QueryType.EAN };
  return { raw: trimmed, type: QueryType.TEXT };
}

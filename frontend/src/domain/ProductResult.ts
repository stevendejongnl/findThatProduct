export interface ProductResult {
  title: string;
  price: number | null;
  currency: string;
  url: string;
  source: string;
  image_url: string | null;
  ean: string | null;
}

export function isProductResult(value: unknown): value is ProductResult {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v.title === "string" && typeof v.url === "string" && typeof v.source === "string";
}

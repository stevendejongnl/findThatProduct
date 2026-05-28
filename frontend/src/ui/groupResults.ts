import { ProductResult } from "../domain/ProductResult";

export interface ProductGroup {
  key: string;
  title: string;
  ean: string | null;
  image_url: string | null;
  bestPrice: number | null;
  avgPrice: number | null;
  currency: string;
  listings: ProductResult[];
}

export function groupResults(results: ProductResult[]): ProductGroup[] {
  const groups = new Map<string, ProductResult[]>();
  for (const r of results) {
    const key = r.ean?.trim() || r.title.toLowerCase().trim().slice(0, 60);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(r);
  }

  return [...groups.entries()]
    .map(([key, listings]) => {
      const withPrice = listings.filter((l) => l.price !== null);
      const prices = withPrice.map((l) => l.price as number);
      const bestPrice = prices.length ? Math.min(...prices) : null;
      const avgPrice = prices.length
        ? prices.reduce((a, b) => a + b, 0) / prices.length
        : null;
      return {
        key,
        title: listings[0].title,
        ean: listings.find((l) => l.ean)?.ean ?? null,
        image_url: listings.find((l) => l.image_url)?.image_url ?? null,
        bestPrice,
        avgPrice,
        currency: listings[0].currency,
        listings: [...listings].sort((a, b) => {
          if (a.price === null) return 1;
          if (b.price === null) return -1;
          return a.price - b.price;
        }),
      };
    })
    .sort((a, b) => {
      if (a.bestPrice === null) return 1;
      if (b.bestPrice === null) return -1;
      return a.bestPrice - b.bestPrice;
    });
}

import { ProductResult } from "../domain/ProductResult";
import { AlternativeResult } from "../domain/AlternativeResult";
import { renderResultCard } from "./ResultCard";
import { renderAlternativesList } from "./AlternativesList";

export function renderResultsList(
  results: ProductResult[],
  alternatives: AlternativeResult[] = [],
  warnings: string[] = [],
  query = ""
): HTMLElement {
  const container = document.createElement("section");
  container.className = "results-list";

  if (results.length === 0) {
    const empty = document.createElement("div");
    empty.className = "results-list__empty";
    empty.innerHTML = `<span class="results-list__empty-icon">🔍</span><p>No results found</p><p class="results-list__empty-sub">Try a different product name or EAN code</p>`;
    container.appendChild(empty);
    return container;
  }

  const header = document.createElement("div");
  header.className = "results-list__header";
  header.textContent = `${results.length} result${results.length !== 1 ? "s" : ""} found`;

  if (warnings.length > 0) {
    const banner = document.createElement("div");
    banner.className = "results-list__warnings";
    banner.textContent = warnings.join("; ");
    container.appendChild(banner);
  }

  container.appendChild(header);

  const bestPriceIndex = results.reduce((best, r, i) => {
    if (r.price === null) return best;
    if (best === -1) return i;
    const bestPrice = results[best].price;
    return bestPrice === null || r.price < bestPrice ? i : best;
  }, -1);

  for (let i = 0; i < results.length; i++) {
    container.appendChild(renderResultCard(results[i], i === bestPriceIndex, query));
  }

  const altSection = renderAlternativesList(alternatives);
  if (altSection) container.appendChild(altSection);

  return container;
}

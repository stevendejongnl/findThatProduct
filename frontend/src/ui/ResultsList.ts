import { ProductResult } from "../domain/ProductResult";
import { renderResultCard } from "./ResultCard";

export function renderResultsList(results: ProductResult[]): HTMLElement {
  const container = document.createElement("section");
  container.className = "results-list";

  if (results.length === 0) {
    const empty = document.createElement("p");
    empty.className = "results-list__empty";
    empty.textContent = "No results found.";
    container.appendChild(empty);
    return container;
  }

  for (const result of results) {
    container.appendChild(renderResultCard(result));
  }
  return container;
}

import { ProductResult } from "../domain/ProductResult";
import { AlternativeResult } from "../domain/AlternativeResult";
import { groupResults, ProductGroup } from "./groupResults";
import { renderResultCard } from "./ResultCard";

export function renderResultsList(
  results: ProductResult[],
  alternatives: AlternativeResult[],
  warnings: string[],
  query: string,
  monitoredIds: Set<string>,
  onMonitor: (group: ProductGroup, schedule: string) => void,
): HTMLElement {
  const container = document.createElement("section");
  container.className = "results-section";

  const groups = groupResults(results);

  // Toolbar
  const toolbar = document.createElement("div");
  toolbar.className = "results-toolbar";
  const toolbarInner = document.createElement("div");
  toolbarInner.className = "container results-toolbar__inner";
  toolbarInner.innerHTML = `
    <span class="results-toolbar__count">
      <span class="results-toolbar__num">${groups.length}</span> product${groups.length !== 1 ? "s" : ""}
      · <span class="results-toolbar__num">${results.length}</span> listing${results.length !== 1 ? "s" : ""}
    </span>
  `;
  toolbar.appendChild(toolbarInner);
  container.appendChild(toolbar);

  if (warnings.length > 0) {
    const banner = document.createElement("div");
    banner.className = "results-warning container";
    banner.textContent = warnings.join("; ");
    container.appendChild(banner);
  }

  const list = document.createElement("div");
  list.className = "results-list container";

  if (groups.length === 0) {
    const empty = document.createElement("div");
    empty.className = "results-empty";
    empty.innerHTML = `<p>No results for <strong>${query}</strong></p><p class="results-empty__sub">Try a different name or EAN code</p>`;
    list.appendChild(empty);
  } else {
    groups.forEach((group, i) => {
      list.appendChild(renderResultCard(group, i, monitoredIds, onMonitor, query));
    });
  }

  container.appendChild(list);
  return container;
}

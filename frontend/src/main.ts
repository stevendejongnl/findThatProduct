import { renderSearchBar } from "./ui/SearchBar";
import { renderResultsList } from "./ui/ResultsList";
import { searchProducts } from "./application/search";
import { ProductResult } from "./domain/ProductResult";

function mount(root: HTMLElement): void {
  const header = document.createElement("header");
  header.className = "app-header";
  const h1 = document.createElement("h1");
  h1.textContent = "findThatProduct";
  header.appendChild(h1);
  root.appendChild(header);

  const main = document.createElement("main");
  main.className = "app-main";

  let resultsContainer: HTMLElement | null = null;
  let statusEl: HTMLElement | null = null;

  function setStatus(msg: string): void {
    if (!statusEl) {
      statusEl = document.createElement("p");
      statusEl.className = "app-status";
      main.insertBefore(statusEl, resultsContainer);
    }
    statusEl.textContent = msg;
  }

  function clearStatus(): void {
    if (statusEl) {
      statusEl.remove();
      statusEl = null;
    }
  }

  async function handleSearch(query: string): Promise<void> {
    clearStatus();
    setStatus("Searching…");
    let results: ProductResult[] = [];
    try {
      results = await searchProducts(query);
    } catch (e) {
      clearStatus();
      setStatus(e instanceof Error ? e.message : "Search failed.");
      return;
    }
    clearStatus();
    if (resultsContainer) resultsContainer.remove();
    resultsContainer = renderResultsList(results);
    main.appendChild(resultsContainer);
  }

  const searchBar = renderSearchBar(handleSearch);
  main.appendChild(searchBar);
  root.appendChild(main);
}

const root = document.getElementById("app");
if (root) mount(root);

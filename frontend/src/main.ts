import { renderSearchBar } from "./ui/SearchBar";
import { renderResultsList } from "./ui/ResultsList";
import { renderProductHero } from "./ui/ProductHero";
import { searchProducts } from "./application/search";

function mount(root: HTMLElement): void {
  const header = document.createElement("header");
  header.className = "app-header";
  const icon = document.createElement("span");
  icon.className = "app-header__icon";
  icon.textContent = "🔍";
  const wordmark = document.createElement("div");
  wordmark.className = "app-header__wordmark";
  const h1 = document.createElement("h1");
  h1.textContent = "findThatProduct";
  const sub = document.createElement("span");
  sub.className = "app-header__sub";
  sub.textContent = "Price comparison";
  wordmark.appendChild(h1);
  wordmark.appendChild(sub);
  header.appendChild(icon);
  header.appendChild(wordmark);
  root.appendChild(header);

  const hero = document.createElement("div");
  hero.className = "app-hero";
  const heroTitle = document.createElement("p");
  heroTitle.className = "app-hero__title";
  heroTitle.textContent = "Find the best price instantly";
  const heroSub = document.createElement("p");
  heroSub.className = "app-hero__sub";
  heroSub.textContent = "Search by product name or EAN barcode";
  hero.appendChild(heroTitle);
  hero.appendChild(heroSub);
  root.appendChild(hero);

  const main = document.createElement("main");
  main.className = "app-main";

  let productHeroEl: HTMLElement | null = null;
  let resultsContainer: HTMLElement | null = null;
  let statusEl: HTMLElement | null = null;

  function setStatus(msg: string): void {
    if (!statusEl) {
      statusEl = document.createElement("p");
      statusEl.className = "app-status";
      main.insertBefore(statusEl, productHeroEl ?? resultsContainer);
    }
    statusEl.textContent = msg;
  }

  function clearStatus(): void {
    if (statusEl) { statusEl.remove(); statusEl = null; }
  }

  async function handleSearch(query: string): Promise<void> {
    clearStatus();
    if (productHeroEl) { productHeroEl.remove(); productHeroEl = null; }
    if (resultsContainer) { resultsContainer.remove(); resultsContainer = null; }
    setStatus("Searching…");

    let response;
    try {
      response = await searchProducts(query, (position) => {
        setStatus(`Searching… (queue position: ${position})`);
      });
    } catch (e) {
      clearStatus();
      setStatus(e instanceof Error ? e.message : "Search failed.");
      return;
    }

    clearStatus();

    productHeroEl = renderProductHero(response.query, response.query_type, response.results);
    main.appendChild(productHeroEl);

    resultsContainer = renderResultsList(response.results, response.alternatives ?? [], response.warnings ?? [], response.query);
    main.appendChild(resultsContainer);
  }

  const searchBar = renderSearchBar(handleSearch);
  main.appendChild(searchBar);
  root.appendChild(main);

  const initialQuery = new URLSearchParams(window.location.search).get("q");
  if (initialQuery) handleSearch(initialQuery);
}

const root = document.getElementById("app");
if (root) mount(root);

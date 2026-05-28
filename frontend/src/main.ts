import { renderHeader, Page } from "./ui/Header";
import { renderFooter } from "./ui/Footer";
import { renderResultsList } from "./ui/ResultsList";
import { renderMonitoredPage } from "./ui/MonitoredPage";
import { searchProducts } from "./application/search";
import { makeMonitoredProduct } from "./ui/ResultCard";
import { ProductGroup } from "./ui/groupResults";
import { addMonitored, removeMonitored, loadMonitored, isMonitored } from "./infrastructure/monitoredStore";
import { MonitoredProduct } from "./domain/MonitoredProduct";
import { showToast } from "./ui/Toast";

type Theme = "light" | "dark";

function getTheme(): Theme {
  const stored = localStorage.getItem("ftp-theme") as Theme | null;
  if (stored) return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("ftp-theme", theme);
}

function getPage(): Page {
  const h = window.location.hash.replace("#", "");
  return h === "monitored" ? "monitored" : "search";
}

function mount(root: HTMLElement): void {
  let theme = getTheme();
  let page: Page = getPage();
  let query = new URLSearchParams(window.location.search).get("q") ?? "";
  let monitored: MonitoredProduct[] = loadMonitored();
  let monitoredIds = new Set(monitored.map((m) => m.id));

  let headerEl: HTMLElement | null = null;
  let mainEl: HTMLElement | null = null;
  let footerEl: HTMLElement | null = null;

  applyTheme(theme);

  function buildHeader(): HTMLElement {
    return renderHeader({
      page, monitoredCount: monitored.length, theme, query,
      onNavigate: (pg) => { page = pg; window.location.hash = pg; renderPage(); },
      onThemeToggle: () => { theme = theme === "dark" ? "light" : "dark"; applyTheme(theme); renderPage(); },
      onSearch: (q) => { query = q; page = "search"; renderPage(); handleSearch(q); },
    });
  }

  function renderPage(): void {
    if (headerEl) headerEl.remove();
    headerEl = buildHeader();
    root.insertBefore(headerEl, root.firstChild);

    if (!footerEl) {
      footerEl = renderFooter();
      root.appendChild(footerEl);
    }

    if (mainEl) mainEl.remove();

    if (page === "monitored") {
      mainEl = renderMonitoredPage(monitored, (id) => {
        monitored = removeMonitored(id);
        monitoredIds = new Set(monitored.map((m) => m.id));
        showToast("removed from monitoring");
        renderPage();
      });
    } else {
      mainEl = document.createElement("main");
      mainEl.className = "app-main";
      if (!query) mainEl.appendChild(renderHero());
    }

    root.insertBefore(mainEl, footerEl);
  }

  function handleSearch(q: string): void {
    if (!mainEl) return;
    mainEl.innerHTML = "";
    const status = document.createElement("p");
    status.className = "app-status container";
    status.textContent = "Searching…";
    mainEl.appendChild(status);

    searchProducts(q, (position) => {
      status.textContent = `Searching… (queue position: ${position})`;
    })
      .then((response) => {
        if (!mainEl) return;
        mainEl.innerHTML = "";
        mainEl.appendChild(renderResultsList(
          response.results,
          response.alternatives ?? [],
          response.warnings ?? [],
          q,
          monitoredIds,
          (group: ProductGroup) => {
            const key = group.ean ?? group.key;
            if (isMonitored(key)) {
              showToast(`already tracking · ${group.title}`);
              return;
            }
            const product = makeMonitoredProduct(group);
            monitored = addMonitored(product);
            monitoredIds = new Set(monitored.map((m) => m.id));
            showToast(`exported to monitoring · ${group.title}`);
            if (headerEl) {
              headerEl.remove();
              headerEl = buildHeader();
              root.insertBefore(headerEl, mainEl);
            }
          },
        ));
      })
      .catch((err: Error) => {
        if (!mainEl) return;
        mainEl.innerHTML = "";
        const errEl = document.createElement("p");
        errEl.className = "app-status app-status--error container";
        errEl.textContent = err.message;
        mainEl.appendChild(errEl);
      });
  }

  // Keyboard nav: g s / g m
  let gPressed = false;
  window.addEventListener("keydown", (e) => {
    if ((e.target as HTMLElement).tagName === "INPUT") return;
    if (e.key === "g") { gPressed = true; setTimeout(() => { gPressed = false; }, 800); return; }
    if (gPressed && e.key === "s") { page = "search"; window.location.hash = "search"; renderPage(); gPressed = false; }
    if (gPressed && e.key === "m") { page = "monitored"; window.location.hash = "monitored"; renderPage(); gPressed = false; }
  });

  window.addEventListener("hashchange", () => {
    const newPage = getPage();
    if (newPage !== page) { page = newPage; renderPage(); }
  });

  renderPage();
  if (query) handleSearch(query);
}

function renderHero(): HTMLElement {
  const hero = document.createElement("div");
  hero.className = "app-hero container";
  hero.innerHTML = `
    <p class="app-hero__title">Find the best price instantly</p>
    <p class="app-hero__sub">Search by product name, brand, or EAN barcode — then monitor for price drops.</p>
  `;
  return hero;
}

const root = document.getElementById("app");
if (root) mount(root);

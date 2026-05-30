import { renderHeader, Page } from "./ui/Header";
import { renderFooter } from "./ui/Footer";
import { renderResultsList } from "./ui/ResultsList";
import { renderMonitoredPage } from "./ui/MonitoredPage";
import { searchProducts } from "./application/search";
import { ProductGroup } from "./ui/groupResults";
import { fetchConfig, fetchMonitored, createMonitor, deleteMonitor, MonitoredItem } from "./infrastructure/monitoredApi";
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

function toSlug(q: string): string {
  return q.trim().toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-]/g, "");
}

function fromSlug(slug: string): string {
  return slug.replace(/-/g, " ").trim();
}

function getPage(): Page {
  return window.location.pathname === "/monitored" ? "monitored" : "search";
}

function pushUrl(page: Page, query = ""): void {
  if (page === "monitored") {
    history.pushState({}, "", "/monitored");
  } else if (query) {
    history.pushState({}, "", `/?q=${toSlug(query)}`);
  } else {
    history.pushState({}, "", "/");
  }
}

function mount(root: HTMLElement): void {
  let theme = getTheme();
  let page: Page = getPage();
  const rawQ = new URLSearchParams(window.location.search).get("q") ?? "";
  let query = rawQ ? fromSlug(rawQ) : "";
  let monitored: MonitoredItem[] = [];
  let monitoredIds = new Set<string>();
  let monitoringEnabled = false;

  let headerEl: HTMLElement | null = null;
  let mainEl: HTMLElement | null = null;
  let footerEl: HTMLElement | null = null;

  applyTheme(theme);

  function buildHeader(): HTMLElement {
    return renderHeader({
      page, monitoredCount: monitored.length, theme, query,
      monitoringEnabled,
      onNavigate: (pg) => { page = pg; pushUrl(pg, pg === "search" ? query : ""); renderPage(); },
      onThemeToggle: () => { theme = theme === "dark" ? "light" : "dark"; applyTheme(theme); renderPage(); },
      onSearch: (q) => { query = q; page = "search"; pushUrl("search", q); renderPage(); handleSearch(q); },
    });
  }

  function buildRemoveCallback(): (id: string) => void {
    return async (id: string) => {
      await deleteMonitor(id);
      monitored = monitored.filter((m) => m.id !== id);
      monitoredIds = new Set(monitored.map((m) => m.id));
      showToast("removed from monitoring");
      renderPage();
    };
  }

  function renderPage(): void {
    if (page === "monitored" && !monitoringEnabled) {
      page = "search";
    }

    if (headerEl) headerEl.remove();
    headerEl = buildHeader();
    root.insertBefore(headerEl, root.firstChild);

    if (!footerEl) {
      footerEl = renderFooter();
      root.appendChild(footerEl);
    }

    if (mainEl) mainEl.remove();

    if (page === "monitored") {
      mainEl = renderMonitoredPage(monitored, buildRemoveCallback());
      // Refresh from API
      fetchMonitored().then((items) => {
        monitored = items;
        monitoredIds = new Set(items.map((m) => m.id));
        if (page === "monitored" && mainEl) {
          mainEl.remove();
          mainEl = renderMonitoredPage(monitored, buildRemoveCallback());
          root.insertBefore(mainEl, footerEl);
        }
      });
    } else {
      mainEl = document.createElement("main");
      mainEl.className = "app-main";
      if (!query) mainEl.appendChild(renderHero());
    }

    root.insertBefore(mainEl, footerEl);
  }

  function handleSearch(q: string, updateUrl = false): void {
    if (updateUrl) pushUrl("search", q);
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
          (group: ProductGroup, schedule: string) => {
            const key = group.ean ?? group.key;
            if (monitoredIds.has(key)) {
              showToast(`already tracking · ${group.title}`);
              return;
            }
            if (!monitoringEnabled) {
              showToast("monitoring unavailable");
              return;
            }
            createMonitor({
              name: group.title,
              ean: group.ean,
              currency: group.currency,
              schedule,
            }).then((result) => {
              if (result) {
                monitored = [...monitored, {
                  id: result.id,
                  name: group.title,
                  ean: group.ean,
                  currency: group.currency,
                  current_price: group.bestPrice,
                  last_checked: null,
                  status: null,
                  trend: "flat",
                  history: [],
                }];
                monitoredIds = new Set(monitored.map((m) => m.id));
                showToast(`exported to monitoring · ${group.title}`);
                if (headerEl) {
                  headerEl.remove();
                  headerEl = buildHeader();
                  root.insertBefore(headerEl, mainEl);
                }
              } else {
                showToast("monitoring unavailable");
              }
            });
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
    if (gPressed && e.key === "s") { page = "search"; pushUrl("search", query); renderPage(); gPressed = false; }
    if (gPressed && e.key === "m") { page = "monitored"; pushUrl("monitored"); renderPage(); gPressed = false; }
  });

  window.addEventListener("popstate", () => {
    const newPage = getPage();
    const newQ = fromSlug(new URLSearchParams(window.location.search).get("q") ?? "");
    if (newPage !== page || newQ !== query) {
      page = newPage;
      query = newQ;
      renderPage();
      if (query && page === "search") handleSearch(query);
    }
  });

  fetchConfig().then(async (cfg) => {
    monitoringEnabled = cfg.monitoring_enabled;
    if (monitoringEnabled) {
      monitored = await fetchMonitored();
      monitoredIds = new Set(monitored.map((m) => m.id));
    }
    renderPage();
    if (query) handleSearch(query);
  });
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

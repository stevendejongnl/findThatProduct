export type Page = "search" | "monitored";

export interface HeaderOptions {
  page: Page;
  monitoredCount: number;
  theme: "light" | "dark";
  monitoringEnabled: boolean;
  onNavigate: (page: Page) => void;
  onThemeToggle: () => void;
  onSearch: (query: string) => void;
  query: string;
}

let clockInterval: ReturnType<typeof setInterval> | null = null;

function moonIcon(): string {
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
}

function sunIcon(): string {
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>`;
}

function searchIcon(): string {
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>`;
}

function fmt(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

export function renderHeader(opts: HeaderOptions): HTMLElement {
  const header = document.createElement("header");
  header.className = "app-header";

  const inner = document.createElement("div");
  inner.className = "container app-header__inner";

  // Brand
  const brand = document.createElement("button");
  brand.className = "app-header__brand";
  brand.type = "button";
  brand.innerHTML = `<span class="app-header__logo">F</span><span class="app-header__wordmark">findThatProduct</span>`;
  brand.addEventListener("click", () => opts.onNavigate("search"));
  inner.appendChild(brand);

  // Search
  const searchShell = document.createElement("div");
  searchShell.className = "app-header__search input-shell";
  const searchIcon_ = document.createElement("span");
  searchIcon_.className = "app-header__search-icon";
  searchIcon_.innerHTML = searchIcon();
  const input = document.createElement("input");
  input.type = "search";
  input.value = opts.query;
  input.placeholder = "Search products, brands, models, EAN…";
  input.className = "app-header__search-input";
  const kbd = document.createElement("kbd");
  kbd.textContent = "⌘K";
  searchShell.appendChild(searchIcon_);
  searchShell.appendChild(input);
  searchShell.appendChild(kbd);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const v = input.value.trim();
      if (v) opts.onSearch(v);
    }
  });

  inner.appendChild(searchShell);

  // Spacer
  const spacer = document.createElement("div");
  spacer.style.flex = "1";
  inner.appendChild(spacer);

  // Meta
  const meta = document.createElement("span");
  meta.className = "app-header__meta";
  meta.innerHTML = `<span class="dot dot--down"></span> 10 src`;
  inner.appendChild(meta);

  // Clock
  const clock = document.createElement("span");
  clock.className = "app-header__clock mono";
  clock.textContent = fmt(new Date());
  if (clockInterval) clearInterval(clockInterval);
  clockInterval = setInterval(() => { clock.textContent = fmt(new Date()); }, 1000);
  inner.appendChild(clock);

  // Theme toggle
  const themeBtn = document.createElement("button");
  themeBtn.className = "app-header__theme-btn";
  themeBtn.type = "button";
  themeBtn.setAttribute("aria-label", "Toggle theme");
  themeBtn.innerHTML = opts.theme === "dark" ? sunIcon() : moonIcon();
  themeBtn.addEventListener("click", opts.onThemeToggle);
  inner.appendChild(themeBtn);

  header.appendChild(inner);

  // Sub-nav (breadcrumb)
  const nav = document.createElement("div");
  nav.className = "app-subnav";
  const navInner = document.createElement("div");
  navInner.className = "container app-subnav__inner";

  function crumb(label: string, pg: Page, active: boolean): HTMLElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `app-subnav__crumb${active ? " app-subnav__crumb--active" : ""}`;
    btn.textContent = label;
    if (pg === "monitored") {
      const count = document.createElement("span");
      count.className = "app-subnav__count";
      count.textContent = `(${opts.monitoredCount})`;
      btn.appendChild(count);
    }
    btn.addEventListener("click", () => opts.onNavigate(pg));
    return btn;
  }

  function chevron(): HTMLElement {
    const s = document.createElement("span");
    s.className = "app-subnav__sep";
    s.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--ink-4)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>`;
    return s;
  }

  // Home crumb
  const homeBtn = document.createElement("button");
  homeBtn.type = "button";
  homeBtn.className = "app-subnav__crumb";
  homeBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m3 11 9-8 9 8"/><path d="M5 10v10a1 1 0 0 0 1 1h3v-6h6v6h3a1 1 0 0 0 1-1V10"/></svg> Home`;
  homeBtn.addEventListener("click", () => opts.onNavigate("search"));
  navInner.appendChild(homeBtn);
  navInner.appendChild(chevron());

  navInner.appendChild(crumb("Search", "search", opts.page === "search"));
  if (opts.monitoringEnabled) {
    navInner.appendChild(chevron());
    navInner.appendChild(crumb("Monitored", "monitored", opts.page === "monitored"));
  }

  // Right side — actions injected per-page via dataset
  const navRight = document.createElement("div");
  navRight.className = "app-subnav__right";
  navRight.id = "subnav-right";
  navInner.appendChild(navRight);

  nav.appendChild(navInner);
  header.appendChild(nav);

  return header;
}

import { MonitoredItem } from "../infrastructure/monitoredApi";
import { renderSparkline } from "./Sparkline";

type SortKey = "name" | "current" | "delta";
type SortDir = "asc" | "desc";

function trendArrow(trend: MonitoredItem["trend"]): string {
  return trend === "down" ? "↓" : trend === "up" ? "↑" : "—";
}

function trendClass(trend: MonitoredItem["trend"]): string {
  return trend === "down" ? "text-down" : trend === "up" ? "text-up" : "text-muted";
}

export function renderMonitoredPage(
  monitored: MonitoredItem[],
  onRemove: (id: string) => void,
): HTMLElement {
  const page = document.createElement("main");
  page.className = "monitored-page";

  let filter = "";
  let view: "all" | "alerts" | "drops" | "rising" = "all";
  let sortKey: SortKey = "delta";
  let sortDir: SortDir = "asc";

  // ── KPI cards ─────────────────────────────────────────────────────────────
  const kpiSection = document.createElement("section");
  kpiSection.style.cssText = "padding: 24px 0 8px;";

  const kpiGrid = document.createElement("div");
  kpiGrid.className = "monitored-kpi-grid";

  const dropping = monitored.filter((m) => m.trend === "down").length;
  const rising = monitored.filter((m) => m.trend === "up").length;

  function makeKpi(icon: string, label: string, value: string | number, sub: string, tone?: "accent" | "down"): HTMLElement {
    const card = document.createElement("div");
    card.className = "monitored-kpi";
    const iconSvgs: Record<string, string> = {
      box: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m21 16-9 5-9-5V8l9-5 9 5z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`,
      bell: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>`,
      arrowDown: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`,
      download: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/></svg>`,
    };
    const iconClass = tone === "accent" ? "monitored-kpi__icon monitored-kpi__icon--accent"
      : tone === "down" ? "monitored-kpi__icon monitored-kpi__icon--down"
      : "monitored-kpi__icon";
    const valueClass = tone === "accent" ? "monitored-kpi__value monitored-kpi__value--accent"
      : tone === "down" ? "monitored-kpi__value monitored-kpi__value--down"
      : "monitored-kpi__value";
    card.innerHTML = `
      <div class="monitored-kpi__header">
        <span class="${iconClass}">${iconSvgs[icon] ?? ""}</span>
        <span class="label" style="margin-bottom:0">${label}</span>
      </div>
      <div class="${valueClass}">${value}</div>
      <div class="monitored-kpi__sub">${sub}</div>
    `;
    return card;
  }

  kpiGrid.appendChild(makeKpi("box", "Tracked products", monitored.length, "across sources"));
  kpiGrid.appendChild(makeKpi("bell", "Active alerts", monitored.filter(m => m.trend === "down").length, "price dropping", "accent"));
  kpiGrid.appendChild(makeKpi("arrowDown", "Dropping · 24h", dropping, `${rising} rising`, "down"));
  kpiGrid.appendChild(makeKpi("download", "Sources", monitored.reduce((acc, m) => acc + (m.history?.length ?? 0), 0), "data points tracked"));
  kpiSection.appendChild(kpiGrid);
  page.appendChild(kpiSection);

  // ── Title bar ─────────────────────────────────────────────────────────────
  const titleBar = document.createElement("section");
  titleBar.className = "monitored-titlebar";
  const titleInner = document.createElement("div");
  titleInner.className = "container monitored-titlebar__inner";

  const title = document.createElement("h1");
  title.className = "monitored-titlebar__title";
  title.innerHTML = `Monitored products <span class="monitored-titlebar__count mono">[${monitored.length}]</span>`;
  titleInner.appendChild(title);

  const statsEl = document.createElement("div");
  statsEl.className = "monitored-titlebar__stats mono";
  const renderStats = () => {
    const dropping = monitored.filter((m) => m.trend === "down").length;
    const rising = monitored.filter((m) => m.trend === "up").length;
    const flat = monitored.filter((m) => m.trend === "flat").length;
    statsEl.innerHTML = [
      stat("dropping", dropping, dropping > 0 ? "text-down" : ""),
      stat("rising", rising, rising > 0 ? "text-up" : ""),
      stat("flat", flat, ""),
      stat("last sweep", "just now", ""),
    ].join("");
  };
  renderStats();
  titleInner.appendChild(statsEl);

  const titleActions = document.createElement("div");
  titleActions.className = "monitored-titlebar__actions";
  titleActions.innerHTML = `<button class="btn btn--ghost btn--small">↓ csv</button>`;
  titleInner.appendChild(titleActions);

  titleBar.appendChild(titleInner);
  page.appendChild(titleBar);

  // ── Toolbar ───────────────────────────────────────────────────────────────
  const toolbar = document.createElement("section");
  toolbar.className = "monitored-toolbar";
  const toolbarInner = document.createElement("div");
  toolbarInner.className = "container monitored-toolbar__inner";

  const filterShell = document.createElement("div");
  filterShell.className = "monitored-toolbar__filter";
  filterShell.innerHTML = `<span class="monitored-toolbar__prompt">›</span>`;
  const filterInput = document.createElement("input");
  filterInput.type = "text";
  filterInput.placeholder = "filter by name or ean…";
  filterInput.className = "monitored-toolbar__input mono";
  filterShell.appendChild(filterInput);
  toolbarInner.appendChild(filterShell);

  const viewLabel = document.createElement("span");
  viewLabel.className = "monitored-toolbar__view-label";
  viewLabel.textContent = "view";
  toolbarInner.appendChild(viewLabel);

  const viewGroup = document.createElement("div");
  viewGroup.className = "monitored-toolbar__views";
  const views: Array<["all" | "alerts" | "drops" | "rising", string]> = [
    ["all", "all"], ["alerts", "alerts"], ["drops", "dropping"], ["rising", "rising"],
  ];
  const viewBtns: HTMLButtonElement[] = [];
  views.forEach(([k, label], i) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `monitored-toolbar__view-btn${view === k ? " monitored-toolbar__view-btn--active" : ""}`;
    btn.dataset["border"] = i === 0 ? "left" : "";
    btn.textContent = label;
    btn.addEventListener("click", () => {
      view = k;
      viewBtns.forEach((b) => b.classList.remove("monitored-toolbar__view-btn--active"));
      btn.classList.add("monitored-toolbar__view-btn--active");
      renderTable();
    });
    viewBtns.push(btn);
    viewGroup.appendChild(btn);
  });
  toolbarInner.appendChild(viewGroup);

  const showingEl = document.createElement("span");
  showingEl.className = "monitored-toolbar__showing mono";
  toolbarInner.appendChild(showingEl);

  toolbar.appendChild(toolbarInner);
  page.appendChild(toolbar);

  // ── Table ─────────────────────────────────────────────────────────────────
  const tableSection = document.createElement("section");
  tableSection.className = "monitored-table-section";
  const tableWrap = document.createElement("div");
  tableWrap.className = "container monitored-table-wrap";
  const tableScroll = document.createElement("div");
  tableScroll.className = "monitored-table-scroll";

  const table = document.createElement("table");
  table.className = "mon-table";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  const cols: Array<{ label: string; key?: SortKey; cls?: string }> = [
    { label: "#", cls: "num-cell" },
    { label: "product", key: "name" },
    { label: "ean" },
    { label: "current", key: "current", cls: "right" },
    { label: "Δ", key: "delta", cls: "right" },
    { label: "history · 30d" },
    { label: "" },
  ];

  const thEls: HTMLTableCellElement[] = [];
  cols.forEach((col) => {
    const th = document.createElement("th");
    if (col.cls) th.className = col.cls;
    if (col.key) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "mon-table__sort-btn";
      btn.addEventListener("click", () => {
        if (sortKey === col.key) sortDir = sortDir === "asc" ? "desc" : "asc";
        else { sortKey = col.key!; sortDir = "asc"; }
        renderTable();
        updateSortIndicators();
      });
      const labelEl = document.createElement("span");
      labelEl.textContent = col.label;
      const indicator = document.createElement("span");
      indicator.className = "mon-table__sort-ind";
      indicator.dataset["key"] = col.key;
      indicator.textContent = col.key === sortKey ? (sortDir === "asc" ? "↑" : "↓") : "·";
      btn.appendChild(labelEl);
      btn.appendChild(indicator);
      th.appendChild(btn);
    } else {
      th.textContent = col.label;
    }
    thEls.push(th);
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  table.appendChild(tbody);
  tableScroll.appendChild(table);
  tableWrap.appendChild(tableScroll);
  tableSection.appendChild(tableWrap);
  page.appendChild(tableSection);

  function updateSortIndicators() {
    table.querySelectorAll<HTMLElement>(".mon-table__sort-ind").forEach((el) => {
      const k = el.dataset["key"];
      el.textContent = k === sortKey ? (sortDir === "asc" ? "↑" : "↓") : "·";
      el.classList.toggle("mon-table__sort-ind--active", k === sortKey);
    });
  }

  function renderTable() {
    let list = monitored.filter((m) =>
      m.name.toLowerCase().includes(filter.toLowerCase()) ||
      (m.ean ?? "").includes(filter)
    );
    if (view === "drops") list = list.filter((m) => m.trend === "down");
    if (view === "rising") list = list.filter((m) => m.trend === "up");

    list.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "name") return a.name.localeCompare(b.name) * dir;
      if (sortKey === "current") return ((a.current_price ?? 0) - (b.current_price ?? 0)) * dir;
      if (sortKey === "delta") return 0;
      return 0;
    });

    showingEl.textContent = `showing ${list.length}/${monitored.length} · auto-sweep every 15min`;

    tbody.innerHTML = "";

    if (list.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 7;
      td.className = "monitored-empty";
      td.textContent = "no products match this filter.";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    list.forEach((m, i) => {
      const tr = document.createElement("tr");

      const nameCell = m.url
        ? `<a href="${m.url}" target="_blank" rel="noopener noreferrer" class="monitored-name monitored-name--link">${m.name}</a>`
        : `<span class="monitored-name">${m.name}</span>`;

      tr.innerHTML = `
        <td class="num-cell">${String(i + 1).padStart(2, "0")}</td>
        <td class="monitored-name-cell">${nameCell}</td>
        <td class="monitored-ean mono">${m.ean ?? "—"}</td>
        <td class="right monitored-current">
          <div class="monitored-current__price">${m.current_price !== null ? `${m.currency} ${m.current_price.toFixed(2).replace(".", ",")}` : "—"}</div>
          <div class="monitored-current__sub">${m.last_checked ?? ""}</div>
        </td>
        <td class="right ${trendClass(m.trend)}">${trendArrow(m.trend)}</td>
        <td class="monitored-spark"></td>
        <td class="right monitored-remove"></td>
      `;

      const sparkCell = tr.querySelector<HTMLElement>(".monitored-spark")!;
      if (m.history.length >= 2) {
        sparkCell.appendChild(renderSparkline(m.history, 120, 26));
      }

      const removeCell = tr.querySelector<HTMLElement>(".monitored-remove")!;
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "monitored-remove__btn";
      removeBtn.title = "stop monitoring";
      removeBtn.textContent = "×";
      removeBtn.addEventListener("click", () => onRemove(m.id));
      removeCell.appendChild(removeBtn);

      tbody.appendChild(tr);
    });
  }

  filterInput.addEventListener("input", () => {
    filter = filterInput.value;
    renderTable();
  });

  renderTable();
  return page;
}

function stat(label: string, value: string | number, cls: string): string {
  return `<span class="monitored-stat"><span class="monitored-stat__label">${label}</span> <span class="monitored-stat__value${cls ? ` ${cls}` : ""}">${value}</span></span>`;
}

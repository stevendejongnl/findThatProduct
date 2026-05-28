import { MonitoredProduct } from "../domain/MonitoredProduct";
import { renderSparkline } from "./Sparkline";

type SortKey = "name" | "current" | "delta";
type SortDir = "asc" | "desc";

function fmtPrice(v: number | null, currency: string): string {
  if (v === null) return "—";
  return `${currency} ${v.toFixed(2).replace(".", ",")}`;
}

function trendArrow(trend: MonitoredProduct["trend"]): string {
  return trend === "down" ? "↓" : trend === "up" ? "↑" : "—";
}

function trendClass(trend: MonitoredProduct["trend"]): string {
  return trend === "down" ? "text-down" : trend === "up" ? "text-up" : "text-muted";
}

export function renderMonitoredPage(
  monitored: MonitoredProduct[],
  onRemove: (id: string) => void,
): HTMLElement {
  const page = document.createElement("main");
  page.className = "monitored-page";

  let filter = "";
  let view: "all" | "alerts" | "drops" | "rising" = "all";
  let sortKey: SortKey = "delta";
  let sortDir: SortDir = "asc";

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
    const alerts = monitored.filter((m) => m.alerted).length;
    const dropping = monitored.filter((m) => m.trend === "down").length;
    const rising = monitored.filter((m) => m.trend === "up").length;
    const flat = monitored.filter((m) => m.trend === "flat").length;
    statsEl.innerHTML = [
      stat("alerts", alerts, alerts > 0 ? "text-accent" : ""),
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
    { label: "target", cls: "right" },
    { label: "current", key: "current", cls: "right" },
    { label: "Δ", key: "delta", cls: "right" },
    { label: "history · 30d" },
    { label: "src", cls: "right" },
    { label: "checked" },
    { label: "added" },
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
    if (view === "alerts") list = list.filter((m) => m.alerted);
    if (view === "drops") list = list.filter((m) => m.trend === "down");
    if (view === "rising") list = list.filter((m) => m.trend === "up");

    list.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "name") return a.name.localeCompare(b.name) * dir;
      if (sortKey === "current") return ((a.currentPrice ?? 0) - (b.currentPrice ?? 0)) * dir;
      if (sortKey === "delta") return (a.delta - b.delta) * dir;
      return 0;
    });

    showingEl.textContent = `showing ${list.length}/${monitored.length} · auto-sweep every 15min`;

    tbody.innerHTML = "";

    if (list.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 11;
      td.className = "monitored-empty";
      td.textContent = "no products match this filter.";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    list.forEach((m, i) => {
      const tr = document.createElement("tr");
      const atTarget = m.currentPrice !== null && m.targetPrice !== null && m.currentPrice <= m.targetPrice;
      const distToTarget = (m.currentPrice ?? 0) - (m.targetPrice ?? 0);

      tr.innerHTML = `
        <td class="num-cell">${String(i + 1).padStart(2, "0")}</td>
        <td class="monitored-name-cell">
          <span class="monitored-name">${m.name}</span>
          ${m.alerted ? `<span class="badge badge--accent">● alert</span>` : ""}
          ${atTarget && !m.alerted ? `<span class="badge badge--down">at target</span>` : ""}
        </td>
        <td class="monitored-ean mono">${m.ean ?? "—"}</td>
        <td class="right monitored-target">${fmtPrice(m.targetPrice, m.currency)}</td>
        <td class="right monitored-current">
          <div class="monitored-current__price${atTarget ? " text-down" : ""}">${fmtPrice(m.currentPrice, m.currency)}</div>
          <div class="monitored-current__sub">${distToTarget > 0 ? `+${fmtPrice(distToTarget, m.currency)} above` : atTarget ? "at target" : ""}</div>
        </td>
        <td class="right ${trendClass(m.trend)}">${trendArrow(m.trend)} ${m.delta === 0 ? "—" : fmtPrice(Math.abs(m.delta), m.currency)}</td>
        <td class="monitored-spark"></td>
        <td class="right"><span class="text-ink">${m.sources}</span><span class="text-muted">/10</span></td>
        <td class="text-muted">${m.lastChecked}</td>
        <td class="text-muted">${m.added}</td>
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

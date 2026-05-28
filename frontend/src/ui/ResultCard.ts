import { ProductGroup } from "./groupResults";
import { MonitoredProduct } from "../domain/MonitoredProduct";
import { renderSparkline } from "./Sparkline";
import { showExplainPopup } from "./ExplainPopup";

function fmtPricePlain(v: number | null, currency: string): string {
  if (v === null) return "—";
  return `${currency} ${v.toFixed(2).replace(".", ",")}`;
}

function savingsPct(best: number, avg: number): string {
  return (((avg - best) / avg) * 100).toFixed(1);
}

const SCHEDULES: Array<[string, string]> = [
  ["Every 6 hours (recommended)", "0 */6 * * *"],
  ["Every hour", "0 * * * *"],
  ["Every 12 hours", "0 */12 * * *"],
  ["Once a day", "0 0 * * *"],
];

export function renderResultCard(
  group: ProductGroup,
  index: number,
  monitoredIds: Set<string>,
  onMonitor: (group: ProductGroup, schedule: string) => void,
  query = "",
): HTMLElement {
  const card = document.createElement("article");
  card.className = "result-card";

  const key = group.ean ?? group.key;
  const isTracked = monitoredIds.has(key);

  // ── Index col ─────────────────────────────────────────────────────────────
  const idxCol = document.createElement("div");
  idxCol.className = "result-card__index";
  idxCol.innerHTML = `
    <div class="result-card__idx-num">${String(index + 1).padStart(2, "0")}</div>
    <div class="result-card__idx-count mono">${group.listings.length}src</div>
  `;
  card.appendChild(idxCol);

  // ── Image col ─────────────────────────────────────────────────────────────
  const imgCol = document.createElement("div");
  imgCol.className = "result-card__image-wrap";
  if (group.image_url) {
    const img = document.createElement("img");
    img.src = group.image_url;
    img.alt = group.title;
    img.className = "result-card__image";
    img.onerror = () => {
      img.remove();
      imgCol.classList.add("result-card__image-wrap--empty");
    };
    imgCol.appendChild(img);
  } else {
    imgCol.classList.add("result-card__image-wrap--empty");
  }
  card.appendChild(imgCol);

  // ── Content col ───────────────────────────────────────────────────────────
  const content = document.createElement("div");
  content.className = "result-card__content";

  // Tag line
  const tagLine = document.createElement("div");
  tagLine.className = "result-card__tagline label";
  const tags: string[] = [];
  if (group.ean) tags.push(`<span class="mono">EAN ${group.ean}</span>`);
  tags.push(`<span>${group.listings.length} listing${group.listings.length !== 1 ? "s" : ""}</span>`);
  tagLine.innerHTML = tags.join(`<span class="result-card__dot"> · </span>`);
  content.appendChild(tagLine);

  // Title
  const title = document.createElement("h2");
  title.className = "result-card__title";
  title.textContent = group.title;
  content.appendChild(title);

  // Best source + toggle
  const bestListing = group.listings[0];
  const sourceRow = document.createElement("div");
  sourceRow.className = "result-card__source-row";

  if (bestListing) {
    const dot = document.createElement("span");
    dot.className = "result-card__source-dot";
    dot.textContent = bestListing.source.slice(0, 2).toUpperCase();
    sourceRow.appendChild(dot);

    const srcName = document.createElement("a");
    srcName.href = bestListing.url;
    srcName.target = "_blank";
    srcName.rel = "noopener noreferrer";
    srcName.className = "result-card__source-name";
    srcName.textContent = bestListing.source;
    sourceRow.appendChild(srcName);

    if (group.bestPrice !== null && group.avgPrice !== null && group.avgPrice > group.bestPrice) {
      const savings = document.createElement("span");
      savings.className = "result-card__savings";
      savings.innerHTML = `<span class="result-card__savings-price">${fmtPricePlain(group.bestPrice, group.currency)}</span> <span class="result-card__savings-pct">(-${savingsPct(group.bestPrice, group.avgPrice)}%)</span> <span class="result-card__savings-avg">vs avg ${fmtPricePlain(group.avgPrice, group.currency)}</span>`;
      sourceRow.appendChild(savings);
    }
  }

  content.appendChild(sourceRow);

  // Expandable listings
  const listingsEl = renderListings(group);
  listingsEl.style.display = "none";

  if (group.listings.length > 1) {
    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "result-card__toggle";
    toggleBtn.textContent = "view all listings";
    let expanded = false;
    toggleBtn.addEventListener("click", () => {
      expanded = !expanded;
      listingsEl.style.display = expanded ? "" : "none";
      toggleBtn.textContent = expanded ? "collapse" : "view all listings";
    });
    sourceRow.appendChild(toggleBtn);
  }

  content.appendChild(listingsEl);

  // Action buttons
  const actions = document.createElement("div");
  actions.className = "result-card__actions";

  const monitorWrap = document.createElement("div");
  monitorWrap.className = "result-card__monitor-wrap";

  if (isTracked) {
    const trackingBtn = document.createElement("button");
    trackingBtn.type = "button";
    trackingBtn.className = "btn btn--small btn--tracking";
    trackingBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5 10 17l9-10"/></svg>Tracking`;
    monitorWrap.appendChild(trackingBtn);
  } else {
    let pickerOpen = false;

    const monBtn = document.createElement("button");
    monBtn.type = "button";
    monBtn.className = "btn btn--small btn--primary";
    monBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5 10 17l9-10"/></svg>Monitor`;

    const picker = document.createElement("div");
    picker.className = "result-card__schedule-picker";
    picker.style.display = "none";

    const pickerLabel = document.createElement("span");
    pickerLabel.className = "result-card__schedule-label";
    pickerLabel.textContent = "Check price:";
    picker.appendChild(pickerLabel);

    const select = document.createElement("select");
    select.className = "result-card__schedule-select";
    SCHEDULES.forEach(([label, value]) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      select.appendChild(opt);
    });
    picker.appendChild(select);

    const confirmBtn = document.createElement("button");
    confirmBtn.type = "button";
    confirmBtn.className = "btn btn--small btn--primary";
    confirmBtn.textContent = "Confirm";
    confirmBtn.addEventListener("click", () => {
      onMonitor(group, select.value);
      picker.style.display = "none";
      pickerOpen = false;
      monBtn.style.display = "";
    });
    picker.appendChild(confirmBtn);

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "btn btn--small btn--ghost";
    cancelBtn.textContent = "Cancel";
    cancelBtn.addEventListener("click", () => {
      picker.style.display = "none";
      pickerOpen = false;
      monBtn.style.display = "";
    });
    picker.appendChild(cancelBtn);

    monBtn.addEventListener("click", () => {
      pickerOpen = !pickerOpen;
      picker.style.display = pickerOpen ? "flex" : "none";
      monBtn.style.display = pickerOpen ? "none" : "";
    });

    monitorWrap.appendChild(monBtn);
    monitorWrap.appendChild(picker);
  }

  actions.appendChild(monitorWrap);

  if (bestListing) {
    const openBtn = document.createElement("a");
    openBtn.href = bestListing.url;
    openBtn.target = "_blank";
    openBtn.rel = "noopener noreferrer";
    openBtn.className = "btn btn--small";
    openBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7"/><path d="M8 7h9v9"/></svg>Open at source`;
    actions.appendChild(openBtn);

    const explainBtn = document.createElement("button");
    explainBtn.type = "button";
    explainBtn.className = "btn btn--small";
    explainBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>Explain`;
    explainBtn.addEventListener("click", () =>
      showExplainPopup({ title: group.title, url: bestListing.url, price: group.bestPrice, query })
    );
    actions.appendChild(explainBtn);
  }

  content.appendChild(actions);
  card.appendChild(content);

  // ── Price col ─────────────────────────────────────────────────────────────
  const priceCol = document.createElement("div");
  priceCol.className = "result-card__price-col result-price";

  const priceLabel = document.createElement("div");
  priceLabel.className = "label";
  priceLabel.textContent = "Best price";
  priceCol.appendChild(priceLabel);

  const priceEl = document.createElement("div");
  priceEl.className = "result-card__price-big";
  if (group.bestPrice !== null) {
    const [whole, dec] = group.bestPrice.toFixed(2).split(".");
    priceEl.innerHTML = `<span class="result-card__price-currency">${group.currency}</span><span class="result-card__price-whole">${whole}</span><span class="result-card__price-dec">,${dec}</span>`;
  } else {
    priceEl.textContent = "—";
  }
  priceCol.appendChild(priceEl);

  const priceNote = document.createElement("div");
  priceNote.className = "result-card__price-note";
  priceNote.textContent = "incl. shipping";
  priceCol.appendChild(priceNote);

  if (group.bestPrice !== null) {
    const p = group.bestPrice;
    const sparkData = [p * 1.08, p * 1.05, p * 1.03, p * 1.01, p];
    const sparkWrap = document.createElement("div");
    sparkWrap.className = "result-card__spark";
    sparkWrap.appendChild(renderSparkline(sparkData, 170, 36, true));
    priceCol.appendChild(sparkWrap);
  }

  card.appendChild(priceCol);
  return card;
}

function renderListings(group: ProductGroup): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "result-card__listings";

  group.listings.forEach((listing, i) => {
    const row = document.createElement("div");
    row.className = "listing-row";

    const num = document.createElement("span");
    num.className = "listing-row__num mono";
    num.textContent = String(i + 1).padStart(2, "0");

    const src = document.createElement("span");
    src.className = "listing-row__source";
    const dot = document.createElement("span");
    dot.className = "listing-row__dot";
    dot.textContent = listing.source.slice(0, 2).toUpperCase();
    const name = document.createElement("a");
    name.href = listing.url;
    name.target = "_blank";
    name.rel = "noopener noreferrer";
    name.className = `listing-row__name${i === 0 ? " listing-row__name--best" : ""}`;
    name.textContent = listing.source;
    src.appendChild(dot);
    src.appendChild(name);

    const priceCell = document.createElement("span");
    priceCell.className = "listing-row__price";
    if (i === 0) {
      const badge = document.createElement("span");
      badge.className = "badge badge--accent";
      badge.textContent = "Best";
      priceCell.appendChild(badge);
    }
    priceCell.appendChild(document.createTextNode(
      listing.price !== null ? `${listing.currency} ${listing.price.toFixed(2).replace(".", ",")}` : "—"
    ));

    row.appendChild(num);
    row.appendChild(src);
    row.appendChild(priceCell);
    wrap.appendChild(row);
  });

  return wrap;
}

export function makeMonitoredProduct(group: ProductGroup): MonitoredProduct {
  const price = group.bestPrice;
  return {
    id: group.ean ?? group.key,
    name: group.title,
    ean: group.ean,
    currency: group.currency,
    targetPrice: price !== null ? Math.round(price * 0.95 * 100) / 100 : null,
    currentPrice: price,
    prevPrice: group.avgPrice,
    sources: group.listings.length,
    lastChecked: "just now",
    trend: "flat",
    delta: 0,
    history: price !== null ? [price * 1.08, price * 1.05, price * 1.03, price * 1.01, price] : [],
    alerted: false,
    added: new Date().toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" }),
    url: group.listings[0]?.url ?? "",
  };
}

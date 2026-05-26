import { ProductResult } from "../domain/ProductResult";

export function renderProductHero(query: string, queryType: string, results: ProductResult[]): HTMLElement {
  const section = document.createElement("div");
  section.className = "product-hero";

  const imageResult = results.find((r) => r.image_url) ?? null;
  const ean = results.find((r) => r.ean)?.ean ?? null;

  const imgWrap = document.createElement("div");
  imgWrap.className = "product-hero__image-wrap";
  if (imageResult?.image_url) {
    const img = document.createElement("img");
    img.src = imageResult.image_url;
    img.alt = imageResult.title;
    img.className = "product-hero__image";
    img.onerror = () => {
      img.style.display = "none";
      imgWrap.classList.add("product-hero__image-wrap--empty");
    };
    imgWrap.appendChild(img);
  } else {
    imgWrap.classList.add("product-hero__image-wrap--empty");
  }
  section.appendChild(imgWrap);

  const info = document.createElement("div");
  info.className = "product-hero__info";

  const typeLabel = queryType === "ean" ? "EAN lookup" : "Product search";
  const typeBadge = document.createElement("span");
  typeBadge.className = `product-hero__type product-hero__type--${queryType}`;
  typeBadge.textContent = typeLabel;
  info.appendChild(typeBadge);

  const title = document.createElement("h2");
  title.className = "product-hero__title";
  title.textContent = results.length > 0 ? results[0].title : query;
  info.appendChild(title);

  if (ean) {
    const eanEl = document.createElement("p");
    eanEl.className = "product-hero__ean";
    eanEl.textContent = `EAN: ${ean}`;
    info.appendChild(eanEl);
  }

  const meta = document.createElement("p");
  meta.className = "product-hero__meta";
  const pricesWithValue = results.filter((r) => r.price !== null);
  if (pricesWithValue.length > 0) {
    const prices = pricesWithValue.map((r) => r.price as number);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const currency = results[0].currency;
    meta.textContent =
      min === max
        ? `${currency} ${min.toFixed(2)} · ${results.length} store${results.length !== 1 ? "s" : ""}`
        : `${currency} ${min.toFixed(2)} – ${max.toFixed(2)} · ${results.length} store${results.length !== 1 ? "s" : ""}`;
  } else {
    meta.textContent = `${results.length} result${results.length !== 1 ? "s" : ""}`;
  }
  info.appendChild(meta);

  section.appendChild(info);
  return section;
}

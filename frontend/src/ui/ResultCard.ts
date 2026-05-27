import { ProductResult } from "../domain/ProductResult";
import { showExplainPopup } from "./ExplainPopup";

export function renderResultCard(result: ProductResult, isBestPrice = false, query = ""): HTMLElement {
  const card = document.createElement("article");
  card.className = "result-card";

  const wrap = document.createElement("div");
  wrap.className = "result-card__image-wrap";
  if (result.image_url) {
    const img = document.createElement("img");
    img.src = result.image_url;
    img.alt = result.title;
    img.className = "result-card__image";
    img.onerror = () => {
      img.style.display = "none";
      wrap.classList.add("result-card__image-wrap--empty");
    };
    wrap.appendChild(img);
  } else {
    wrap.classList.add("result-card__image-wrap--empty");
  }
  card.appendChild(wrap);

  const body = document.createElement("div");
  body.className = "result-card__body";

  const titleRow = document.createElement("div");
  titleRow.className = "result-card__title-row";
  const title = document.createElement("h2");
  title.className = "result-card__title";
  title.textContent = result.title;
  titleRow.appendChild(title);
  if (isBestPrice) {
    const badge = document.createElement("span");
    badge.className = "result-card__badge";
    badge.textContent = "Best price";
    titleRow.appendChild(badge);
  }
  body.appendChild(titleRow);

  const price = document.createElement("p");
  price.className = "result-card__price";
  price.textContent =
    result.price !== null
      ? `${result.currency} ${result.price.toFixed(2)}`
      : "Price unknown";
  body.appendChild(price);

  const source = document.createElement("p");
  source.className = "result-card__source";
  source.textContent = result.source;
  body.appendChild(source);

  if (result.ean) {
    const eanLink = document.createElement("a");
    eanLink.href = `/?q=${encodeURIComponent(result.ean)}`;
    eanLink.target = "_blank";
    eanLink.rel = "noopener noreferrer";
    eanLink.className = "result-card__ean";
    eanLink.textContent = `EAN: ${result.ean}`;
    eanLink.title = "Search by EAN in new tab";
    body.appendChild(eanLink);
  }

  const link = document.createElement("a");
  link.href = result.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.className = "result-card__link";
  link.textContent = "View deal →";
  body.appendChild(link);

  const explainBtn = document.createElement("button");
  explainBtn.type = "button";
  explainBtn.className = "result-card__explain-btn";
  explainBtn.textContent = "Why is this a good deal?";
  explainBtn.setAttribute("aria-label", `Explain why ${result.title} is a good deal`);
  explainBtn.addEventListener("click", () =>
    showExplainPopup({ title: result.title, url: result.url, price: result.price, query })
  );
  body.appendChild(explainBtn);

  card.appendChild(body);
  return card;
}

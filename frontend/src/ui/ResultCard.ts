import { ProductResult } from "../domain/ProductResult";

export function renderResultCard(result: ProductResult): HTMLElement {
  const card = document.createElement("article");
  card.className = "result-card";

  if (result.image_url) {
    const img = document.createElement("img");
    img.src = result.image_url;
    img.alt = result.title;
    img.className = "result-card__image";
    card.appendChild(img);
  }

  const title = document.createElement("h2");
  title.className = "result-card__title";
  title.textContent = result.title;
  card.appendChild(title);

  const price = document.createElement("p");
  price.className = "result-card__price";
  price.textContent =
    result.price !== null
      ? `${result.currency} ${result.price.toFixed(2)}`
      : "Price unknown";
  card.appendChild(price);

  const source = document.createElement("p");
  source.className = "result-card__source";
  source.textContent = `via ${result.source}`;
  card.appendChild(source);

  const link = document.createElement("a");
  link.href = result.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "View →";
  card.appendChild(link);

  return card;
}

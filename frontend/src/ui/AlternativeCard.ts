import { AlternativeResult } from "../domain/AlternativeResult";

export function renderAlternativeCard(alt: AlternativeResult): HTMLElement {
  const card = document.createElement("article");
  card.className = "alternative-card";

  const title = document.createElement("h3");
  title.className = "alternative-card__title";
  title.textContent = alt.title;
  card.appendChild(title);

  const reason = document.createElement("p");
  reason.className = "alternative-card__reason";
  reason.textContent = alt.reason;
  card.appendChild(reason);

  const price = document.createElement("p");
  price.className = "alternative-card__price";
  price.textContent =
    alt.price !== null ? `${alt.currency} ${alt.price.toFixed(2)}` : "Price unknown";
  card.appendChild(price);

  const link = document.createElement("a");
  link.href = alt.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.className = "alternative-card__link";
  link.textContent = "View →";
  card.appendChild(link);

  return card;
}

import { AlternativeResult } from "../domain/AlternativeResult";
import { renderAlternativeCard } from "./AlternativeCard";

export function renderAlternativesList(alternatives: AlternativeResult[]): HTMLElement | null {
  if (alternatives.length === 0) return null;

  const section = document.createElement("section");
  section.className = "alternatives-list";

  const heading = document.createElement("h2");
  heading.className = "alternatives-list__heading";
  heading.textContent = "Alternatives you might consider";
  section.appendChild(heading);

  for (const alt of alternatives) {
    section.appendChild(renderAlternativeCard(alt));
  }

  return section;
}

export interface ExplainParams {
  title: string;
  url: string;
  price: number | null;
  query: string;
}

export function showExplainPopup(params: ExplainParams): void {
  const existing = document.querySelector(".explain-popup");
  if (existing) existing.remove();

  const overlay = document.createElement("div");
  overlay.className = "explain-popup";

  const box = document.createElement("div");
  box.className = "explain-popup__box";

  const closeBtn = document.createElement("button");
  closeBtn.className = "explain-popup__close";
  closeBtn.textContent = "×";
  closeBtn.setAttribute("aria-label", "Close");
  closeBtn.addEventListener("click", () => overlay.remove());
  box.appendChild(closeBtn);

  const loading = document.createElement("p");
  loading.className = "explain-popup__loading";
  loading.textContent = "Analyzing deal…";
  box.appendChild(loading);

  overlay.appendChild(box);
  document.body.appendChild(overlay);

  fetch("/api/explain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: params.title, url: params.url, price: params.price, query: params.query }),
  })
    .then((r) => r.json())
    .then((data: { explanation: string | null; warnings: string[] }) => {
      loading.remove();
      if (data.explanation) {
        const content = document.createElement("p");
        content.className = "explain-popup__content";
        content.textContent = data.explanation;
        box.appendChild(content);
      } else {
        const err = document.createElement("p");
        err.className = "explain-popup__error";
        err.textContent = "Could not analyze this deal right now.";
        box.appendChild(err);
      }
    })
    .catch(() => {
      loading.remove();
      const err = document.createElement("p");
      err.className = "explain-popup__error";
      err.textContent = "Could not analyze this deal right now.";
      box.appendChild(err);
    });
}

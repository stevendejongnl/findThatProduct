let toastEl: HTMLElement | null = null;
let toastTimer: ReturnType<typeof setTimeout> | null = null;

export function showToast(message: string): void {
  if (!toastEl) {
    toastEl = document.createElement("div");
    toastEl.className = "toast";
    document.body.appendChild(toastEl);
  }

  if (toastTimer) clearTimeout(toastTimer);

  const check = document.createElement("span");
  check.className = "toast__icon";
  check.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5 10 17l9-10"/></svg>`;

  toastEl.innerHTML = "";
  toastEl.appendChild(check);
  toastEl.appendChild(document.createTextNode(message));
  toastEl.classList.add("toast--visible");

  toastTimer = setTimeout(() => {
    toastEl?.classList.remove("toast--visible");
  }, 2800);
}

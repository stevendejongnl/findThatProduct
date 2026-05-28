export function renderFooter(): HTMLElement {
  const footer = document.createElement("footer");
  footer.className = "app-footer";
  footer.innerHTML = `
    <div class="container app-footer__inner">
      <span><kbd>↵</kbd>search</span>
      <span><kbd>g s</kbd>search</span>
      <span><kbd>g m</kbd>monitored</span>
      <div style="flex:1"></div>
      <span>findThatProduct · internal tool</span>
    </div>
  `;
  return footer;
}

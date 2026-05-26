export function renderSearchBar(onSearch: (query: string) => void): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "search-bar";

  const form = document.createElement("form");
  form.className = "search-bar__form";

  const input = document.createElement("input");
  input.type = "search";
  input.placeholder = "EAN or product name…";
  input.className = "search-bar__input";
  input.autocomplete = "off";

  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Search";
  button.className = "search-bar__button";

  form.appendChild(input);
  form.appendChild(button);
  wrapper.appendChild(form);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const value = input.value.trim();
    if (value) onSearch(value);
  });

  return wrapper;
}

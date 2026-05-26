import { describe, it, expect, vi } from "vitest";
import { renderSearchBar } from "./SearchBar";

describe("renderSearchBar", () => {
  it("renders input and button", () => {
    const el = renderSearchBar(vi.fn());
    expect(el.querySelector("input")).not.toBeNull();
    expect(el.querySelector("button")).not.toBeNull();
  });

  it("calls onSearch with input value on submit", () => {
    const onSearch = vi.fn();
    const el = renderSearchBar(onSearch);
    const input = el.querySelector("input") as HTMLInputElement;
    const form = el.querySelector("form") as HTMLFormElement;
    input.value = "peanut butter";
    form.dispatchEvent(new Event("submit", { bubbles: true }));
    expect(onSearch).toHaveBeenCalledWith("peanut butter");
  });

  it("does not call onSearch when input is empty", () => {
    const onSearch = vi.fn();
    const el = renderSearchBar(onSearch);
    const form = el.querySelector("form") as HTMLFormElement;
    form.dispatchEvent(new Event("submit", { bubbles: true }));
    expect(onSearch).not.toHaveBeenCalled();
  });
});

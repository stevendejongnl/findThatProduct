import { describe, it, expect, vi, beforeEach } from "vitest";
import { showExplainPopup } from "./ExplainPopup";

beforeEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("showExplainPopup", () => {
  it("shows loading state immediately", () => {
    vi.stubGlobal("fetch", () => new Promise(() => {})); // never resolves
    showExplainPopup({ title: "Peanut Butter", url: "https://example.com", price: 4.99, query: "peanut butter" });
    const popup = document.querySelector(".explain-popup");
    expect(popup).not.toBeNull();
    expect(popup?.querySelector(".explain-popup__loading")).not.toBeNull();
  });

  it("shows explanation after successful fetch", async () => {
    vi.stubGlobal("fetch", () =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ explanation: "Great deal!", warnings: [] }),
      })
    );
    showExplainPopup({ title: "Peanut Butter", url: "https://example.com", price: 4.99, query: "peanut butter" });
    await vi.waitFor(() => {
      const content = document.querySelector(".explain-popup__content");
      expect(content).not.toBeNull();
    });
    expect(document.querySelector(".explain-popup__content")?.textContent).toContain("Great deal!");
  });

  it("shows error message when explanation is null", async () => {
    vi.stubGlobal("fetch", () =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ explanation: null, warnings: ["rate limit"] }),
      })
    );
    showExplainPopup({ title: "P", url: "https://example.com", price: null, query: "p" });
    await vi.waitFor(() => {
      expect(document.querySelector(".explain-popup__error")).not.toBeNull();
    });
  });

  it("shows error message on fetch failure", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new Error("network error")));
    showExplainPopup({ title: "P", url: "https://example.com", price: null, query: "p" });
    await vi.waitFor(() => {
      expect(document.querySelector(".explain-popup__error")).not.toBeNull();
    });
  });

  it("removes popup when close button is clicked", () => {
    vi.stubGlobal("fetch", () => new Promise(() => {}));
    showExplainPopup({ title: "P", url: "https://example.com", price: null, query: "p" });
    const btn = document.querySelector<HTMLButtonElement>(".explain-popup__close");
    btn?.click();
    expect(document.querySelector(".explain-popup")).toBeNull();
  });
});

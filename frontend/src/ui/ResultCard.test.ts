import { describe, it, expect } from "vitest";
import { renderResultCard } from "./ResultCard";
import { ProductGroup } from "./groupResults";

function makeGroup(overrides: Partial<ProductGroup> = {}): ProductGroup {
  return {
    key: "test-key",
    title: "Peanut Butter",
    ean: "8710447308431",
    image_url: null,
    bestPrice: 4.99,
    avgPrice: 5.49,
    currency: "EUR",
    listings: [
      { title: "Peanut Butter", price: 4.99, currency: "EUR", url: "https://example.com/product", source: "open_food_facts", image_url: null, ean: "8710447308431" },
    ],
    ...overrides,
  };
}

const noOp = (_g: ProductGroup, _s: string) => {};
const emptySet = new Set<string>();

describe("renderResultCard", () => {
  it("renders title", () => {
    const el = renderResultCard(makeGroup(), 0, emptySet, noOp);
    expect(el.querySelector(".result-card__title")?.textContent).toBe("Peanut Butter");
  });

  it("renders best price", () => {
    const el = renderResultCard(makeGroup({ bestPrice: 4.99 }), 0, emptySet, noOp);
    expect(el.querySelector(".result-card__price-whole")?.textContent).toContain("4");
  });

  it("renders price column when price is null", () => {
    const el = renderResultCard(makeGroup({ bestPrice: null }), 0, emptySet, noOp);
    expect(el.querySelector(".result-card__price-big")?.textContent).toBe("—");
  });

  it("renders source name", () => {
    const el = renderResultCard(makeGroup(), 0, emptySet, noOp);
    expect(el.querySelector(".result-card__source-name")?.textContent).toContain("open_food_facts");
  });

  it("renders link to product url", () => {
    const el = renderResultCard(makeGroup(), 0, emptySet, noOp);
    const link = el.querySelector<HTMLAnchorElement>(".result-card__source-name");
    expect(link?.getAttribute("href")).toBe("https://example.com/product");
  });

  it("renders image when image_url present", () => {
    const el = renderResultCard(makeGroup({ image_url: "https://example.com/img.jpg" }), 0, emptySet, noOp);
    const img = el.querySelector("img");
    expect(img?.getAttribute("src")).toBe("https://example.com/img.jpg");
  });

  it("renders no image when image_url is null", () => {
    const el = renderResultCard(makeGroup({ image_url: null }), 0, emptySet, noOp);
    expect(el.querySelector("img")).toBeNull();
  });

  it("renders Monitor button when not tracked", () => {
    const el = renderResultCard(makeGroup(), 0, emptySet, noOp);
    const btn = el.querySelector(".btn--primary");
    expect(btn?.textContent).toContain("Monitor");
  });

  it("renders Tracking button when already tracked", () => {
    const tracked = new Set(["8710447308431"]);
    const el = renderResultCard(makeGroup(), 0, tracked, noOp);
    const btn = el.querySelector(".btn--tracking");
    expect(btn?.textContent).toContain("Tracking");
  });

  it("calls onMonitor when Monitor button clicked then Confirm clicked", () => {
    let calledWith: [ProductGroup | null, string | null] = [null, null];
    const el = renderResultCard(makeGroup(), 0, emptySet, (g, s) => { calledWith = [g, s]; });
    const buttons = el.querySelectorAll<HTMLButtonElement>(".btn--primary");
    // First btn--primary is the Monitor button; click it to open picker
    buttons[0].click();
    // Now find the Confirm button (last btn--primary in the picker)
    const allPrimary = el.querySelectorAll<HTMLButtonElement>(".btn--primary");
    const confirmBtn = Array.from(allPrimary).find(b => b.textContent === "Confirm");
    confirmBtn?.click();
    expect(calledWith[0]).not.toBeNull();
    expect(typeof calledWith[1]).toBe("string");
  });

  it("renders index number", () => {
    const el = renderResultCard(makeGroup(), 2, emptySet, noOp);
    expect(el.querySelector(".result-card__idx-num")?.textContent).toBe("03");
  });

  it("renders EAN in tagline", () => {
    const el = renderResultCard(makeGroup(), 0, emptySet, noOp);
    expect(el.querySelector(".result-card__tagline")?.textContent).toContain("8710447308431");
  });
});

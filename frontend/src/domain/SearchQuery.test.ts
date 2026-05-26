import { describe, it, expect } from "vitest";
import { createSearchQuery, QueryType } from "./SearchQuery";

describe("createSearchQuery", () => {
  it("detects EAN-13", () => {
    const q = createSearchQuery("8710447308431");
    expect(q.type).toBe(QueryType.EAN);
    expect(q.raw).toBe("8710447308431");
  });

  it("detects EAN-8", () => {
    expect(createSearchQuery("01234565").type).toBe(QueryType.EAN);
  });

  it("treats short number as text", () => {
    expect(createSearchQuery("123").type).toBe(QueryType.TEXT);
  });

  it("treats product name as text", () => {
    expect(createSearchQuery("peanut butter").type).toBe(QueryType.TEXT);
  });

  it("throws on empty string", () => {
    expect(() => createSearchQuery("")).toThrow("Query too short");
  });

  it("throws on single char", () => {
    expect(() => createSearchQuery("a")).toThrow("Query too short");
  });
});

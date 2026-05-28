import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchMonitored, createMonitor, deleteMonitor, fetchConfig } from "./monitoredApi";

afterEach(() => vi.restoreAllMocks());

describe("fetchMonitored", () => {
  it("returns items on success", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ id: "ftp_123", name: "Sony", ean: "123", currency: "EUR", current_price: 329, last_checked: null, status: "ok", trend: "down", history: [335, 329] }]), { status: 200 })
    );
    const result = await fetchMonitored();
    expect(result[0].name).toBe("Sony");
  });

  it("returns empty array on error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 503 }));
    const result = await fetchMonitored();
    expect(result).toEqual([]);
  });
});

describe("createMonitor", () => {
  it("posts and returns id", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "ftp_123" }), { status: 201 })
    );
    const result = await createMonitor({ name: "Sony", ean: "123", currency: "EUR", schedule: "0 */6 * * *" });
    expect(result?.id).toBe("ftp_123");
  });

  it("returns null on failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 503 }));
    const result = await createMonitor({ name: "Sony", ean: "123", currency: "EUR", schedule: "0 */6 * * *" });
    expect(result).toBeNull();
  });
});

describe("fetchConfig", () => {
  it("returns monitoring_enabled true", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ monitoring_enabled: true }), { status: 200 })
    );
    const cfg = await fetchConfig();
    expect(cfg.monitoring_enabled).toBe(true);
  });

  it("returns disabled on error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 500 }));
    const cfg = await fetchConfig();
    expect(cfg.monitoring_enabled).toBe(false);
  });
});

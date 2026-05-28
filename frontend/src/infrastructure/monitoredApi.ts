export interface MonitoredItem {
  id: string;
  name: string;
  ean: string | null;
  currency: string;
  current_price: number | null;
  last_checked: string | null;
  status: string | null;
  trend: "up" | "down" | "flat";
  history: number[];
}

export interface CreateMonitorRequest {
  name: string;
  ean: string | null;
  currency: string;
  schedule: string;
}

export async function fetchMonitored(): Promise<MonitoredItem[]> {
  const resp = await fetch("/api/monitored");
  if (!resp.ok) return [];
  return resp.json();
}

export async function createMonitor(req: CreateMonitorRequest): Promise<{ id: string } | null> {
  const resp = await fetch("/api/monitored", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) return null;
  return resp.json();
}

export async function deleteMonitor(id: string): Promise<void> {
  await fetch(`/api/monitored/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function fetchConfig(): Promise<{ monitoring_enabled: boolean }> {
  const resp = await fetch("/api/config");
  if (!resp.ok) return { monitoring_enabled: false };
  return resp.json();
}

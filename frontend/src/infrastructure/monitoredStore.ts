import { MonitoredProduct } from "../domain/MonitoredProduct";

const KEY = "ftp-monitored";

export function loadMonitored(): MonitoredProduct[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function saveMonitored(list: MonitoredProduct[]): void {
  localStorage.setItem(KEY, JSON.stringify(list));
}

export function addMonitored(product: MonitoredProduct): MonitoredProduct[] {
  const list = loadMonitored();
  if (list.some((m) => m.id === product.id)) return list;
  const updated = [product, ...list];
  saveMonitored(updated);
  return updated;
}

export function removeMonitored(id: string): MonitoredProduct[] {
  const updated = loadMonitored().filter((m) => m.id !== id);
  saveMonitored(updated);
  return updated;
}

export function isMonitored(id: string): boolean {
  return loadMonitored().some((m) => m.id === id);
}

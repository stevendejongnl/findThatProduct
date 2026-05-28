export interface MonitoredProduct {
  id: string;
  name: string;
  ean: string | null;
  currency: string;
  targetPrice: number | null;
  currentPrice: number | null;
  prevPrice: number | null;
  sources: number;
  lastChecked: string;
  trend: "up" | "down" | "flat";
  delta: number;
  history: number[];
  alerted: boolean;
  added: string;
  url: string;
}

import type { LogEntry } from "./types.ts";

export const PAGE_SIZE = 50;

export interface FetchLogsResult {
  logs: LogEntry[];
  total: number;
}

export interface FetchLogParams {
  page: number;
  startDate?: string;
  endDate?: string;
}

export async function fetchLogs(
  { page, startDate, endDate }: FetchLogParams,
): Promise<FetchLogsResult> {
  let apiUrl = Deno.env.get("LOGWEB_API_URL");
  if (apiUrl) {
    apiUrl = apiUrl.replace(/\/+$/, "");
  }

  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("limit", String(PAGE_SIZE));
  if (startDate) params.set("start", startDate);
  if (endDate) params.set("end", endDate);

  const res = await fetch(`${apiUrl}/logs?${params}`);
  if (!res.ok) return { logs: [], total: 0 };

  const body = await res.json();
  return {
    logs: Array.isArray(body.logs) ? body.logs : [],
    total: typeof body.total === "number" ? body.total : 0,
  };
}
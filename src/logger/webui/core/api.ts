import type { LogEntry } from "./types.ts"

export const PAGE_SIZE = 50;

export interface FetchLogsResult {
    logs: LogEntry[];
    total: number;
}

export interface FetchLogParams{
    page: number;
}

export async function fetchLogs( {page}: FetchLogParams): Promise<FetchLogsResult> {
    const apiUrl = Deno.env.get("LOGWEB_API_ADDR");
    const res = await fetch(`${apiUrl}/logs?start=2025-01-01T00:00:00`);

    const all: LogEntry[] = await res.json();
    const sorted = [...all].sort((a, b) => b.occured.localeCompare(a.occured));
    const start = (page - 1) * PAGE_SIZE;
    const logs = sorted.slice(start, start + PAGE_SIZE);
    return {logs, total: sorted.length };
}
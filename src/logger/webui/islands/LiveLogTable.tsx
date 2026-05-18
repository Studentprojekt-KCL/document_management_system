// islands/LiveLogTable.tsx
import { useEffect } from "preact/hooks";
import { useSignal } from "@preact/signals";
import type { LogEntry } from "@/core/types.ts";
import { PAGE_SIZE } from "@/core/api.ts";
import { LogTable } from "@/components/LogTable.tsx";
import { LogFilters } from "@/components/LogFilters.tsx";
import { Pagination } from "@/components/Pagination.tsx";
import FlappyBirdIsland from "@/islands/FlappyBirdIsland.tsx";

interface Props {
  initialLogs: LogEntry[];
  initialTotal: number;
  initialPage: number;
  initialStart: string;
  initialEnd: string;
}

export default function LiveLogTable(
  {
    initialLogs,
    initialTotal,
    initialPage,
    initialStart,
    initialEnd,
  }: Props,
) {
  const logs = useSignal<LogEntry[]>(initialLogs);
  const total = useSignal(initialTotal);
  const page = useSignal(initialPage);
  const start = useSignal(initialStart);
  const end = useSignal(initialEnd);
  const live = useSignal(true);

  // Sync page + filters to the URL.
  useEffect(() => {
    const url = new URL(window.location.href);

    if (page.value === 1) url.searchParams.delete("page");
    else url.searchParams.set("page", String(page.value));

    if (start.value) url.searchParams.set("start", start.value);
    else url.searchParams.delete("start");

    if (end.value) url.searchParams.set("end", end.value);
    else url.searchParams.delete("end");

    history.replaceState(null, "", url.pathname + url.search);
  }, [page.value, start.value, end.value]);

  // Fetch logs.
  useEffect(() => {
    const tick = async () => {
      if (page.value === 67) return;

      const dataPage = page.value > 67 ? page.value - 1 : page.value;

      const qs = new URLSearchParams();
      qs.set("page", String(dataPage));
      if (start.value) qs.set("start", new Date(start.value).toISOString());
      if (end.value) qs.set("end", new Date(end.value).toISOString());
      try {
        const res = await fetch(`/api/logs?${qs}`);
        if (res.ok) {
          const body = await res.json();
          logs.value = body.logs ?? [];
          total.value = body.total ?? 0;
        }
      } catch (_) { /* retry next tick */ }
    };

    tick();
    if (!live.value || end.value || page.value !== 1) return;
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, [start.value, end.value, page.value, live.value]);

  const actualPages = Math.max(1, Math.ceil(total.value / PAGE_SIZE));
  const totalPages = actualPages + 1;

  return (
    <div>
      <LogFilters
        start={start.value}
        end={end.value}
        live={live.value}
        onStartChange={(v) => { start.value = v; page.value = 1; }}
        onEndChange={(v) => { end.value = v; page.value = 1; }}
        onLiveChange={(v) => live.value = v}
        onClear={() => { start.value = ""; end.value = ""; page.value = 1; }}
      />
      {page.value === 67
        ? <FlappyBirdIsland />
        : <LogTable logs={logs.value} />}
      <Pagination
        currentPage={page.value}
        totalPages={totalPages}
        onPageChange={(p) => page.value = p}
      />
    </div>
  );
}
// islands/LiveLogTable.tsx
import { useEffect } from "preact/hooks";
import { useSignal } from "@preact/signals";
import type { LogEntry } from "@/core/types.ts";
import { PAGE_SIZE } from "@/core/api.ts";
import { LogTable } from "@/components/LogTable.tsx";
import { LogFilters } from "@/components/LogFilters.tsx";
import { Pagination } from "@/components/Pagination.tsx";

interface Props {
  initialLogs: LogEntry[];
  initialTotal: number;
}

export default function LiveLogTable(
  { initialLogs, initialTotal }: Props,
) {
  const logs = useSignal<LogEntry[]>(initialLogs);
  const total = useSignal(initialTotal);
  const page = useSignal(1);
  const start = useSignal("");
  const end = useSignal("");
  const live = useSignal(true);

  useEffect(() => {
    const tick = async () => {
      const qs = new URLSearchParams();
      qs.set("page", String(page.value));
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

  const totalPages = Math.max(1, Math.ceil(total.value / PAGE_SIZE));

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
      <LogTable logs={logs.value} />
      <Pagination
        currentPage={page.value}
        totalPages={totalPages}
        onPageChange={(p) => page.value = p}
      />
    </div>
  );
}
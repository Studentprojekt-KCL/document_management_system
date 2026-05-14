import { useEffect } from "preact/hooks";
import { useSignal } from "@preact/signals";
import type { LogEntry } from "@/core/types.ts";
import { LogTable } from "@/components/LogTable.tsx";

export default function LiveLogTable ({ initial }: {initial: LogEntry[] }) {
    const logs = useSignal(initial);

    useEffect(() => {
    const tick = async () => {
      const res = await fetch("/api/logs");
      if (res.ok) logs.value = await res.json();
    };
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, []);

  return <LogTable logs={logs.value} />;
}
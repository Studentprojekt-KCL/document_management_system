// webui/components/LogRow.tsx
import type { LogEntry } from "@/core/types.ts";
import { formatDate } from "@/core/format.ts";
import { LogBadge } from "@/components/LogBadge.tsx";

interface LogRowProps {
  log: LogEntry;
}

export function LogRow({ log }: LogRowProps) {
  return (
    <tr class="hover:bg-gray-50 transition-colors">
      <td class="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
        {formatDate(log.occured)}
      </td>
      <td class="px-6 py-4 text-sm font-medium text-gray-900">
        {log.service}
      </td>
      <td class="px-6 py-4 text-sm">
        <LogBadge eventType={log.event_type} />
      </td>
      <td class="px-6 py-4 text-sm text-gray-600 font-mono">
        {log.message}
      </td>
    </tr>
  );
}
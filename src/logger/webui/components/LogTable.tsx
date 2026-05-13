// webui/components/LogTable.tsx
import type { LogEntry } from "@/core/types.ts";
import { LogRow } from "@/components/LogRow.tsx";

interface LogTableProps {
  logs: LogEntry[];
}

export function LogTable({ logs }: LogTableProps) {
  return (
    <div class="bg-white shadow-md rounded-lg overflow-hidden border border-gray-200">
      <table class="w-full text-left border-collapse">
        <thead class="bg-gray-100 border-b border-gray-200">
          <tr>
            <th class="px-6 py-3 text-xs font-semibold text-gray-600 uppercase">Occurred</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-600 uppercase">Service</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-600 uppercase">Type</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-600 uppercase">Message</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          {logs.length === 0 ? (
            <tr>
              <td colSpan={4} class="px-6 py-8 text-center text-gray-500">
                No logs recorded in the last hour.
              </td>
            </tr>
          ) : (
            logs.map((log) => <LogRow key={log.id} log={log} />)
          )}
        </tbody>
      </table>
    </div>
  );
}
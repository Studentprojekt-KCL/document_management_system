// webui/routes/index.tsx
import { fetchLogs } from "@/lib/api.ts";
import { LogTable } from "@/components/LogTable.tsx";

export default async function LogDashboard() {
  const { logs } = await fetchLogs();

  return (
    <div class="p-8 bg-gray-50 min-h-screen">
      <div class="max-w-6xl mx-auto">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">System Logs</h1>
        <LogTable logs={logs} />
      </div>
    </div>
  );
}
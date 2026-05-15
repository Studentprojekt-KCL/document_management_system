// webui/routes/index.tsx
import { define } from "@/utils.ts";
import { fetchLogs } from "@/core/api.ts";
import LiveLogTable from "@/islands/LiveLogTable.tsx";

export const handler = define.handlers({
  async GET(ctx) {
    const url = new URL(ctx.req.url);
    const initialPage = Math.max(
      1,
      parseInt(url.searchParams.get("page") ?? "1") || 1,
    );
    const initialStart = url.searchParams.get("start") ?? "";
    const initialEnd = url.searchParams.get("end") ?? "";
    const dataPage = initialPage === 67
      ? 1
      : initialPage > 67
      ? initialPage - 1
      : initialPage;

    const { logs, total } = await fetchLogs({
      page: dataPage,
      startDate: initialStart || undefined,
      endDate: initialEnd || undefined,
    });

    return {
      data: { logs, total, initialPage, initialStart, initialEnd },
    };
  },
});

export default define.page<typeof handler>(function LogDashboard({ data }) {
  return (
    <div class="p-8 bg-gray-50 min-h-screen">
      <div class="max-w-6xl mx-auto">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">System Logs</h1>
        <LiveLogTable
          initialLogs={data.logs}
          initialTotal={data.total}
          initialPage={data.initialPage}
          initialStart={data.initialStart}
          initialEnd={data.initialEnd}
        />
      </div>
    </div>
  );
});
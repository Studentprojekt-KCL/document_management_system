// webui/routes/index.tsx
import { define } from "@/utils.ts";
import { fetchLogs, PAGE_SIZE } from "@/core/api.ts";
import { LogTable } from "@/components/LogTable.tsx";
import { Pagination } from "@/components/Pagination.tsx";
import FlappyBirdIsland from "@/islands/FlappyBirdIsland.tsx";
import LiveLogTable from "@/islands/LiveLogTable.tsx";

export const handler = define.handlers({
  async GET(ctx) {
    const url = new URL(ctx.req.url);
    const pageNum = Math.max(
      1,
      parseInt(url.searchParams.get("page") ?? "1") || 1,
    );

    const { logs, total } = await fetchLogs({ page: pageNum });
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    return { data: { logs, total, page: pageNum, totalPages } };
  },
});

export default define.page<typeof handler>(function LogDashboard({ data }) {
  const { logs, page, totalPages } = data;
  return (
    <div class="p-8 bg-gray-50 min-h-screen">
      <div class="max-w-6xl mx-auto">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">System Logs</h1>
        {page === 67 ? (
          <FlappyBirdIsland />
        ) : page === 1 ? (
          <LiveLogTable initial={logs} />
        ) : (
          <LogTable logs={logs} />
        )}
        <Pagination currentPage={page} totalPages={totalPages} />
      </div>
    </div>
  );
});
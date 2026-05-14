// webui/routes/index.tsx
import { define } from "@/utils.ts";
import { fetchLogs } from "@/core/api.ts";
import FlappyBirdIsland from "@/islands/FlappyBirdIsland.tsx";
import LiveLogTable from "@/islands/LiveLogTable.tsx";

export const handler = define.handlers({
  async GET(ctx) {
    const url = new URL(ctx.req.url);
    const page = parseInt(url.searchParams.get("page") ?? "1") || 1;

    if (page === 67) {
      return { data: { easterEgg: true } };
    }

    const { logs, total } = await fetchLogs({ page: 1 });
    return { data: { easterEgg: false, logs, total } };
  },
});

export default define.page<typeof handler>(function LogDashboard({ data }) {
  return (
    <div class="p-8 bg-gray-50 min-h-screen">
      <div class="max-w-6xl mx-auto">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">System Logs</h1>
        {data.easterEgg
          ? <FlappyBirdIsland />
          : (
            <LiveLogTable
              initialLogs={data.logs!}
              initialTotal={data.total!}
            />
          )}
      </div>
    </div>
  );
});
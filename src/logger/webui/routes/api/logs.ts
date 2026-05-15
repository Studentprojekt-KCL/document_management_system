import { define } from "@/utils.ts";
import { fetchLogs } from "@/core/api.ts";

export const handler = define.handlers({
  async GET(ctx) {
    const url = new URL(ctx.req.url);
    const page = Math.max(
      1,
      parseInt(url.searchParams.get("page") ?? "1") || 1,
    );
    const startDate = url.searchParams.get("start") ?? undefined;
    const endDate = url.searchParams.get("end") ?? undefined;

    const { logs, total } = await fetchLogs({ page, startDate, endDate });
    return Response.json({ logs, total });
  },
});
import { define } from "@/utils.ts";
import { fetchLogs } from "@/core/api.ts";

export const handler = define.handlers({
  async GET() {
    const { logs } = await fetchLogs({ page: 1 });
    return Response.json(logs);
  },
});
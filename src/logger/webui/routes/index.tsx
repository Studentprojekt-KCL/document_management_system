// webui/routes/index.tsx

// 1. Define the TypeScript interface based on your Python Log model
interface LogEntry {
  id: number;
  occured: string;
  message: string;
  event_type: string; 
  service: string;
}

export default async function LogDashboard() {
  const apiUrl = Deno.env.get("LOG_API_URL");
  
  let allLogs: LogEntry[] = [];
  let fetchError = false;

  try {
    // 3. Fetch the logs from the Python API securely on the server
    const res = await fetch(`${apiUrl}/logs`);
    if (res.ok) {
      allLogs = await res.json();
    } else {
      console.error("Failed to fetch logs:", res.status);
      fetchError = true;
    }
  } catch (error) {
    console.error("API connection error:", error);
    fetchError = true;
  }

  return (
    <div class="p-8 bg-gray-50 min-h-screen">
      <div class="max-w-6xl mx-auto">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">System Logs</h1>
        
        {fetchError && (
          <div class="mb-4 p-4 bg-red-100 text-red-700 rounded-md border border-red-200">
            Error communicating with the Log API. Is the Python service running?
          </div>
        )}

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
              {allLogs.length === 0 && !fetchError ? (
                <tr>
                  <td colSpan={4} class="px-6 py-8 text-center text-gray-500">
                    No logs recorded in the last hour.
                  </td>
                </tr>
              ) : (
                allLogs.map((log) => {
                  const date = new Date(log.occured);
                  const formattedDate = date.toLocaleString();

                  return (
                    <tr key={log.id} class="hover:bg-gray-50 transition-colors">
                      <td class="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                        {formattedDate}
                      </td>
                      <td class="px-6 py-4 text-sm font-medium text-gray-900">
                        {log.service}
                      </td>
                      <td class="px-6 py-4 text-sm">
                        <span class={`px-2 py-1 rounded text-xs font-bold ${
                          log.event_type === 'ERROR' ? 'bg-red-100 text-red-700' : 
                          log.event_type === 'WARNING' ? 'bg-yellow-100 text-yellow-700' :
                          log.event_type === 'DEBUG' ? 'bg-gray-100 text-gray-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {log.event_type}
                        </span>
                      </td>
                      <td class="px-6 py-4 text-sm text-gray-600 font-mono">
                        {log.message}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
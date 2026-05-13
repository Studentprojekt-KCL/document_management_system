// webui/components/LogBadge.tsx

const BADGE_COLORS: Record<string, string> = {
  ERROR: "bg-red-100 text-red-700",
  WARNING: "bg-yellow-100 text-yellow-700",
  DEBUG: "bg-gray-100 text-gray-700",
  INFO: "bg-blue-100 text-blue-700",
};

const DEFAULT_COLOR = "bg-blue-100 text-blue-700";

interface LogBadgeProps {
  eventType: string;
}

export function LogBadge({ eventType }: LogBadgeProps) {
  const colorClasses = BADGE_COLORS[eventType] ?? DEFAULT_COLOR;

  return (
    <span class={`px-2 py-1 rounded text-xs font-bold ${colorClasses}`}>
      {eventType}
    </span>
  );
}
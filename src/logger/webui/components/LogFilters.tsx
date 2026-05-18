// components/LogFilters.tsx
interface Props {
  start: string;
  end: string;
  live: boolean;
  onStartChange: (v: string) => void;
  onEndChange: (v: string) => void;
  onLiveChange: (v: boolean) => void;
  onClear: () => void;
}

const inputCls =
  "px-3 py-2 border border-gray-300 rounded-md text-sm bg-white";
const btnCls =
  "px-3 py-2 text-sm bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200";

export function LogFilters({
  start,
  end,
  live,
  onStartChange,
  onEndChange,
  onLiveChange,
  onClear,
}: Props) {
  return (
    <div class="flex items-end gap-3 mb-4 flex-wrap">
      <label class="flex flex-col text-xs text-gray-600 gap-1">
        Start
        <input
          type="datetime-local"
          class={inputCls}
          value={start}
          onInput={(e) => onStartChange((e.target as HTMLInputElement).value)}
        />
      </label>

      <label class="flex flex-col text-xs text-gray-600 gap-1">
        End
        <input
          type="datetime-local"
          class={inputCls}
          value={end}
          onInput={(e) => onEndChange((e.target as HTMLInputElement).value)}
        />
      </label>

      <button type="button" class={btnCls} onClick={onClear}>
        Clear
      </button>

      <label class="flex items-center gap-2 text-sm text-gray-700 ml-auto">
        <input
          type="checkbox"
          checked={live}
          disabled={!!end}
          onChange={(e) =>
            onLiveChange((e.target as HTMLInputElement).checked)}
        />
        Live {end && (
          <span class="text-xs text-gray-500">(disabled — end set)</span>
        )}
      </label>
    </div>
  );
}
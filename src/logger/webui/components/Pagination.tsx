// webui/components/Pagination.tsx

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination(
  { currentPage, totalPages, onPageChange }: PaginationProps,
) {
  if (totalPages <= 1) return null;

  const hasPrev = currentPage > 1;
  const hasNext = currentPage < totalPages;

  const buttonBase = "px-4 py-2 text-sm font-medium rounded-md border";
  const enabled = "bg-white text-gray-700 border-gray-300 hover:bg-gray-50";
  const disabled =
    "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed";

  return (
    <div class="flex items-center justify-between mt-6">
      {hasPrev
        ? (
          <button
            type="button"
            class={`${buttonBase} ${enabled}`}
            onClick={() => onPageChange(currentPage - 1)}
          >
            ← Previous
          </button>
        )
        : <span class={`${buttonBase} ${disabled}`}>← Previous</span>}

      <span class="text-sm text-gray-600">
        Page {currentPage} of {totalPages}
      </span>

      {hasNext
        ? (
          <button
            type="button"
            class={`${buttonBase} ${enabled}`}
            onClick={() => onPageChange(currentPage + 1)}
          >
            Next →
          </button>
        )
        : <span class={`${buttonBase} ${disabled}`}>Next →</span>}
    </div>
  );
}
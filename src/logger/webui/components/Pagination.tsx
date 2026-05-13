// webui/components/Pagination.tsx

interface PaginationProps {
  currentPage: number;
  totalPages: number;
}

export function Pagination({ currentPage, totalPages }: PaginationProps) {
  if (totalPages <= 1) return null;

  const hasPrev = currentPage > 1;
  const hasNext = currentPage < totalPages;

  const prevHref = `?page=${currentPage - 1}`;
  const nextHref = `?page=${currentPage + 1}`;

  const buttonBase = "px-4 py-2 text-sm font-medium rounded-md border";
  const enabled = "bg-white text-gray-700 border-gray-300 hover:bg-gray-50";
  const disabled = "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed";

  return (
    <div class="flex items-center justify-between mt-6">
      {hasPrev
        ? (
          <a href={prevHref} class={`${buttonBase} ${enabled}`}>
            ← Previous
          </a>
        )
        : (
          <span class={`${buttonBase} ${disabled}`}>
            ← Previous
          </span>
        )}

      <span class="text-sm text-gray-600">
        Page {currentPage} of {totalPages}
      </span>

      {hasNext
        ? (
          <a href={nextHref} class={`${buttonBase} ${enabled}`}>
            Next →
          </a>
        )
        : (
          <span class={`${buttonBase} ${disabled}`}>
            Next →
          </span>
        )}
    </div>
  );
}
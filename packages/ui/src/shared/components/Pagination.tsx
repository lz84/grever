import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
}

export default function Pagination({ currentPage = 1, totalPages = 1, onPageChange }: PaginationProps) {
  // Defensive: guard against missing/invalid props
  if (typeof currentPage !== 'number' || typeof totalPages !== 'number' || totalPages <= 1) return null;
  if (typeof onPageChange !== 'function') return null;

  const clampedCurrent = Math.max(1, Math.min(currentPage, totalPages));

  const pages: (number | string)[] = [];
  const showPages = Math.min(5, totalPages);
  let start = Math.max(1, clampedCurrent - Math.floor(showPages / 2));
  const end = Math.min(totalPages, start + showPages - 1);
  start = Math.max(1, end - showPages + 1);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => onPageChange(clampedCurrent - 1)}
        disabled={clampedCurrent === 1}
        className="p-1 rounded-sm hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronLeft className="w-4 h-4 text-slate-500" />
      </button>
      {pages.map((p, i) =>
        typeof p === 'number' ? (
          <button
            key={i}
            onClick={() => onPageChange(p)}
            className={`min-w-[32px] h-8 text-sm rounded-sm transition-colors ${
              p === clampedCurrent
                ? 'bg-blue-600 text-white'
                : 'hover:bg-slate-100 text-slate-600'
            }`}
          >
            {p}
          </button>
        ) : (
          <span key={i} className="px-1 text-slate-400">
            {p}
          </span>
        )
      )}
      <button
        onClick={() => onPageChange(clampedCurrent + 1)}
        disabled={clampedCurrent === totalPages}
        className="p-1 rounded-sm hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronRight className="w-4 h-4 text-slate-500" />
      </button>
    </div>
  );
}

import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Props {
  total: number
  page: number
  pages: number
  label: string
  onPageChange: (page: number) => void
}

export function PaginationBar({ total, page, pages, label, onPageChange }: Props) {
  return (
    <div className="flex items-center justify-between px-3 py-2.5 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-950">
      <span className="text-xs text-gray-500">
        {total} {label} · page {page} of {pages}
      </span>
      <div className="flex items-center gap-1">
        <button onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page === 1}
          className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-40 transition-colors">
          <ChevronLeft className="w-4 h-4" />
        </button>
        <button onClick={() => onPageChange(Math.min(pages, page + 1))} disabled={page >= pages}
          className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-40 transition-colors">
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

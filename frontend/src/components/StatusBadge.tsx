export const STATUS_COLORS: Record<string, string> = {
  sent: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  opened: 'bg-blue-100 text-blue-700',
  pending: 'bg-yellow-100 text-yellow-700',
  sending: 'bg-gray-100 text-gray-600',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

import type { Toast as ToastState } from '@/hooks/useToast'

export function Toast({ toast }: { toast: ToastState }) {
  if (!toast) return null
  return (
    <div className={`fixed bottom-4 right-4 px-4 py-2 rounded-lg text-sm text-white shadow-lg ${
      toast.type === 'ok' ? 'bg-green-600' : 'bg-red-600'
    }`}>
      {toast.msg}
    </div>
  )
}

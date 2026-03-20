import { useState } from 'react'

export type Toast = { msg: string; type: 'ok' | 'err' } | null

export function useToast(duration = 3000) {
  const [toast, setToast] = useState<Toast>(null)
  const showToast = (msg: string, type: 'ok' | 'err' = 'ok') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), duration)
  }
  return { toast, showToast }
}

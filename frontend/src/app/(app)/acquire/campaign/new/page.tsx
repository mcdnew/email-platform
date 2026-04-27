'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createWorkerCampaign } from '@/lib/api'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { WorkerCampaignEditor } from '@/components/WorkerCampaignEditor'

export default function NewWorkerCampaignPage() {
  const router = useRouter()
  const qc = useQueryClient()
  const { toast, showToast } = useToast()

  const createMutation = useMutation({
    mutationFn: ({ name, config }: { name: string; config: Record<string, unknown> }) =>
      createWorkerCampaign({ name, config }),
    onSuccess: async (result) => {
      await qc.invalidateQueries({ queryKey: ['worker-campaigns'] })
      showToast('Campaign created')
      router.push(`/acquire/campaign/${encodeURIComponent(result.campaign)}`)
    },
    onError: (error: unknown) => showToast(error instanceof Error ? error.message : String(error), 'err'),
  })

  return (
    <div className="p-6 space-y-6">
      <div>
        <Link href="/acquire" className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
          ← Back to Acquire
        </Link>
        <h1 className="mt-2 text-xl font-semibold text-gray-900 dark:text-gray-100">New Campaign</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Build a configurable campaign from structured fields instead of cloning a hardcoded example.
        </p>
      </div>

      <WorkerCampaignEditor
        mode="create"
        saving={createMutation.isPending}
        onSave={(payload) => createMutation.mutate(payload)}
      />

      <Toast toast={toast} />
    </div>
  )
}

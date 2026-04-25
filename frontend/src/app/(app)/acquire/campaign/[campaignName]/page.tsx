'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getWorkerCampaignDetail, runWorkerCampaign } from '@/lib/api'

export default function AcquireCampaignDetailPage() {
  const params = useParams<{ campaignName: string }>()
  const campaignName = decodeURIComponent(params.campaignName)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['worker-campaign-detail', campaignName],
    queryFn: () => getWorkerCampaignDetail(campaignName),
    enabled: Boolean(campaignName),
  })

  const runMutation = useMutation({
    mutationFn: ({ dryRun }: { dryRun: boolean }) => runWorkerCampaign(campaignName, { dry_run: dryRun }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['worker-campaign-detail', campaignName] })
      await qc.invalidateQueries({ queryKey: ['worker-campaigns'] })
      await qc.invalidateQueries({ queryKey: ['activity-events'] })
    },
  })

  const cfg = data?.config ?? {}
  const campaign = (cfg.campaign as Record<string, unknown> | undefined) ?? {}
  const discover = (cfg.discover as Record<string, unknown> | undefined) ?? {}
  const sequence = (cfg.sequence as Array<Record<string, unknown>> | undefined) ?? []

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <Link href="/acquire" className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
            ← Back to Acquire
          </Link>
          <h1 className="mt-2 text-xl font-semibold text-gray-900 dark:text-gray-100">
            {campaignName}
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {String(campaign.product ?? '')}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => runMutation.mutate({ dryRun: false })}
            className="px-3 py-2 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            disabled={runMutation.isPending || Boolean(data?.running)}
          >
            Run
          </button>
          <button
            onClick={() => runMutation.mutate({ dryRun: true })}
            className="px-3 py-2 text-xs rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
            disabled={runMutation.isPending || Boolean(data?.running)}
          >
            Dry run
          </button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : !data ? (
        <p className="text-sm text-gray-500">Campaign data unavailable.</p>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Campaign</h2>
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              <div><span className="font-medium">Product:</span> {String(campaign.product ?? '—')}</div>
              <div><span className="font-medium">Language:</span> {String(campaign.language ?? '—')}</div>
              <div><span className="font-medium">Tone:</span> {String(campaign.tone ?? '—')}</div>
              <div><span className="font-medium">Sender:</span> {String(campaign.sender_name ?? '—')}</div>
              <div><span className="font-medium">Status:</span> {data.running ? 'running' : 'idle'}</div>
            </div>
          </section>

          <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Discovery</h2>
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              <div><span className="font-medium">Prompt:</span> {String(discover.prompt ?? '—')}</div>
              <div><span className="font-medium">Count:</span> {String(discover.count ?? '—')}</div>
              <div><span className="font-medium">Approval:</span> {String(discover.approval ?? '—')}</div>
            </div>
          </section>

          <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Stats</h2>
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              <div><span className="font-medium">Emails sent:</span> {String((data.stats as Record<string, unknown>).emails_sent ?? 0)}</div>
              <div><span className="font-medium">Started:</span> {data.started ?? '—'}</div>
              <div><span className="font-medium">Error:</span> {data.error ?? '—'}</div>
            </div>
          </section>

          <section className="xl:col-span-3 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Sequence</h2>
            {!sequence.length ? (
              <p className="text-sm text-gray-500">No sequence definition available.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                {sequence.map((step, index) => (
                  <div key={`${step.type}-${index}`} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">Step {index + 1}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {[`day ${String(step.day ?? 0)}`, String(step.type ?? 'followup')].join(' • ')}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  archiveWorkerCampaign,
  deleteWorkerCampaign,
  discoverWorkerCampaign,
  getWorkerCampaignActivity,
  getWorkerCampaignDetail,
  getWorkerCampaignTraces,
  runWorkerCampaign,
  updateWorkerCampaign,
} from '@/lib/api'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { WorkerCampaignEditor } from '@/components/WorkerCampaignEditor'

export default function AcquireCampaignDetailPage() {
  const params = useParams<{ campaignName: string }>()
  const campaignName = decodeURIComponent(params.campaignName)
  const qc = useQueryClient()
  const { toast, showToast } = useToast()
  const [configJson, setConfigJson] = useState('')
  const [previewTab, setPreviewTab] = useState<'json' | 'text' | 'html'>('json')
  const [discoverCount, setDiscoverCount] = useState('10')
  const [selectedRunId, setSelectedRunId] = useState('all')
  const [selectedTraceEvent, setSelectedTraceEvent] = useState('all')
  const [truncateAt, setTruncateAt] = useState('1200')
  const [deleteConfirmName, setDeleteConfirmName] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['worker-campaign-detail', campaignName],
    queryFn: () => getWorkerCampaignDetail(campaignName),
    enabled: Boolean(campaignName),
    refetchInterval: (query) => query.state.data?.running ? 4000 : false,
  })
  const { data: activityFeed } = useQuery({
    queryKey: ['worker-campaign-activity', campaignName],
    queryFn: () => getWorkerCampaignActivity(campaignName, { limit: 40 }),
    enabled: Boolean(campaignName),
    refetchInterval: data?.running ? 4000 : false,
  })
  const { data: traceEntries } = useQuery({
    queryKey: ['worker-campaign-traces', campaignName, selectedRunId],
    queryFn: () => getWorkerCampaignTraces(campaignName, { limit: 120, run_id: selectedRunId === 'all' ? undefined : selectedRunId }),
    enabled: Boolean(campaignName),
    refetchInterval: data?.running ? 4000 : false,
  })

  const runMutation = useMutation({
    mutationFn: ({ dryRun }: { dryRun: boolean }) => runWorkerCampaign(campaignName, { dry_run: dryRun }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['worker-campaign-detail', campaignName] }),
        qc.invalidateQueries({ queryKey: ['worker-campaigns'] }),
        qc.invalidateQueries({ queryKey: ['activity-events'] }),
        qc.invalidateQueries({ queryKey: ['worker-campaign-activity', campaignName] }),
        qc.invalidateQueries({ queryKey: ['worker-campaign-traces', campaignName] }),
      ])
      showToast('Cycle started')
    },
    onError: (error: unknown) => showToast(error instanceof Error ? error.message : String(error), 'err'),
  })
  const discoverMutation = useMutation({
    mutationFn: ({ dryRun }: { dryRun: boolean }) =>
      discoverWorkerCampaign(campaignName, { dry_run: dryRun, count: Number(discoverCount) || undefined }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['worker-campaign-detail', campaignName] }),
        qc.invalidateQueries({ queryKey: ['worker-campaigns'] }),
        qc.invalidateQueries({ queryKey: ['activity-events'] }),
        qc.invalidateQueries({ queryKey: ['worker-campaign-activity', campaignName] }),
        qc.invalidateQueries({ queryKey: ['worker-campaign-traces', campaignName] }),
      ])
      showToast('Discovery started')
    },
    onError: (error: unknown) => showToast(error instanceof Error ? error.message : String(error), 'err'),
  })
  const saveMutation = useMutation({
    mutationFn: (config: Record<string, unknown>) => updateWorkerCampaign(campaignName, { config }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['worker-campaign-detail', campaignName] }),
        qc.invalidateQueries({ queryKey: ['worker-campaigns'] }),
        qc.invalidateQueries({ queryKey: ['activity-events'] }),
      ])
      showToast('Campaign config saved')
    },
    onError: (error: unknown) => showToast(error instanceof Error ? error.message : String(error), 'err'),
  })
  const archiveMutation = useMutation({
    mutationFn: ({ archived }: { archived: boolean }) => archiveWorkerCampaign(campaignName, { archived }),
    onSuccess: async (result) => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['worker-campaign-detail', campaignName] }),
        qc.invalidateQueries({ queryKey: ['worker-campaigns'] }),
      ])
      showToast(result.archived ? 'Campaign archived' : 'Campaign restored')
    },
    onError: (error: unknown) => showToast(error instanceof Error ? error.message : String(error), 'err'),
  })
  const deleteMutation = useMutation({
    mutationFn: () => deleteWorkerCampaign(campaignName, { confirm_name: deleteConfirmName }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['worker-campaigns'] })
      showToast('Campaign deleted')
      window.location.href = '/acquire'
    },
    onError: (error: unknown) => showToast(error instanceof Error ? error.message : String(error), 'err'),
  })

  const cfg = data?.config ?? {}
  const campaign = (cfg.campaign as Record<string, unknown> | undefined) ?? {}
  const discover = (cfg.discover as Record<string, unknown> | undefined) ?? {}
  const sequence = (cfg.sequence as Array<Record<string, unknown>> | undefined) ?? []
  const truncationLimit = truncateAt === 'full' ? Number.POSITIVE_INFINITY : Number(truncateAt)

  function safeParsePayload(value: string | null): Record<string, unknown> | null {
    if (!value) return null
    try {
      return JSON.parse(value) as Record<string, unknown>
    } catch {
      return null
    }
  }

  const parsedTraceEntries = (traceEntries ?? []).map((entry) => ({
    ...entry,
    parsedPayload: safeParsePayload(entry.payload),
  }))
  const availableRunIds = Array.from(new Set(parsedTraceEntries.map((entry) => entry.run_id).filter(Boolean))) as string[]
  const availableEvents = Array.from(new Set(parsedTraceEntries.map((entry) => entry.event))).sort()
  const filteredTraceEntries = parsedTraceEntries.filter((entry) => selectedTraceEvent === 'all' || entry.event === selectedTraceEvent)
  const runSummaries = availableRunIds.map((runId) => {
    const entriesForRun = parsedTraceEntries.filter((entry) => entry.run_id === runId)
    const first = entriesForRun[entriesForRun.length - 1]
    const last = entriesForRun[0]
    const usageTotals = entriesForRun.reduce((acc, entry) => {
      const usage = entry.parsedPayload?.usage as Record<string, unknown> | undefined
      acc.input_tokens += Number(usage?.input_tokens ?? 0)
      acc.output_tokens += Number(usage?.output_tokens ?? 0)
      acc.cache_creation_input_tokens += Number(usage?.cache_creation_input_tokens ?? 0)
      acc.cache_read_input_tokens += Number(usage?.cache_read_input_tokens ?? 0)
      return acc
    }, { input_tokens: 0, output_tokens: 0, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 })
    return {
      runId,
      kind: first?.kind ?? '—',
      startedAt: first?.ts ?? '—',
      endedAt: last?.ts ?? '—',
      events: entriesForRun.length,
      usageTotals,
    }
  })

  async function copyTraceBundle() {
    const bundle = {
      campaignName,
      selectedRunId,
      selectedTraceEvent,
      truncateAt,
      activity: activityFeed?.entries ?? [],
      traces: filteredTraceEntries.map((entry) => ({
        ...entry,
        parsedPayload: entry.parsedPayload,
      })),
      runSummaries,
    }
    await navigator.clipboard.writeText(JSON.stringify(bundle, null, 2))
  }

  function renderPayload(value: string | null) {
    if (!value) return ''
    if (Number.isFinite(truncationLimit) && value.length > truncationLimit) {
      return `${value.slice(0, truncationLimit)}\n… truncated ${value.length - truncationLimit} chars`
    }
    return value
  }
  const textPreview = [
    `Campaign: ${campaignName}`,
    `Product: ${String(campaign.product ?? '—')}`,
    `Language: ${String(campaign.language ?? '—')}`,
    `Tone: ${String(campaign.tone ?? '—')}`,
    `Sender: ${String(campaign.sender_name ?? '—')}`,
    '',
    `Discovery prompt: ${String(discover.prompt ?? '—')}`,
    `Discovery count: ${String(discover.count ?? '—')}`,
    `Approval: ${String(discover.approval ?? '—')}`,
    '',
    'Sequence:',
    ...sequence.map((step, index) => `  ${index + 1}. day ${String(step.day ?? 0)} • ${String(step.type ?? 'followup')}`),
  ].join('\n')
  const htmlPreview = `
    <div style="font-family: system-ui, sans-serif; padding: 16px; line-height: 1.5;">
      <h1 style="margin: 0 0 12px 0;">${campaignName}</h1>
      <p style="margin: 0 0 8px 0;"><strong>Product:</strong> ${String(campaign.product ?? '—')}</p>
      <p style="margin: 0 0 8px 0;"><strong>Language:</strong> ${String(campaign.language ?? '—')}</p>
      <p style="margin: 0 0 8px 0;"><strong>Tone:</strong> ${String(campaign.tone ?? '—')}</p>
      <p style="margin: 0 0 16px 0;"><strong>Sender:</strong> ${String(campaign.sender_name ?? '—')}</p>
      <h2 style="margin: 16px 0 8px 0;">Discovery</h2>
      <p style="margin: 0 0 8px 0;">${String(discover.prompt ?? '—')}</p>
      <p style="margin: 0;"><strong>Count:</strong> ${String(discover.count ?? '—')} • <strong>Approval:</strong> ${String(discover.approval ?? '—')}</p>
      <h2 style="margin: 16px 0 8px 0;">Sequence</h2>
      <ul style="padding-left: 18px; margin: 0;">
        ${sequence.map((step, index) => `<li>Step ${index + 1}: day ${String(step.day ?? 0)} • ${String(step.type ?? 'followup')}</li>`).join('')}
      </ul>
    </div>
  `

  useEffect(() => {
    if (data?.config) {
      setConfigJson(JSON.stringify(data.config, null, 2))
    }
  }, [data?.config])

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
          <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
            `Run cycle` only processes existing active prospects. Use `Discover` to generate new leads.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => runMutation.mutate({ dryRun: false })}
            className="px-3 py-2 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            disabled={runMutation.isPending || Boolean(data?.running) || Boolean(data?.archived)}
          >
            Run cycle
          </button>
          <button
            onClick={() => runMutation.mutate({ dryRun: true })}
            className="px-3 py-2 text-xs rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
            disabled={runMutation.isPending || Boolean(data?.running) || Boolean(data?.archived)}
          >
            Dry run cycle
          </button>
          <input
            value={discoverCount}
            onChange={(event) => setDiscoverCount(event.target.value)}
            className="w-20 px-2 py-2 text-xs rounded-md border border-gray-300 bg-white text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
            aria-label="Discover count"
          />
          <button
            onClick={() => discoverMutation.mutate({ dryRun: false })}
            className="px-3 py-2 text-xs rounded-md bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50"
            disabled={discoverMutation.isPending || Boolean(data?.running) || Boolean(data?.archived)}
          >
            Discover
          </button>
          <button
            onClick={() => discoverMutation.mutate({ dryRun: true })}
            className="px-3 py-2 text-xs rounded-md bg-amber-100 text-amber-900 hover:bg-amber-200 dark:bg-amber-950 dark:text-amber-200 dark:hover:bg-amber-900 disabled:opacity-50"
            disabled={discoverMutation.isPending || Boolean(data?.running) || Boolean(data?.archived)}
          >
            Dry run discover
          </button>
          <button
            onClick={() => archiveMutation.mutate({ archived: !Boolean(data?.archived) })}
            className="px-3 py-2 text-xs rounded-md bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:bg-gray-950 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-900"
            disabled={archiveMutation.isPending || Boolean(data?.running)}
          >
            {data?.archived ? 'Restore' : 'Archive'}
          </button>
          <button
            onClick={() => {
              try {
                const parsed = JSON.parse(configJson) as Record<string, unknown>
                saveMutation.mutate(parsed)
              } catch {
                // invalid JSON aborts save
              }
            }}
            className="px-3 py-2 text-xs rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
            disabled={saveMutation.isPending}
          >
            Save JSON
          </button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : !data ? (
        <p className="text-sm text-gray-500">Campaign data unavailable.</p>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-3">
            <WorkerCampaignEditor
              mode="edit"
              initialName={campaignName}
              initialConfig={data.config}
              saving={saveMutation.isPending}
              onSave={({ config }) => saveMutation.mutate(config)}
            />
          </div>

          <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Campaign</h2>
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              <div><span className="font-medium">Product:</span> {String(campaign.product ?? '—')}</div>
              <div><span className="font-medium">Language:</span> {String(campaign.language ?? '—')}</div>
              <div><span className="font-medium">Tone:</span> {String(campaign.tone ?? '—')}</div>
              <div><span className="font-medium">Sender:</span> {String(campaign.sender_name ?? '—')}</div>
              <div><span className="font-medium">Status:</span> {data.archived ? 'archived' : data.running ? 'running' : 'idle'}</div>
              <div><span className="font-medium">Mode:</span> {data.mode ?? 'cycle'}</div>
            </div>
          </section>

          <section className="xl:col-span-3 bg-white dark:bg-gray-900 rounded-xl border border-red-200 dark:border-red-900/40 p-4">
            <h2 className="text-sm font-medium text-red-700 dark:text-red-300 mb-2">Danger Zone</h2>
            <p className="text-xs text-red-600 dark:text-red-400 mb-3">
              Hard delete removes the campaign definition and future run/discover access, but historical business records remain in the databases.
            </p>
            <div className="flex flex-col md:flex-row gap-3 items-start md:items-end">
              <div>
                <label className="block text-xs font-medium text-red-700 dark:text-red-300 mb-1">Type campaign name to confirm delete</label>
                <input
                  value={deleteConfirmName}
                  onChange={(event) => setDeleteConfirmName(event.target.value)}
                  className="rounded-md border border-red-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-red-900/60 dark:bg-gray-950 dark:text-gray-100"
                  placeholder={campaignName}
                />
              </div>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending || Boolean(data?.running) || deleteConfirmName !== campaignName}
                className="px-4 py-2 text-sm rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                Delete permanently
              </button>
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
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Config</h2>
              <div className="flex gap-2">
                {(['json', 'text', 'html'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setPreviewTab(tab)}
                    className={`px-2.5 py-1.5 text-xs rounded-md ${previewTab === tab ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-800 dark:bg-gray-800 dark:text-gray-200'}`}
                  >
                    {tab.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            {previewTab === 'json' ? (
              <textarea
                value={configJson}
                onChange={(e) => setConfigJson(e.target.value)}
                className="w-full min-h-[320px] rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-mono text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                spellCheck={false}
              />
            ) : previewTab === 'text' ? (
              <pre className="w-full min-h-[320px] rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-mono text-gray-900 whitespace-pre-wrap dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100">{textPreview}</pre>
            ) : (
              <iframe
                title="Campaign HTML Preview"
                className="w-full min-h-[320px] rounded-lg border border-gray-300 bg-white dark:border-gray-700"
                srcDoc={htmlPreview}
              />
            )}
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

          <section className="xl:col-span-3 grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Worker Activity</h2>
              {!activityFeed?.entries.length ? (
                <p className="text-sm text-gray-500">No worker activity yet.</p>
              ) : (
                <div className="space-y-2 max-h-[420px] overflow-auto">
                  {activityFeed.entries.map((entry) => (
                    <div key={entry.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                      <div className="text-xs text-gray-400">{entry.ts} • {entry.level}</div>
                      <div className="mt-1 text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{entry.message}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">LLM / Tool Trace</h2>
                <div className="flex flex-wrap gap-2">
                  <select
                    value={selectedRunId}
                    onChange={(event) => setSelectedRunId(event.target.value)}
                    className="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                  >
                    <option value="all">All runs</option>
                    {availableRunIds.map((runId) => <option key={runId} value={runId}>{runId}</option>)}
                  </select>
                  <select
                    value={selectedTraceEvent}
                    onChange={(event) => setSelectedTraceEvent(event.target.value)}
                    className="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                  >
                    <option value="all">All events</option>
                    {availableEvents.map((eventName) => <option key={eventName} value={eventName}>{eventName}</option>)}
                  </select>
                  <select
                    value={truncateAt}
                    onChange={(event) => setTruncateAt(event.target.value)}
                    className="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                  >
                    <option value="300">300 chars</option>
                    <option value="1200">1200 chars</option>
                    <option value="4000">4000 chars</option>
                    <option value="full">Full payload</option>
                  </select>
                  <button
                    onClick={() => { void copyTraceBundle() }}
                    className="px-2.5 py-1.5 text-xs rounded-md bg-emerald-600 text-white hover:bg-emerald-700"
                  >
                    Copy trace bundle
                  </button>
                </div>
              </div>
              {!!runSummaries.length && (
                <div className="mb-4 space-y-2">
                  {runSummaries.map((summary) => (
                    <div key={summary.runId} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                      <div className="text-xs text-gray-400">{summary.kind} • run {summary.runId}</div>
                      <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600 dark:text-gray-300">
                        <span>Started</span><span className="text-right">{summary.startedAt}</span>
                        <span>Ended</span><span className="text-right">{summary.endedAt}</span>
                        <span>Trace events</span><span className="text-right">{summary.events}</span>
                        <span>Input tokens</span><span className="text-right">{summary.usageTotals.input_tokens}</span>
                        <span>Output tokens</span><span className="text-right">{summary.usageTotals.output_tokens}</span>
                        <span>Cache create</span><span className="text-right">{summary.usageTotals.cache_creation_input_tokens}</span>
                        <span>Cache read</span><span className="text-right">{summary.usageTotals.cache_read_input_tokens}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {!filteredTraceEntries.length ? (
                <p className="text-sm text-gray-500">No trace entries yet.</p>
              ) : (
                <div className="space-y-2 max-h-[420px] overflow-auto">
                  {filteredTraceEntries.map((entry) => (
                    <div key={entry.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                      <div className="text-xs text-gray-400">{entry.ts} • {entry.kind} • {entry.event} • run {entry.run_id ?? '—'}</div>
                      <pre className="mt-2 text-[11px] whitespace-pre-wrap break-words text-gray-700 dark:text-gray-300">{renderPayload(entry.payload)}</pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>
      )}
      <Toast toast={toast} />
    </div>
  )
}

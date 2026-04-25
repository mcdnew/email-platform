'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAcquisitionCampaignSummaries, getActivityEvents, getConversations, getLeadCaptures, getProspects, getSequences, getWorkerCampaigns, handoffOutreachToNurture, reviewLeadCapture, runWorkerCampaign } from '@/lib/api'

function parseJson(value: string | null): Record<string, unknown> {
  if (!value) return {}
  try {
    return JSON.parse(value) as Record<string, unknown>
  } catch {
    return {}
  }
}

export default function AcquirePage() {
  const qc = useQueryClient()
  const [selectedSequences, setSelectedSequences] = useState<Record<number, string>>({})
  const { data: pendingCaptures, isLoading: capturesLoading } = useQuery({
    queryKey: ['lead-captures', 'pending_review'],
    queryFn: () => getLeadCaptures({ review_status: 'pending_review', source_type: 'web_discovery' }),
  })
  const { data: interestedProspects, isLoading: interestedLoading } = useQuery({
    queryKey: ['prospects', 'interested'],
    queryFn: () => getProspects({ lifecycle_stage: 'interested', per_page: 25, page: 1 }),
  })
  const { data: recentAcquireEvents, isLoading: eventsLoading } = useQuery({
    queryKey: ['activity-events', 'acquire'],
    queryFn: () => getActivityEvents({ source_module: 'acquire', limit: 8 }),
  })
  const { data: gmailConversations, isLoading: conversationsLoading } = useQuery({
    queryKey: ['conversations', 'gmail'],
    queryFn: () => getConversations({ channel: 'gmail', limit: 8 }),
  })
  const { data: campaignSummaries, isLoading: campaignSummariesLoading } = useQuery({
    queryKey: ['acquisition-campaign-summaries'],
    queryFn: getAcquisitionCampaignSummaries,
  })
  const { data: workerCampaigns, isLoading: workerCampaignsLoading } = useQuery({
    queryKey: ['worker-campaigns'],
    queryFn: getWorkerCampaigns,
  })
  const { data: sequences, isLoading: sequencesLoading } = useQuery({
    queryKey: ['sequences'],
    queryFn: getSequences,
  })

  const reviewMutation = useMutation({
    mutationFn: ({ id, review_status }: { id: number; review_status: 'approved' | 'rejected' }) =>
      reviewLeadCapture(id, { review_status }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['lead-captures'] }),
        qc.invalidateQueries({ queryKey: ['prospects'] }),
      ])
    },
  })
  const handoffMutation = useMutation({
    mutationFn: ({ prospectId, sequenceId }: { prospectId: number; sequenceId: number }) =>
      handoffOutreachToNurture({
        prospect_id: prospectId,
        campaign_key: 'acquire:manual-handoff',
        sequence_id: sequenceId,
        qualified: true,
      }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['prospects'] }),
        qc.invalidateQueries({ queryKey: ['activity-events'] }),
      ])
    },
  })
  const runCampaignMutation = useMutation({
    mutationFn: ({ campaignName, dryRun }: { campaignName: string; dryRun: boolean }) =>
      runWorkerCampaign(campaignName, { dry_run: dryRun }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['worker-campaigns'] }),
        qc.invalidateQueries({ queryKey: ['activity-events'] }),
      ])
    },
  })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Acquire</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Pending discovered leads and high-signal outreach contacts now owned by the core platform.
        </p>
      </div>

      <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Campaign Summary</h2>
          <span className="text-xs text-gray-400">{campaignSummaries?.length ?? 0} campaigns</span>
        </div>
        {campaignSummariesLoading ? (
          <p className="text-sm text-gray-500">Loading…</p>
        ) : !campaignSummaries?.length ? (
          <p className="text-sm text-gray-500">No mirrored acquisition campaigns yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {campaignSummaries.map((summary) => (
              <div key={summary.campaign_key} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{summary.campaign_key}</div>
                <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
                  <span>Pending review</span><span className="text-right">{summary.pending_review}</span>
                  <span>Interested</span><span className="text-right">{summary.interested}</span>
                  <span>Conversations</span><span className="text-right">{summary.conversations}</span>
                  <span>Events</span><span className="text-right">{summary.recent_events}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Worker Campaigns</h2>
          <span className="text-xs text-gray-400">{workerCampaigns?.length ?? 0} mirrored configs</span>
        </div>
        {workerCampaignsLoading ? (
          <p className="text-sm text-gray-500">Loading…</p>
        ) : !workerCampaigns?.length ? (
          <p className="text-sm text-gray-500">No worker campaign metadata available.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {workerCampaigns.map((campaign) => (
              <div key={campaign.name} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{campaign.name}</div>
                  <span className={`text-[11px] uppercase tracking-wide ${campaign.running ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-400'}`}>
                    {campaign.running ? 'running' : 'idle'}
                  </span>
                </div>
                <div className="mt-1 text-xs text-gray-500">{campaign.product}</div>
                <div className="mt-2 text-[11px] text-gray-500 line-clamp-3">{campaign.discover_prompt}</div>
                <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
                  <span>Language</span><span className="text-right">{campaign.language}</span>
                  <span>Discover count</span><span className="text-right">{campaign.discover_count}</span>
                  <span>Active</span><span className="text-right">{campaign.active}</span>
                  <span>Interested</span><span className="text-right">{campaign.interested}</span>
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => runCampaignMutation.mutate({ campaignName: campaign.name, dryRun: false })}
                    className="px-2.5 py-1.5 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                    disabled={runCampaignMutation.isPending || campaign.running}
                  >
                    Run
                  </button>
                  <button
                    onClick={() => runCampaignMutation.mutate({ campaignName: campaign.name, dryRun: true })}
                    className="px-2.5 py-1.5 text-xs rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
                    disabled={runCampaignMutation.isPending || campaign.running}
                  >
                    Dry run
                  </button>
                </div>
                {campaign.error && <div className="mt-2 text-[11px] text-red-500">{campaign.error}</div>}
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Pending Discovery Review</h2>
            <span className="text-xs text-gray-400">{pendingCaptures?.length ?? 0} items</span>
          </div>
          {capturesLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !pendingCaptures?.length ? (
            <p className="text-sm text-gray-500">No pending discovered leads.</p>
          ) : (
            <div className="space-y-3">
              {pendingCaptures.map((capture) => {
                const normalized = parseJson(capture.normalized_payload_json)
                const company = normalized.company as string | undefined
                const email = normalized.email as string | undefined
                const fact = normalized.fact as string | undefined
                const name = normalized.name as string | undefined
                return (
                  <div key={capture.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {name || company || capture.external_ref || `Lead #${capture.id}`}
                        </div>
                        <div className="text-xs text-gray-500 mt-1 truncate">
                          {[company, email].filter(Boolean).join(' • ') || 'No canonical email yet'}
                        </div>
                        {fact && <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">{fact}</p>}
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => reviewMutation.mutate({ id: capture.id, review_status: 'approved' })}
                          className="px-2.5 py-1.5 text-xs rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                          disabled={reviewMutation.isPending}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => reviewMutation.mutate({ id: capture.id, review_status: 'rejected' })}
                          className="px-2.5 py-1.5 text-xs rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
                          disabled={reviewMutation.isPending}
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Interested Contacts</h2>
            <span className="text-xs text-gray-400">{interestedProspects?.total ?? 0} contacts</span>
          </div>
          {interestedLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !interestedProspects?.items.length ? (
            <p className="text-sm text-gray-500">No contacts are currently marked interested.</p>
          ) : (
            <div className="space-y-3">
              {interestedProspects.items.map((prospect) => (
                <div key={prospect.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                        <Link
                          href={`/acquire/${prospect.id}`}
                          className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {prospect.name}
                        </Link>
                  <div className="text-xs text-gray-500 mt-1">
                    {[prospect.company, prospect.email].filter(Boolean).join(' • ')}
                  </div>
                  <div className="mt-2 text-[11px] uppercase tracking-wide text-amber-600 dark:text-amber-400">
                    {prospect.lifecycle_stage || 'interested'}
                  </div>
                  <div className="mt-3 flex flex-col sm:flex-row gap-2">
                    <select
                      value={selectedSequences[prospect.id] ?? ''}
                      onChange={(e) => setSelectedSequences((current) => ({ ...current, [prospect.id]: e.target.value }))}
                      className="min-w-0 flex-1 rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                      disabled={sequencesLoading}
                    >
                      <option value="">Select nurture sequence…</option>
                      {sequences?.map((sequence) => (
                        <option key={sequence.id} value={sequence.id}>{sequence.name}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => {
                        const sequenceId = Number(selectedSequences[prospect.id] ?? '')
                        if (!sequenceId) return
                        handoffMutation.mutate({ prospectId: prospect.id, sequenceId })
                      }}
                      className="px-3 py-2 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                      disabled={handoffMutation.isPending || !selectedSequences[prospect.id]}
                    >
                      Hand off to nurture
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Recent Acquisition Activity</h2>
            <span className="text-xs text-gray-400">{recentAcquireEvents?.length ?? 0} events</span>
          </div>
          {eventsLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !recentAcquireEvents?.length ? (
            <p className="text-sm text-gray-500">No recent acquisition activity.</p>
          ) : (
            <div className="space-y-3">
              {recentAcquireEvents.map((event) => (
                <div key={event.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{event.event_type}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {[event.campaign_key, event.created_at].filter(Boolean).join(' • ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Gmail Conversations</h2>
            <span className="text-xs text-gray-400">{gmailConversations?.length ?? 0} threads</span>
          </div>
          {conversationsLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !gmailConversations?.length ? (
            <p className="text-sm text-gray-500">No mirrored Gmail conversations yet.</p>
          ) : (
            <div className="space-y-3">
              {gmailConversations.map((conversation) => (
                <div key={conversation.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                  <Link
                    href={`/acquire/${conversation.prospect_id}`}
                    className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {conversation.provider_thread_id || `Conversation #${conversation.id}`}
                  </Link>
                  <div className="text-xs text-gray-500 mt-1">
                    {[conversation.campaign_key, conversation.state].filter(Boolean).join(' • ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

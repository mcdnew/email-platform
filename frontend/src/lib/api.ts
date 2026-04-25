// Typed API client — all calls proxied through /api/proxy/[...path]
// The proxy route handler attaches X-API-Key from the httpOnly cookie.

import type {
  Prospect, ProspectCreate, EmailTemplate, Sequence, SequenceStep,
  ScheduledEmail, SentEmail, AnalyticsSummary, PaginatedResponse, BulkImportResult, LeadCapture,
  ActivityEvent, Conversation,
} from './types'

async function req<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`/api/proxy${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (res.status === 401) {
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

function buildQs(params: Record<string, unknown>): string {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString()
  return qs ? `?${qs}` : ''
}

// ── Analytics ──────────────────────────────────────────────────────────────
export const getAnalytics = () => req<AnalyticsSummary>('/analytics/summary')

// ── Prospects ──────────────────────────────────────────────────────────────
export const getProspects = (params: {
  page?: number; per_page?: number; sort_by?: string;
  order?: string; search?: string; assigned?: string; unsubscribed?: string; lifecycle_stage?: string
}) => req<PaginatedResponse<Prospect>>(`/prospects${buildQs(params)}`)

export const createProspect = (data: ProspectCreate) =>
  req<Prospect>('/prospects', { method: 'POST', body: JSON.stringify(data) })

export const updateProspect = (id: number, data: Partial<ProspectCreate & { sequence_id: number | null; unsubscribed: boolean }>) =>
  req<Prospect>(`/prospects/${id}`, { method: 'PUT', body: JSON.stringify(data) })

export const deleteProspect = (id: number) =>
  req<void>(`/prospects/${id}`, { method: 'DELETE' })

export const bulkImportProspects = (items: ProspectCreate[]) =>
  req<BulkImportResult>('/prospects/bulk', { method: 'POST', body: JSON.stringify(items) })

export const assignSequence = (data: {
  prospect_ids: number[]; sequence_id: number; ventilate_days?: number; start_date?: string
}) => req<{ message: string }>('/assign-sequence', { method: 'POST', body: JSON.stringify(data) })

// ── Templates ──────────────────────────────────────────────────────────────
export const getTemplates = () => req<EmailTemplate[]>('/templates')

export const createTemplate = (data: Omit<EmailTemplate, 'id' | 'created_at'>) =>
  req<EmailTemplate>('/templates', { method: 'POST', body: JSON.stringify(data) })

export const updateTemplate = (id: number, data: Partial<Omit<EmailTemplate, 'id' | 'created_at'>>) =>
  req<EmailTemplate>(`/templates/${id}`, { method: 'PATCH', body: JSON.stringify(data) })

export const deleteTemplate = (id: number) =>
  req<void>(`/templates/${id}`, { method: 'DELETE' })

// ── Sequences ──────────────────────────────────────────────────────────────
export const getSequences = () => req<Sequence[]>('/sequences')

export const createSequence = (data: { name: string; bcc_email?: string }) =>
  req<Sequence>('/sequences', { method: 'POST', body: JSON.stringify(data) })

export const updateSequence = (id: number, data: { name?: string; bcc_email?: string }) =>
  req<Sequence>(`/sequences/${id}`, { method: 'PATCH', body: JSON.stringify(data) })

export const deleteSequence = (id: number) =>
  req<void>(`/sequences/${id}`, { method: 'DELETE' })

export const getSteps = (sequenceId: number) =>
  req<SequenceStep[]>(`/sequences/${sequenceId}/steps`)

export const createStep = (sequenceId: number, data: { template_id: number; delay_days: number }) =>
  req<SequenceStep>(`/sequences/${sequenceId}/steps`, { method: 'POST', body: JSON.stringify({ ...data, sequence_id: sequenceId }) })

export const updateStep = (stepId: number, data: Partial<SequenceStep>) =>
  req<SequenceStep>(`/sequences/steps/${stepId}`, { method: 'PATCH', body: JSON.stringify(data) })

export const deleteStep = (stepId: number) =>
  req<void>(`/sequences/steps/${stepId}`, { method: 'DELETE' })

export const reorderSteps = (sequenceId: number, steps: Array<{ step_id: number; delay_days: number }>) =>
  req<{ message: string }>(`/sequences/${sequenceId}/reorder`, { method: 'POST', body: JSON.stringify({ steps }) })

// ── Queue ──────────────────────────────────────────────────────────────────
export const getQueue = () => req<ScheduledEmail[]>('/scheduled-emails')

export const deleteQueueItem = (id: number) =>
  req<void>(`/scheduled-emails/${id}`, { method: 'DELETE' })

export const patchQueueItem = (id: number, data: { send_at?: string; template_id?: number }) =>
  req<{ message: string }>(`/scheduled-emails/${id}`, { method: 'PATCH', body: JSON.stringify(data) })

// ── Sent emails ────────────────────────────────────────────────────────────
export const getSentEmails = (params: {
  page?: number; per_page?: number; sort_by?: string; order?: string; status_filter?: string
}) => req<PaginatedResponse<SentEmail>>(`/sent-emails${buildQs(params)}`)

// ── Scheduler ──────────────────────────────────────────────────────────────
export const runScheduler = () => req<{ message: string }>('/run-scheduler', { method: 'POST' })
export const forceScheduler = () => req<{ message: string }>('/force-scheduler', { method: 'POST' })

// ── Test email ─────────────────────────────────────────────────────────────
export const sendTestEmail = (data: { email: string; subject: string; body: string }) =>
  req<{ message: string }>('/send-test', { method: 'POST', body: JSON.stringify(data) })

// ── Analytics breakdowns ────────────────────────────────────────────────────
export type BreakdownRow = {
  id: number
  name: string
  subject?: string
  sent: number
  opened: number
  failed: number
  open_rate: number
}

export const getAnalyticsByTemplate = () => req<BreakdownRow[]>('/analytics/by-template')
export const getAnalyticsBySequence = () => req<BreakdownRow[]>('/analytics/by-sequence')

// ── Prospect timeline ───────────────────────────────────────────────────────
export type TimelineEntry = {
  step_number: number | null
  template_name: string
  subject: string
  scheduled_at: string | null
  sent_at: string | null
  status: string
  opened_at: string | null
}

export const getProspectTimeline = (pid: number) =>
  req<TimelineEntry[]>(`/prospects/${pid}/timeline`)

// ── SMTP settings ───────────────────────────────────────────────────────────
export type SmtpSettingsData = {
  smtp_server: string
  smtp_port: number
  smtp_user: string
  smtp_password: string
  smtp_bcc: string
  source: 'env' | 'db'
}

export const getSmtpSettings = () => req<SmtpSettingsData>('/settings/smtp')

export const updateSmtpSettings = (data: Partial<SmtpSettingsData>) =>
  req<{ message: string }>('/settings/smtp', { method: 'PUT', body: JSON.stringify(data) })

// ── Error log ───────────────────────────────────────────────────────────────
export type LogEntry = {
  timestamp: string
  level: string
  logger?: string
  event: string
  [key: string]: unknown
}

export const getErrorLog  = () => req<{ entries: LogEntry[] }>('/error-log')
export const clearErrorLog = () => req<{ message: string }>('/clear-error-log', { method: 'POST' })

// ── Acquisition / review ────────────────────────────────────────────────────
export const getLeadCaptures = (params: { review_status?: string; source_type?: string }) =>
  req<LeadCapture[]>(`/lead-captures${buildQs(params)}`)

export const reviewLeadCapture = (id: number, data: { review_status: 'approved' | 'rejected'; notes?: string }) =>
  req<{ message: string; capture_id: number; review_status: string }>(`/lead-captures/${id}/review`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const getActivityEvents = (params: { source_module?: string; event_type?: string; prospect_id?: number; campaign_key?: string; limit?: number }) =>
  req<ActivityEvent[]>(`/activity-events${buildQs(params)}`)

export const getConversations = (params: { channel?: string; state?: string; campaign_key?: string; limit?: number }) =>
  req<Conversation[]>(`/conversations${buildQs(params)}`)

export const getConversationsByProspect = (prospectId: number, params: { channel?: string; state?: string; campaign_key?: string; limit?: number } = {}) =>
  req<Conversation[]>(`/conversations${buildQs({ ...params, prospect_id: prospectId })}`)

export const getActivityEventsByProspect = (prospectId: number, params: { source_module?: string; event_type?: string; campaign_key?: string; limit?: number } = {}) =>
  req<ActivityEvent[]>(`/activity-events${buildQs({ ...params, prospect_id: prospectId })}`)

export const handoffOutreachToNurture = (data: {
  prospect_id: number
  campaign_key: string
  sequence_id: number
  qualified?: boolean
  start_date?: string
  ventilate_days?: number
  notes?: string
}) => req<{ message: string; prospect_id: number; sequence_id: number; lifecycle_stage: string }>(
  '/integrations/outreach/handoffs/nurture',
  {
    method: 'POST',
    body: JSON.stringify(data),
  },
)

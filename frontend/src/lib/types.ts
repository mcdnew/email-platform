// TypeScript types mirroring FastAPI Pydantic schemas

export interface Prospect {
  id: number
  name: string
  email: string
  company: string | null
  title: string | null
  sequence_id: number | null
  sequence_name: string | null
  sequence_steps_total: number
  sequence_step_current: number
  sequence_progress_pct: number
  created_at: string
  unsubscribed: boolean
}

export interface ProspectCreate {
  name: string
  email: string
  company?: string
  title?: string
}

export interface EmailTemplate {
  id: number
  name: string
  subject: string
  body: string
  created_at: string
}

export interface Sequence {
  id: number
  name: string
  bcc_email: string | null
  created_at: string
}

export interface SequenceStep {
  id: number
  sequence_id: number
  template_id: number
  delay_days: number
  template_name?: string
}

export interface ScheduledEmail {
  id: number
  prospect_id: number
  prospect_name: string | null
  prospect_email: string | null
  template_id: number | null
  template_name: string | null
  send_at: string
  sent_at: string | null
  status: string
}

export interface SentEmail {
  id: number
  to: string
  subject: string
  body: string
  sent_at: string
  status: string
  prospect_id: number | null
  template_id: number | null
  template_name: string | null
  sequence_id: number | null
  sequence_name: string | null
  click_count: number
}

export interface AnalyticsSummary {
  total_sent: number
  total_failed: number
  open_rate: number
  sent_today: number
  recent: Array<{
    to: string
    subject: string
    status: string
    sent_at: string
    template_name: string | null
    sequence_name: string | null
  }>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface BulkImportResult {
  imported: number
  skipped: number
  errors: Array<{ email: string; error: string }>
}

// TypeScript types mirroring FastAPI Pydantic schemas

export interface Prospect {
  id: number
  name: string
  email: string
  company: string | null
  title: string | null
  sequence_id: number | null
  sequence_name: string | null
  lifecycle_stage: string | null
  sequence_steps_total: number
  sequence_step_current: number
  sequence_progress_pct: number
  created_at: string
  unsubscribed: boolean
}

export interface LeadCapture {
  id: number
  prospect_id: number | null
  source_type: string
  review_status: string
  raw_payload_json: string | null
  normalized_payload_json: string | null
  external_ref: string | null
  created_at: string
  reviewed_at: string | null
}

export interface ActivityEvent {
  id: number
  prospect_id: number | null
  sequence_id: number | null
  campaign_key: string | null
  event_type: string
  source_module: string
  payload_json: string | null
  created_at: string
}

export interface Conversation {
  id: number
  prospect_id: number
  campaign_key: string | null
  channel: string
  provider_thread_id: string | null
  state: string
  opened_at: string
  last_message_at: string | null
}

export interface AcquisitionCampaignSummary {
  campaign_key: string
  pending_review: number
  interested: number
  conversations: number
  recent_events: number
}

export interface WorkerCampaign {
  name: string
  product: string
  language: string
  discover_prompt: string
  discover_count: number
  approval_required: boolean
  active: number
  interested: number
  emails_sent: number
  running: boolean
  started: string | null
  error: string | null
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

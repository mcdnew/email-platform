'use client'

import type { ReactNode } from 'react'
import { useEffect, useMemo, useState } from 'react'

type SequenceStep = { day: string; type: string }
type ReplyActions = {
  INTERESTED: string
  QUESTION: string
  NOT_NOW: string
  UNSUBSCRIBE: string
  OTHER: string
}

type CampaignEditorState = {
  name: string
  product: string
  valueProp: string
  senderName: string
  language: string
  tone: string
  throttlePerHour: string
  personalizationLevel: string
  countryRegion: string
  industrySegment: string
  targetPersona: string
  about: string
  pricing: string
  proofPoints: string
  objections: string
  discoveryPrompt: string
  discoveryCount: string
  discoverySchedule: string
  approval: string
  sequence: SequenceStep[]
  replyActions: ReplyActions
}

type PresetKey = 'blank' | 'sawmills-na' | 'dealers-france' | 'pallet-spain' | 'pallet-europe' | 'packaging-generic'
type WizardStep = 'basics' | 'market' | 'product' | 'discovery' | 'sequence' | 'review'

const DEFAULT_SEQUENCE: SequenceStep[] = [
  { day: '0', type: 'initial' },
  { day: '4', type: 'followup' },
  { day: '9', type: 'followup' },
  { day: '16', type: 'breakup' },
]

const DEFAULT_REPLY_ACTIONS: ReplyActions = {
  INTERESTED: 'pause',
  QUESTION: 'auto_reply',
  NOT_NOW: 'auto_reply',
  UNSUBSCRIBE: 'stop',
  OTHER: 'auto_reply',
}

const WIZARD_STEPS: Array<{ key: WizardStep; label: string; description: string }> = [
  { key: 'basics', label: 'Basics', description: 'Slug, product, sender, and tone' },
  { key: 'market', label: 'Market', description: 'Country, segment, and target persona' },
  { key: 'product', label: 'Product', description: 'Knowledge base, pricing, proof, objections' },
  { key: 'discovery', label: 'Discovery', description: 'Prompt, count, approval, schedule' },
  { key: 'sequence', label: 'Sequence', description: 'Cadence and reply handling' },
  { key: 'review', label: 'Review', description: 'Validation and final config preview' },
]

const PRESET_CATALOG: Array<{ key: PresetKey; label: string; description: string }> = [
  { key: 'blank', label: 'Blank', description: 'Start from a clean generic template.' },
  { key: 'sawmills-na', label: 'Sawmills NA', description: 'North American hardwood sawmills and production facilities.' },
  { key: 'dealers-france', label: 'Dealers France', description: 'French lumber dealers, yards, and distributors.' },
  { key: 'pallet-spain', label: 'Pallet Spain', description: 'Spanish pallet makers, recyclers, and logistics yards.' },
  { key: 'pallet-europe', label: 'Pallet Europe', description: 'European pallet and industrial wood packaging operators.' },
  { key: 'packaging-generic', label: 'Packaging Generic', description: 'Generic industrial wood packaging operations.' },
]

function buildPrompt(industrySegment: string, countryRegion: string, targetPersona: string) {
  const left = [industrySegment.trim(), countryRegion.trim() ? `in ${countryRegion.trim()}` : ''].filter(Boolean).join(' ')
  const right = targetPersona.trim()
  return right ? `${left} — ${right}` : left
}

function baseState(): CampaignEditorState {
  return {
    name: '',
    product: 'TallyExpress — AI Lumber Tally App',
    valueProp: 'reduces manual tallying time dramatically with smartphone-based AI measurement',
    senderName: 'Claudiu Muntianu',
    language: 'en',
    tone: 'professional',
    throttlePerHour: '30',
    personalizationLevel: '2',
    countryRegion: '',
    industrySegment: '',
    targetPersona: '',
    about: '',
    pricing: 'Subscription-based. Contact for pricing.',
    proofPoints: '',
    objections: '',
    discoveryPrompt: '',
    discoveryCount: '10',
    discoverySchedule: '',
    approval: 'required',
    sequence: DEFAULT_SEQUENCE.map((step) => ({ ...step })),
    replyActions: { ...DEFAULT_REPLY_ACTIONS },
  }
}

function templateState(template: PresetKey): CampaignEditorState {
  const base = baseState()
  if (template === 'blank') return base
  if (template === 'sawmills-na') {
    const countryRegion = 'United States and Canada'
    const industrySegment = 'hardwood sawmills and lumber production facilities'
    const targetPersona = 'operations managers, mill managers, or production directors responsible for production efficiency'
    return {
      ...base,
      countryRegion,
      industrySegment,
      targetPersona,
      valueProp: 'reduces lumber bundle tallying from 15 minutes to 90 seconds with 99% accuracy on any Android phone',
      about: 'TallyExpress is an AI-powered lumber end-tally system for Android smartphones. Workers place a reference square on a bundle, take a photo, and the app measures every board and calculates total volume in about 90 seconds.',
      proofPoints: 'Reduces a 15-minute manual tally to 90 seconds\n98–99.5% accuracy, improving with use\nWorks on Android phones without dedicated hardware',
      objections: 'Manual tallying is slow and error-prone.\nThe app is simple to adopt because the workflow is just placing a marker and taking a photo.',
      discoveryPrompt: buildPrompt(industrySegment, countryRegion, targetPersona),
    }
  }
  if (template === 'dealers-france') {
    const countryRegion = 'France'
    const industrySegment = 'hardwood lumber dealers, wholesale distributors, and lumber yards'
    const targetPersona = 'operations directors, yard managers, or owners handling receiving and shipping'
    return {
      ...base,
      countryRegion,
      industrySegment,
      targetPersona,
      valueProp: 'eliminates bottlenecks at receiving and shipping docks by tallying any bundle in 90 seconds on a smartphone',
      about: 'TallyExpress is an AI-powered lumber end-tally system for Android smartphones. It helps receiving teams verify inbound shipments quickly and outbound teams reduce claims and disputes.',
      proofPoints: '90-second bundle tallies vs. 15-minute manual process\nCatch short-shipments before the truck leaves\nNo dedicated hardware required',
      objections: 'Receiving speed matters when trucks are waiting.\nThe app integrates with existing inventory systems instead of replacing them.',
      discoveryPrompt: buildPrompt(industrySegment, countryRegion, targetPersona),
    }
  }
  if (template === 'pallet-spain') {
    const countryRegion = 'Spain'
    const industrySegment = 'pallet manufacturers, pallet recycling companies, pallet logistics yards, and industrial wood packaging operators'
    const targetPersona = 'operations managers, plant managers, logistics managers, or yard managers responsible for production efficiency and outbound logistics'
    return {
      ...base,
      countryRegion,
      industrySegment,
      targetPersona,
      valueProp: 'reduces manual pallet-load and bundle tallying time with smartphone-based AI measurement',
      about: 'TallyExpress is an AI-powered wood bundle tally system for Android smartphones. Operators place a reference square on a pallet load, timber pack, or outbound bundle, take a photo, and the app quickly measures and records the load without fixed scanners or manual counting.',
      proofPoints: 'Reduces manual load tally time to under 90 seconds\n98–99.5% accuracy, improving with repeated use\nHelps pallet and wood-packaging yards reduce receiving and outbound bottlenecks',
      objections: 'Manual tallying slows receiving and dispatch.\nThe workflow is simple and fits smartphone-first operations.',
      discoveryPrompt: buildPrompt(industrySegment, countryRegion, targetPersona),
    }
  }
  if (template === 'pallet-europe') {
    const countryRegion = 'Western Europe'
    const industrySegment = 'pallet manufacturers, pallet recyclers, timber packaging plants, and pallet pooling operators'
    const targetPersona = 'operations managers, site managers, and logistics leaders responsible for production flow and outbound handling'
    return {
      ...base,
      countryRegion,
      industrySegment,
      targetPersona,
      valueProp: 'cuts manual pallet and timber-pack tally time using smartphone-based AI measurement',
      about: 'TallyExpress is an AI-assisted tally workflow for smartphone-based wood-pack and pallet measurement in fast-moving industrial yards and packaging plants.',
      proofPoints: 'Fast receiving and outbound checks with smartphone capture\nReduces recounts and bottlenecks across pallet flows\nNo fixed scanners or dedicated hardware',
      objections: 'Existing manual checks are inconsistent under yard pressure.\nThe tool is lightweight enough to fit existing operator workflows.',
      discoveryPrompt: buildPrompt(industrySegment, countryRegion, targetPersona),
    }
  }
  const countryRegion = 'Europe'
  const industrySegment = 'industrial wood packaging manufacturers and export packaging operators'
  const targetPersona = 'operations managers, plant managers, and packaging leads responsible for throughput and outbound quality'
  return {
    ...base,
    countryRegion,
    industrySegment,
    targetPersona,
    valueProp: 'reduces manual packaging-load tally time with smartphone-based AI measurement',
    about: 'TallyExpress helps industrial wood packaging teams measure and verify outbound bundles and loads without fixed scanning stations.',
    proofPoints: 'Works on Android phones without new fixed equipment\nImproves measurement consistency and outbound confidence\nDesigned for high-throughput packaging operations',
    objections: 'Packaging teams cannot afford slow inspection steps.\nA simple capture workflow lowers the training burden.',
    discoveryPrompt: buildPrompt(industrySegment, countryRegion, targetPersona),
  }
}

function guessPresetKey(config: Record<string, unknown> | undefined): PresetKey {
  const prompt = String(((config?.discover as Record<string, unknown> | undefined)?.prompt) ?? '').toLowerCase()
  if (prompt.includes('pallet') && prompt.includes('spain')) return 'pallet-spain'
  if (prompt.includes('pallet')) return 'pallet-europe'
  if (prompt.includes('dealer') || prompt.includes('distributor') || prompt.includes('lumber yard')) return 'dealers-france'
  if (prompt.includes('sawmill')) return 'sawmills-na'
  if (prompt.includes('packaging')) return 'packaging-generic'
  return 'blank'
}

function stateFromConfig(initialName: string | undefined, config: Record<string, unknown> | undefined): CampaignEditorState {
  if (!config) return templateState('blank')
  const campaign = (config.campaign as Record<string, unknown> | undefined) ?? {}
  const knowledge = (config.knowledge as Record<string, unknown> | undefined) ?? {}
  const discover = (config.discover as Record<string, unknown> | undefined) ?? {}
  const sequence = Array.isArray(config.sequence) ? config.sequence as Array<Record<string, unknown>> : []
  const replies = (config.replies as Record<string, unknown> | undefined) ?? {}
  const guessedPreset = templateState(guessPresetKey(config))
  return {
    ...guessedPreset,
    name: initialName ?? String(campaign.name ?? ''),
    product: String(campaign.product ?? guessedPreset.product),
    valueProp: String(campaign.value_prop ?? guessedPreset.valueProp),
    senderName: String(campaign.sender_name ?? guessedPreset.senderName),
    language: String(campaign.language ?? guessedPreset.language),
    tone: String(campaign.tone ?? guessedPreset.tone),
    throttlePerHour: String(campaign.throttle_per_hour ?? guessedPreset.throttlePerHour),
    personalizationLevel: String(campaign.personalization_level ?? guessedPreset.personalizationLevel),
    targetPersona: String(knowledge.target_persona ?? guessedPreset.targetPersona),
    about: String(knowledge.about ?? guessedPreset.about),
    pricing: String(knowledge.pricing ?? guessedPreset.pricing),
    proofPoints: Array.isArray(knowledge.proof_points) ? (knowledge.proof_points as string[]).join('\n') : guessedPreset.proofPoints,
    objections: String(knowledge.objections ?? guessedPreset.objections),
    discoveryPrompt: String(discover.prompt ?? guessedPreset.discoveryPrompt),
    discoveryCount: String(discover.count ?? guessedPreset.discoveryCount),
    discoverySchedule: String(discover.schedule ?? guessedPreset.discoverySchedule),
    approval: String(discover.approval ?? guessedPreset.approval),
    sequence: sequence.length ? sequence.map((step) => ({ day: String(step.day ?? 0), type: String(step.type ?? 'followup') })) : guessedPreset.sequence.map((step) => ({ ...step })),
    replyActions: {
      INTERESTED: String(replies.INTERESTED ?? guessedPreset.replyActions.INTERESTED),
      QUESTION: String(replies.QUESTION ?? guessedPreset.replyActions.QUESTION),
      NOT_NOW: String(replies.NOT_NOW ?? guessedPreset.replyActions.NOT_NOW),
      UNSUBSCRIBE: String(replies.UNSUBSCRIBE ?? guessedPreset.replyActions.UNSUBSCRIBE),
      OTHER: String(replies.OTHER ?? guessedPreset.replyActions.OTHER),
    },
  }
}

export function buildCampaignConfig(state: CampaignEditorState): Record<string, unknown> {
  return {
    campaign: {
      name: state.name,
      product: state.product.trim(),
      value_prop: state.valueProp.trim(),
      sender_name: state.senderName.trim(),
      tone: state.tone.trim(),
      language: state.language.trim().toLowerCase(),
      personalization_level: Number(state.personalizationLevel) || 2,
      throttle_per_hour: Number(state.throttlePerHour) || 30,
    },
    knowledge: {
      about: state.about.trim(),
      target_persona: state.targetPersona.trim(),
      pricing: state.pricing.trim(),
      proof_points: state.proofPoints.split('\n').map((line) => line.trim()).filter(Boolean),
      objections: state.objections.trim(),
    },
    discover: {
      prompt: (state.discoveryPrompt || buildPrompt(state.industrySegment, state.countryRegion, state.targetPersona)).trim(),
      count: Number(state.discoveryCount) || 10,
      schedule: state.discoverySchedule.trim(),
      approval: state.approval.trim(),
    },
    sequence: state.sequence.map((step) => ({
      day: Number(step.day) || 0,
      type: step.type.trim(),
    })),
    replies: { ...state.replyActions },
  }
}

function validateCampaignState(state: CampaignEditorState) {
  const errors: string[] = []
  if (!/^[a-z0-9-]+$/.test(state.name.trim())) errors.push('Campaign slug must use lowercase letters, numbers, and hyphens only.')
  if (!state.product.trim()) errors.push('Product is required.')
  if (!state.valueProp.trim()) errors.push('Value proposition is required.')
  if (!state.senderName.trim()) errors.push('Sender name is required.')
  if (!state.language.trim()) errors.push('Language is required.')
  if (!state.countryRegion.trim()) errors.push('Country / region is required.')
  if (!state.industrySegment.trim()) errors.push('Industry segment is required.')
  if (!state.targetPersona.trim()) errors.push('Target persona is required.')
  if (!state.about.trim()) errors.push('About the product is required.')
  if (!state.pricing.trim()) errors.push('Pricing is required.')
  if (!state.proofPoints.split('\n').map((line) => line.trim()).filter(Boolean).length) errors.push('At least one proof point is required.')
  if (!state.objections.trim()) errors.push('Objections guidance is required.')
  if (!state.discoveryPrompt.trim()) errors.push('Discovery prompt is required.')
  const discoverCount = Number(state.discoveryCount)
  if (!Number.isFinite(discoverCount) || discoverCount < 1 || discoverCount > 50) errors.push('Discover count must be between 1 and 50.')
  const throttle = Number(state.throttlePerHour)
  if (!Number.isFinite(throttle) || throttle < 1 || throttle > 500) errors.push('Throttle per hour must be between 1 and 500.')
  const personalization = Number(state.personalizationLevel)
  if (!Number.isFinite(personalization) || personalization < 0 || personalization > 5) errors.push('Personalization level must be between 0 and 5.')
  if (!state.sequence.length) errors.push('At least one sequence step is required.')
  state.sequence.forEach((step, index) => {
    const day = Number(step.day)
    if (!Number.isFinite(day) || day < 0) errors.push(`Sequence step ${index + 1} needs a day of 0 or greater.`)
    if (!step.type.trim()) errors.push(`Sequence step ${index + 1} needs a type.`)
  })
  ;(Object.keys(state.replyActions) as Array<keyof ReplyActions>).forEach((key) => {
    if (!state.replyActions[key].trim()) errors.push(`Reply action for ${key} is required.`)
  })
  return errors
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <section className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-950/40 p-4 space-y-3">
      <div>
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">{title}</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{description}</p>
      </div>
      {children}
    </section>
  )
}

export function WorkerCampaignEditor({
  initialName,
  initialConfig,
  saving,
  mode,
  onSave,
}: {
  initialName?: string
  initialConfig?: Record<string, unknown>
  saving?: boolean
  mode: 'create' | 'edit'
  onSave: (payload: { name: string; config: Record<string, unknown> }) => void
}) {
  const [state, setState] = useState<CampaignEditorState>(stateFromConfig(initialName, initialConfig))
  const [wizardStep, setWizardStep] = useState<WizardStep>('basics')
  const errors = useMemo(() => validateCampaignState(state), [state])
  const configPreview = useMemo(() => JSON.stringify(buildCampaignConfig(state), null, 2), [state])

  useEffect(() => {
    setState(stateFromConfig(initialName, initialConfig))
  }, [initialName, initialConfig])

  function applyTemplate(template: PresetKey) {
    const next = templateState(template)
    setState((current) => ({
      ...next,
      name: current.name,
      senderName: current.senderName || next.senderName,
    }))
  }

  function updateSequence(index: number, key: 'day' | 'type', value: string) {
    setState((current) => ({
      ...current,
      sequence: current.sequence.map((step, stepIndex) => stepIndex === index ? { ...step, [key]: value } : step),
    }))
  }

  function updateReplyAction(key: keyof ReplyActions, value: string) {
    setState((current) => ({
      ...current,
      replyActions: { ...current.replyActions, [key]: value },
    }))
  }

  function goStep(direction: -1 | 1) {
    const currentIndex = WIZARD_STEPS.findIndex((step) => step.key === wizardStep)
    const nextIndex = Math.max(0, Math.min(WIZARD_STEPS.length - 1, currentIndex + direction))
    setWizardStep(WIZARD_STEPS[nextIndex].key)
  }

  return (
    <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {mode === 'create' ? 'New Campaign Wizard' : 'Structured Campaign Editor'}
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Build campaigns from validated fields, presets, and guided steps instead of hand-editing copied YAML.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {PRESET_CATALOG.map((preset) => (
            <button
              key={preset.key}
              type="button"
              onClick={() => applyTemplate(preset.key)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-left text-xs hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-950 dark:hover:bg-gray-900"
            >
              <div className="font-medium text-gray-900 dark:text-gray-100">{preset.label}</div>
              <div className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">{preset.description}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2">
        {WIZARD_STEPS.map((step) => (
          <button
            key={step.key}
            type="button"
            onClick={() => setWizardStep(step.key)}
            className={`rounded-lg px-3 py-2 text-left ${wizardStep === step.key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200'}`}
          >
            <div className="text-xs font-medium">{step.label}</div>
            <div className={`mt-1 text-[11px] ${wizardStep === step.key ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'}`}>{step.description}</div>
          </button>
        ))}
      </div>

      {!!errors.length && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          <div className="font-medium">Validation</div>
          <ul className="mt-2 list-disc pl-5 space-y-1 text-xs">
            {errors.map((error) => <li key={error}>{error}</li>)}
          </ul>
        </div>
      )}

      {wizardStep === 'basics' && (
        <SectionCard title="Campaign identity" description="Define the slug, product positioning, sender identity, and tone.">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            {[
              ['name', 'Campaign slug'],
              ['product', 'Product'],
              ['valueProp', 'Value proposition'],
              ['senderName', 'Sender name'],
              ['language', 'Language'],
              ['tone', 'Tone'],
              ['throttlePerHour', 'Throttle / hour'],
              ['personalizationLevel', 'Personalization'],
            ].map(([key, label]) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
                <input
                  value={state[key as keyof CampaignEditorState] as string}
                  onChange={(event) => setState((current) => ({ ...current, [key]: event.target.value }))}
                  disabled={mode === 'edit' && key === 'name'}
                  className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                />
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {wizardStep === 'market' && (
        <SectionCard title="Market definition" description="Describe where to search and what type of operators you want to reach.">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              ['countryRegion', 'Country / region'],
              ['industrySegment', 'Industry segment'],
              ['targetPersona', 'Target persona'],
            ].map(([key, label]) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
                <textarea
                  value={state[key as keyof CampaignEditorState] as string}
                  onChange={(event) => setState((current) => ({ ...current, [key]: event.target.value }))}
                  rows={4}
                  className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                />
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {wizardStep === 'product' && (
        <SectionCard title="Product knowledge base" description="Provide the knowledge and sales framing the worker will use in discovery and outreach.">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">About the product</label>
              <textarea value={state.about} onChange={(event) => setState((current) => ({ ...current, about: event.target.value }))} rows={7} className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Pricing</label>
              <textarea value={state.pricing} onChange={(event) => setState((current) => ({ ...current, pricing: event.target.value }))} rows={7} className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Proof points</label>
              <textarea value={state.proofPoints} onChange={(event) => setState((current) => ({ ...current, proofPoints: event.target.value }))} rows={7} className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Objections</label>
              <textarea value={state.objections} onChange={(event) => setState((current) => ({ ...current, objections: event.target.value }))} rows={7} className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" />
            </div>
          </div>
        </SectionCard>
      )}

      {wizardStep === 'discovery' && (
        <SectionCard title="Discovery setup" description="Define how the worker should search, how many results to ask for, and whether review is required.">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Discovery prompt</label>
              <textarea value={state.discoveryPrompt} onChange={(event) => setState((current) => ({ ...current, discoveryPrompt: event.target.value }))} rows={6} className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" />
              <button
                type="button"
                onClick={() => setState((current) => ({ ...current, discoveryPrompt: buildPrompt(current.industrySegment, current.countryRegion, current.targetPersona) }))}
                className="mt-2 px-2.5 py-1.5 text-xs rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
              >
                Regenerate from fields
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Discover count</label>
                <input value={state.discoveryCount} onChange={(event) => setState((current) => ({ ...current, discoveryCount: event.target.value }))} className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Approval mode</label>
                <select value={state.approval} onChange={(event) => setState((current) => ({ ...current, approval: event.target.value }))} className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100">
                  <option value="required">required</option>
                  <option value="auto">auto</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Discovery schedule</label>
                <input value={state.discoverySchedule} onChange={(event) => setState((current) => ({ ...current, discoverySchedule: event.target.value }))} className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" placeholder="weekly / cron / blank for manual" />
              </div>
            </div>
          </div>
        </SectionCard>
      )}

      {wizardStep === 'sequence' && (
        <SectionCard title="Sequence and reply handling" description="Review the cadence and default handling actions for each reply intent.">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div>
              <h3 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">Sequence</h3>
              <div className="space-y-2">
                {state.sequence.map((step, index) => (
                  <div key={`${index}-${step.type}`} className="grid grid-cols-2 gap-2">
                    <input value={step.day} onChange={(event) => updateSequence(index, 'day', event.target.value)} className="rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" placeholder="day" />
                    <input value={step.type} onChange={(event) => updateSequence(index, 'type', event.target.value)} className="rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" placeholder="type" />
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">Reply actions</h3>
              <div className="space-y-2">
                {(Object.keys(state.replyActions) as Array<keyof ReplyActions>).map((key) => (
                  <div key={key} className="grid grid-cols-2 gap-2 items-center">
                    <span className="text-xs text-gray-700 dark:text-gray-300">{key}</span>
                    <input value={state.replyActions[key]} onChange={(event) => updateReplyAction(key, event.target.value)} className="rounded-md border border-gray-300 bg-white px-2.5 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </SectionCard>
      )}

      {wizardStep === 'review' && (
        <SectionCard title="Review and final config" description="Confirm the generated config before saving. The backend will validate and normalize it again.">
          <pre className="w-full min-h-[320px] rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-mono text-gray-900 whitespace-pre-wrap dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100">
            {configPreview}
          </pre>
        </SectionCard>
      )}

      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => goStep(-1)}
          disabled={wizardStep === 'basics'}
          className="px-4 py-2 text-sm rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 disabled:opacity-50 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
        >
          Previous
        </button>
        <div className="flex items-center gap-3">
          {wizardStep !== 'review' && (
            <button
              type="button"
              onClick={() => goStep(1)}
              className="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700"
            >
              Next
            </button>
          )}
          <button
            type="button"
            onClick={() => onSave({ name: state.name.trim().toLowerCase(), config: buildCampaignConfig(state) })}
            disabled={saving || errors.length > 0}
            className="px-4 py-2 text-sm rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {mode === 'create' ? 'Create campaign' : 'Save structured config'}
          </button>
        </div>
      </div>
    </section>
  )
}

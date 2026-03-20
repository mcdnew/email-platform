import { describe, it, expect } from 'vitest'

function renderPreview(body: string): string {
  return body.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    const samples: Record<string, string> = { name: 'Alice', email: 'alice@example.com', company: 'Acme Corp', title: 'CEO' }
    return samples[key] ?? `{{${key}}}`
  })
}

describe('Template preview rendering', () => {
  it('substitutes known variables', () => {
    expect(renderPreview('Hi {{name}}, welcome to {{company}}'))
      .toBe('Hi Alice, welcome to Acme Corp')
  })

  it('leaves unknown variables unchanged', () => {
    expect(renderPreview('Hello {{unknown}}')).toBe('Hello {{unknown}}')
  })

  it('handles body with no variables', () => {
    expect(renderPreview('Plain text body')).toBe('Plain text body')
  })

  it('substitutes email variable', () => {
    expect(renderPreview('Reply to {{email}}')).toBe('Reply to alice@example.com')
  })

  it('substitutes multiple occurrences', () => {
    expect(renderPreview('{{name}} and {{name}}')).toBe('Alice and Alice')
  })
})

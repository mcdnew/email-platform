import { describe, it, expect } from 'vitest'

function renderPreview(body: string): string {
  return body.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    const samples: Record<string, string> = { name: 'Alice', email: 'alice@example.com', company: 'Acme Corp', title: 'CEO' }
    return samples[key] ?? `{{${key}}}`
  })
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
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

  it('substitutes variables inside HTML tags', () => {
    expect(renderPreview('<p>Hi {{name}}, welcome to {{company}}!</p>'))
      .toBe('<p>Hi Alice, welcome to Acme Corp!</p>')
  })
})

describe('stripHtml', () => {
  it('strips simple tags', () => {
    expect(stripHtml('<p>Hello world</p>')).toBe('Hello world')
  })

  it('strips nested tags', () => {
    expect(stripHtml('<h2>Subject</h2><p>Body <strong>text</strong></p>')).toBe('Subject Body text')
  })

  it('collapses multiple spaces', () => {
    expect(stripHtml('<p>  foo  </p><p>  bar  </p>')).toBe('foo bar')
  })

  it('returns empty string for empty input', () => {
    expect(stripHtml('')).toBe('')
  })

  it('returns plain text unchanged', () => {
    expect(stripHtml('No tags here')).toBe('No tags here')
  })
})

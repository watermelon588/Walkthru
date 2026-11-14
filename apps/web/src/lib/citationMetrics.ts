import type { CitationAnswer, CitationBrand } from './runs'

// A matched name is text, not proof it is this business; answers saved before identity was checked count as unconfirmed.
export const identity = (b?: CitationBrand) => b?.entity_status ?? (b?.mentioned ? 'ambiguous' : 'absent')

export function citationMetrics(answers: CitationAnswer[]) {
  const done = answers.filter((a) => a.status === 'done')
  const you = (a: CitationAnswer) => a.result?.brands?.find((b) => b.you)
  const eligible = done.filter((a) => a.result?.measurement_version === 2 && a.result.citation_eligible === true && you(a)?.cited != null)
  const brands = new Map<string, { name: string; you: boolean; mentions: number; share: number }>()
  for (const a of done) for (const b of a.result?.brands ?? []) {
    const key = `${b.you}:${b.domain}:${b.name}`
    const row = brands.get(key) ?? { name: b.name, you: b.you, mentions: 0, share: 0 }
    row.mentions += Number(b.mentioned)
    brands.set(key, row)
  }
  const total = [...brands.values()].reduce((sum, b) => sum + b.mentions, 0)
  const voice = [...brands.values()].map((b) => ({ ...b, share: total ? Math.round(100 * b.mentions / total) : 0 }))
    .sort((a, b) => b.mentions - a.mentions)
  const count = (status: string) => done.filter((a) => identity(you(a)) === status).length
  // Citation slots: answers that searched the web, plus failed checks on that surface. Unknown never becomes a miss.
  const searched = done.filter((a) => a.result?.citation_status !== 'not_applicable').length
  const citationSlots = searched ? searched + answers.filter((a) => a.status === 'failed').length : 0
  const cited = eligible.filter((a) => you(a)?.cited).length
  const unknown = citationSlots - eligible.length
  const pct = (n: number) => Math.round(100 * n / citationSlots)
  return { done, identified: count('verified'), nameOnly: count('ambiguous'), otherEntity: count('other'), cited,
    citationAnswers: eligible.length, citationSlots, unknown, bounds: citationSlots ? [pct(cited), pct(cited + unknown)] : null,
    voice, hasMentions: total > 0 }
}

export function citationLabel(answer: CitationAnswer) {
  return answer.result?.provenance?.label ?? (answer.engine === 'web' ? 'Groq web search (legacy)' : 'Gemini (historical mode unknown)')
}

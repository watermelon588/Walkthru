// Same bands as the badge (app/agent/score.py `band`).
export function band(score: number): { label: string; tone: string } {
  if (score >= 85) return { label: 'Launch ready', tone: 'text-accent' }
  if (score >= 60) return { label: 'Almost ready', tone: 'text-ink' }
  return { label: 'Needs work', tone: 'text-danger' }
}

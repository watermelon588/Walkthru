import { useState } from 'react'
import { copyText } from '../lib/clipboard'
import { getFixPrompt } from '../lib/runs'

/** One Markdown prompt for the owner's coding agent (paid plans). Built by the API on request, never stored in the report. */
export function FixPrompt({ runId, paid, count }: { runId: string; paid: boolean; count: number }) {
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function act(label: string, work: () => Promise<void>) {
    setBusy(true)
    setStatus(null)
    try {
      await work()
      setStatus(label)
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'That did not work. Try again.')
    } finally {
      setBusy(false)
    }
  }

  const copy = (style: 'full' | 'chat', label: string) => act(label, async () => {
    if (!(await copyText(await getFixPrompt(runId, style)))) throw new Error('Could not copy. Use Download instead.')
  })
  const download = () => act('Downloaded walkthru-fixes.md', async () => {
    const url = URL.createObjectURL(new Blob([await getFixPrompt(runId, 'full')], { type: 'text/markdown' }))
    const a = Object.assign(document.createElement('a'), { href: url, download: 'walkthru-fixes.md' })
    a.click()
    URL.revokeObjectURL(url)
  })
  const button = 'rounded-full border border-line px-4 py-2 text-sm transition hover:border-ink disabled:opacity-50'

  return (
    <section aria-labelledby="fix-prompt-title" className="no-print mt-12 rounded-2xl border border-line px-5 py-5">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Fix it with your coding agent</p>
      <h2 id="fix-prompt-title" className="mt-2 text-xl font-light tracking-tight">One prompt for all {count} fixes</h2>
      <p className="mt-2 max-w-[62ch] text-sm leading-relaxed text-muted">
        {paid
          ? 'Paste it into Claude Code, Cursor or Codex, or save the file into your project. Lovable and Bolt get a shorter chat version. Ignored findings are left out; secrets are never included.'
          : 'Pro builds one Markdown prompt from this report for Claude Code, Cursor, Lovable or Bolt, with every fix in order and a check for each. Rerun afterwards to see what was fixed.'}
      </p>
      {paid ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" className={button} disabled={busy} onClick={() => copy('full', 'Copied. Paste it into your coding agent.')}>Copy prompt</button>
          <button type="button" className={button} disabled={busy} onClick={download}>Download walkthru-fixes.md</button>
          <button type="button" className={button} disabled={busy} onClick={() => copy('chat', 'Copied the short version for Lovable or Bolt.')}>Copy chat version</button>
        </div>
      ) : (
        <p className="mt-4 text-sm"><a href="/#pricing" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">See Pro</a></p>
      )}
      {status && <p role="status" className="mt-3 text-xs text-muted">{status}</p>}
    </section>
  )
}

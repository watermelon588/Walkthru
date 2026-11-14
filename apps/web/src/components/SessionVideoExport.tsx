import { FilmStripIcon } from '@phosphor-icons/react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { brand } from '../brand'
import { momentPaths, moments } from '../lib/live'
import { evidenceUrls, getPlan, type Step } from '../lib/runs'
import { recordSession, storyboard, videoName } from '../lib/sessionVideo'
import { btnGhost } from './Shared'

type State =
  | { kind: 'hidden' } // not signed in (a shared report): no export
  | { kind: 'locked' }
  | { kind: 'ready' }
  | { kind: 'recording'; done: number; total: number }
  | { kind: 'saved'; file: string }
  | { kind: 'error'; message: string }

const token = (name: string, fallback: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

/** Plus: save one test user's visit as a video file with watermark badges (lib/sessionVideo.ts). The video is made
 *  in this browser from the frames already on the page; nothing is uploaded. It records in real time. */
export function SessionVideoExport({ steps, runId, name, site, owner }: { steps: Step[]; runId: string; name: string; site: string; owner?: string }) {
  const [state, setState] = useState<State>({ kind: 'hidden' })
  const stop = useRef<AbortController | null>(null)
  const list = useMemo(() => moments(steps, runId), [steps, runId])
  const seconds = Math.round(storyboard(list).total / 1000)

  useEffect(() => {
    let live = true
    getPlan().then((plan) => { if (live) setState({ kind: plan.plan === 'plus' ? 'ready' : 'locked' }) }).catch(() => undefined)
    return () => { live = false; stop.current?.abort() }
  }, [])

  async function record() {
    const control = new AbortController()
    stop.current = control
    setState({ kind: 'recording', done: 0, total: seconds * 1000 })
    try {
      const urls = await evidenceUrls(momentPaths(list))
      const { blob, ext } = await recordSession({
        list, urls, name, site, signal: control.signal,
        watermark: { mark: brand.mark, name: `Tested with ${brand.name}`, owner },
        colors: { bg: token('--bg', '#f4f4f5'), ink: token('--ink', '#1b1b1f'), muted: token('--muted', '#63636b'), line: token('--line', '#dedee2'), surface: token('--surface', '#e9e9eb'), danger: token('--danger', '#a33b3b') },
        onProgress: (done, total) => setState((now) => (now.kind === 'recording' ? { kind: 'recording', done, total } : now)),
      })
      const file = videoName(site, name, ext)
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = file
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(link.href), 10_000)
      setState({ kind: 'saved', file })
    } catch (error) {
      if ((error as Error).name === 'AbortError') return setState({ kind: 'ready' })
      setState({ kind: 'error', message: (error as Error).message || 'The video could not be made.' })
    }
  }

  if (state.kind === 'hidden' || list.length === 0) return null
  if (state.kind === 'locked') {
    return <p className="mt-4 text-sm text-muted">Saving this visit as a video is part of the Plus plan. <Link to="/app/billing" className="text-ink underline underline-offset-4">See plans</Link></p>
  }
  const recording = state.kind === 'recording'
  return (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      {recording ? (
        <button type="button" onClick={() => stop.current?.abort()} className={btnGhost}>Cancel export</button>
      ) : (
        <button type="button" onClick={record} className={btnGhost}><FilmStripIcon weight="light" className="size-4" /> Export video</button>
      )}
      <p role="status" className={`text-xs ${state.kind === 'error' ? 'text-danger' : 'text-muted'}`}>
        {recording ? `Recording, ${Math.max(0, Math.ceil((state.total - state.done) / 1000))} seconds left. Keep this tab open and in front.`
          : state.kind === 'saved' ? `Saved ${state.file}.`
          : state.kind === 'error' ? state.message
          : `Video of ${name}'s visit with a ${brand.name} badge, about ${seconds} seconds. It records at normal speed.`}
      </p>
    </div>
  )
}

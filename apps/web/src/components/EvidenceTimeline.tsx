import { CameraIcon, CaretLeftIcon, CaretRightIcon, PauseIcon, PlayIcon } from '@phosphor-icons/react'
import { useEffect, useMemo, useState } from 'react'
import { evidenceUrls, type Step } from '../lib/runs'
import { AgentBird } from './AgentBird'
import { AgentPresence } from './AgentPresence'
import { BrowserDiagnostics, BrowserDiagnosticsSummary } from './BrowserDiagnostics'

const ACTION_LABEL: Record<Step['action'], string> = {
  click: 'Clicked',
  type: 'Filled field',
  scroll: 'Scrolled',
  wait: 'Waited for page',
  back: 'Went back',
  done: 'Goal reached',
  give_up: 'Stopped',
}

function actionLabel(step: Step) {
  if (step.executor_result?.action === step.action) {
    const outcome = step.executor_result.status
    if (outcome === 'aborted') return step.action === 'wait' ? 'Wait interrupted' : 'Scroll interrupted'
    if (!step.interrupted) {
      if (outcome === 'timeout') return 'Wait timed out'
      if (outcome === 'no_progress') return 'Scroll did not move'
    }
  }
  if (!step.interrupted) return ACTION_LABEL[step.action]
  return ({ click: 'Click not confirmed', type: 'Field entry not confirmed', scroll: 'Scroll not confirmed', wait: 'Wait not confirmed', back: 'Back navigation not confirmed', done: 'Completion not confirmed', give_up: 'Stop not confirmed' })[step.action]
}

export function EvidenceTimeline({ steps, branded = false }: { steps: Step[]; branded?: boolean }) {
  const [selected, setSelected] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [imageResult, setImageResult] = useState<{ key: string; urls: Record<string, string> }>({ key: '', urls: {} })
  const [failedImages, setFailedImages] = useState<Set<string>>(() => new Set())
  const paths = useMemo(() => steps.flatMap((step) => step.evidence?.screenshot_path ?? []), [steps])
  const pathsKey = paths.join('|')
  const images = imageResult.key === pathsKey ? imageResult.urls : {}
  const current = steps[selected]

  useEffect(() => {
    let active = true
    if (paths.length === 0) return () => { active = false }
    evidenceUrls(paths).then((urls) => {
      if (!active) return
      setImageResult({ key: pathsKey, urls })
    })
    return () => { active = false }
  }, [paths, pathsKey])

  useEffect(() => {
    if (!playing || steps.length < 2) return
    const timer = window.setInterval(() => {
      setSelected((index) => {
        if (index >= steps.length - 1) {
          setPlaying(false)
          return index
        }
        return index + 1
      })
    }, 1800)
    return () => window.clearInterval(timer)
  }, [playing, steps.length])

  if (!current) return null
  const evidence = current.evidence
  const screenshot = evidence ? images[evidence.screenshot_path] : undefined
  const imageState = evidence ? imageResult.key === pathsKey ? 'ready' : 'loading' : 'idle'

  function move(delta: number) {
    setPlaying(false)
    setSelected((index) => Math.min(steps.length - 1, Math.max(0, index + delta)))
  }

  return (
    <>
    <section aria-labelledby="journey-evidence-title" className="no-print mt-14">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Journey replay</p>
          <h2 id="journey-evidence-title" className="mt-2 text-2xl font-light tracking-tight">See every meaningful moment</h2>
          <p className="mt-2 max-w-[58ch] text-sm leading-relaxed text-muted">Select a step to inspect what Scout tried, the captured page and where confusion rose. Interrupted actions have no confirmed result.</p>
        </div>
        <AgentPresence
          activity={`Reviewing step ${selected + 1} of ${steps.length}`}
          state={evidence ? 'complete' : 'observing'}
          phase={0.46}
        />
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-line bg-line">
        <div className="grid gap-px lg:grid-cols-[17rem_minmax(0,1fr)_18rem]">
          <ol aria-label="Journey steps" className="max-h-[38rem] overflow-y-auto bg-bg p-2">
            {steps.map((step, index) => (
              <li key={`${step.action}-${index}`}>
                <button
                  type="button"
                  onClick={() => { setSelected(index); setPlaying(false) }}
                  aria-current={selected === index ? 'step' : undefined}
                  className={`grid w-full grid-cols-[2rem_1fr_auto] items-start gap-2 rounded-xl px-3 py-3 text-left transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-accent ${selected === index ? 'bg-surface' : 'hover:bg-surface/60'}`}
                >
                  <span className="pt-0.5 font-mono text-xs text-muted">{String(index + 1).padStart(2, '0')}</span>
                  <span className="min-w-0">
                    <span className="block text-sm">{actionLabel(step)}</span>
                    <span className="mt-1 block truncate font-mono text-[10px] text-muted">{step.url}</span>
                  </span>
                  {step.evidence && <CameraIcon aria-label="Screenshot saved" className="mt-0.5 size-4 text-accent" />}
                </button>
              </li>
            ))}
          </ol>

          <div className="bg-bg p-3 sm:p-5">
            <figure className="overflow-hidden rounded-xl border border-line bg-surface">
              <div className="flex aspect-[16/10] items-center justify-center">
                {screenshot && !failedImages.has(evidence?.screenshot_path ?? '') ? (
                  <img
                    src={screenshot}
                    alt={`Captured page for step ${selected + 1}: ${actionLabel(current)}`}
                    className="h-full w-full object-contain"
                    loading="lazy"
                    decoding="async"
                    onError={() => evidence && setFailedImages((paths) => new Set(paths).add(evidence.screenshot_path))}
                  />
                ) : (
                  <div className="max-w-[34ch] px-6 text-center">
                    <CameraIcon className="mx-auto size-7 text-muted" weight="light" />
                    <p className="mt-3 text-sm">{evidence && imageState === 'loading' ? 'Loading evidence' : evidence ? 'Screenshot unavailable' : 'No screenshot for this step'}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted">
                      {evidence
                        ? imageState === 'loading'
                          ? 'Requesting a short-lived private link.'
                          : 'The capture expired or could not be loaded. The step details are still available.'
                        : 'Visual evidence appears on new runs made with the updated extension. Older runs keep their complete think-aloud history.'}
                    </p>
                  </div>
                )}
              </div>
              <figcaption className="flex flex-wrap items-center justify-between gap-2 border-t border-line bg-bg px-3 py-2 text-[11px] text-muted">
                <span>{evidence ? new Date(evidence.captured_at).toLocaleString() : `Step ${selected + 1}`}</span>
                {evidence && <span>{evidence.width} × {evidence.height}</span>}
              </figcaption>
            </figure>

            <div className="mt-3 flex items-center justify-center gap-2" aria-label="Replay controls">
              <Control label="Previous step" onClick={() => move(-1)} disabled={selected === 0}><CaretLeftIcon /></Control>
              <Control label={playing ? 'Pause replay' : 'Play replay'} onClick={() => setPlaying((value) => !value)} disabled={steps.length < 2}>
                {playing ? <PauseIcon weight="fill" /> : <PlayIcon weight="fill" />}
              </Control>
              <Control label="Next step" onClick={() => move(1)} disabled={selected === steps.length - 1}><CaretRightIcon /></Control>
            </div>
          </div>

          <aside aria-label={`Details for step ${selected + 1}`} className="bg-bg p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Step {selected + 1}</p>
            <p className="mt-3 leading-relaxed">{current.thought}</p>
            <dl className="mt-6 grid gap-4 border-t border-line pt-4 text-sm">
              <Detail term="Action" value={`${actionLabel(current)}${current.target_id != null ? ` · element ${current.target_id}` : ''}`} />
              <Detail term={current.interrupted || !evidence ? 'Recorded page' : 'Result page'} value={current.interrupted ? current.url : evidence?.result_url ?? current.url} mono />
              <Detail term="Confusion" value={`${current.confusion} of 3`} />
              {current.provider && <Detail term="Decision" value={`${current.provider}${current.decision_confidence != null ? ` · ${Math.round(current.decision_confidence * 100)}% confidence` : ''}`} />}
              {current.fallback_reason && <Detail term="Fallback" value={current.fallback_reason} />}
              {evidence?.note && <Detail term="Executor note" value={evidence.note} />}
              {current.interrupted && <Detail term="Result" value="Run ended before this action was confirmed." />}
            </dl>
            {current.diagnostics && <BrowserDiagnostics diagnostics={current.diagnostics} />}
            <div className="mt-5 flex gap-1" aria-label={`Confusion ${current.confusion} of 3`}>
              {[0, 1, 2].map((level) => <span key={level} className={`h-1.5 flex-1 rounded-full ${level < current.confusion ? 'bg-danger' : 'bg-line'}`} />)}
            </div>
          </aside>
        </div>
      </div>
    </section>
    <PrintEvidenceJourney steps={steps} images={images} branded={branded} />
    </>
  )
}

function PrintEvidenceJourney({ steps, images, branded }: { steps: Step[]; images: Record<string, string>; branded: boolean }) {
  const frames = steps
    .map((step, index) => ({ step, index, evidence: step.evidence }))
    .filter((item): item is { step: Step; index: number; evidence: NonNullable<Step['evidence']> } => Boolean(item.evidence))

  return (
    <section aria-label="Visual journey evidence" className="print-only report-print-section print-break-before">
      <header className="report-print-section-heading">
        <div>
          <p className="report-print-kicker">Visual evidence</p>
          <h2>{branded ? 'What the test user saw' : 'What Scout saw'}</h2>
          <p>Frames show the captured page for each recorded step. Interrupted actions have no confirmed result. Form values were masked before capture.</p>
        </div>
        {!branded && <AgentBird variant="solid" className="report-print-bird" phase={0.4} title="Scout, the Walkthru test agent" />}
      </header>

      {frames.length === 0 ? (
        <p className="report-print-empty">No screenshot evidence was saved for this run.</p>
      ) : (
        <div className="report-print-frames">
          {frames.map(({ step, index, evidence }) => {
            const image = images[evidence.screenshot_path]
            return (
              <figure key={evidence.screenshot_path} className="report-print-frame">
                {image ? (
                  <img src={image} alt={`Captured page for step ${index + 1}: ${actionLabel(step)}`} loading="eager" />
                ) : (
                  <div className="report-print-frame-missing">Screenshot unavailable</div>
                )}
                <figcaption>
                  <span className="report-print-step">{String(index + 1).padStart(2, '0')}</span>
                  <span>
                    <strong>{actionLabel(step)}</strong>
                    <span>{step.thought}</span>
                  </span>
                  <span className="report-print-confusion">
                    Confusion {step.confusion}/3{step.diagnostics && <> · <BrowserDiagnosticsSummary diagnostics={step.diagnostics} /></>}
                  </span>
                </figcaption>
              </figure>
            )
          })}
        </div>
      )}
    </section>
  )
}

function Control({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled: boolean; children: React.ReactNode }) {
  return (
    <button type="button" aria-label={label} onClick={onClick} disabled={disabled} className="grid size-9 place-items-center rounded-full border border-line transition-colors duration-150 hover:bg-surface disabled:cursor-default disabled:opacity-35">
      {children}
    </button>
  )
}

function Detail({ term, value, mono = false }: { term: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-muted">{term}</dt>
      <dd className={`mt-1 break-words ${mono ? 'font-mono text-xs' : ''}`}>{value}</dd>
    </div>
  )
}

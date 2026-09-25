import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link } from 'react-router'
import { deleteBranding, getBranding, getPlan, saveBranding, type Brand } from '../lib/runs'
import { btnGhost, btnPrimary } from './Shared'

type State = { kind: 'loading' } | { kind: 'locked' } | { kind: 'ready' } | { kind: 'error'; message: string }
type Save = { kind: 'idle' } | { kind: 'saving' } | { kind: 'saved' } | { kind: 'error'; message: string }

const EMPTY: Brand = { name: '', color: '#1b1b1f', footer: '', logo: null }
const LOGO_BYTES = 200_000
const LOGO_TYPES = ['image/png', 'image/jpeg', 'image/webp']
const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'
const label = 'grid gap-2 text-sm text-muted'

/** Plus: the owner's name, logo and color on printed reports, in place of Walkthru's (P4.3). */
export function ReportBranding() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [brand, setBrand] = useState<Brand>(EMPTY)
  const [saved, setSaved] = useState(false)
  const [save, setSave] = useState<Save>({ kind: 'idle' })

  const load = () =>
    getPlan()
      .then(async (plan) => {
        if (plan.plan !== 'plus') return setState({ kind: 'locked' })
        const current = await getBranding()
        setBrand(current.brand ?? EMPTY)
        setSaved(!!current.brand)
        setState({ kind: 'ready' })
      })
      .catch((e: Error) => setState({ kind: 'error', message: e.message }))
  useEffect(() => { load() }, [])

  function update<K extends keyof Brand>(key: K, value: Brand[K]) {
    setBrand((current) => ({ ...current, [key]: value }))
    setSave({ kind: 'idle' })
  }

  function pickLogo(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (!LOGO_TYPES.includes(file.type)) return setSave({ kind: 'error', message: 'Use a PNG, JPEG or WebP logo.' })
    if (file.size > LOGO_BYTES) return setSave({ kind: 'error', message: 'The logo is larger than 200 kB. Export a smaller version (about 600 pixels wide is plenty).' })
    const reader = new FileReader()
    reader.onload = () => update('logo', String(reader.result))
    reader.onerror = () => setSave({ kind: 'error', message: 'Could not read that file.' })
    reader.readAsDataURL(file)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!brand.name.trim()) return setSave({ kind: 'error', message: 'Add your company or agency name.' })
    setSave({ kind: 'saving' })
    try {
      const result = await saveBranding({ ...brand, name: brand.name.trim(), footer: brand.footer.trim() })
      setBrand(result.brand ?? EMPTY)
      setSaved(true)
      setSave({ kind: 'saved' })
    } catch (e) {
      setSave({ kind: 'error', message: e instanceof Error ? e.message : 'Could not save your branding.' })
    }
  }

  async function remove() {
    if (!window.confirm('Remove your branding? Printed reports go back to the standard layout.')) return
    try {
      await deleteBranding()
      setBrand(EMPTY)
      setSaved(false)
      setSave({ kind: 'idle' })
    } catch (e) {
      setSave({ kind: 'error', message: e instanceof Error ? e.message : 'Could not remove your branding.' })
    }
  }

  return (
    <section id="branding" aria-labelledby="branding-heading" className="mt-14 scroll-mt-24 border-t border-line pt-10">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="branding-heading" className="text-xl font-light">Branded PDF reports</h2>
          <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
            Put your name, logo and color on printed reports so you can hand them straight to a client. Save PDF on any of your reports uses it, with no Walkthru branding on the pages.
          </p>
          <Link to="/docs#reports" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">About reports</Link>
        </div>

        <div aria-live="polite" className="min-w-0">
          {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading your branding" className="h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
          {state.kind === 'error' && (
            <div role="alert" className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-danger">Could not load your branding: {state.message}</p>
              <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
            </div>
          )}
          {state.kind === 'locked' && (
            <div className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-ink">Branded PDF reports are part of the Plus plan.</p>
              <p className="mt-1 text-sm text-muted">Every plan can save a report as a PDF. <Link to="/#pricing" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">See the plans</Link></p>
            </div>
          )}
          {state.kind === 'ready' && (
            <form onSubmit={submit} className="grid gap-6" noValidate>
              <CoverPreview brand={brand} />
              <div className="grid gap-5 sm:grid-cols-2">
                <label htmlFor="brand-name" className={`${label} sm:col-span-2`}>
                  Company or agency name
                  <input id="brand-name" value={brand.name} onChange={(e) => update('name', e.target.value)} maxLength={80} className={input} placeholder="Acme Studio" required />
                </label>
                <div className={label}>
                  <label htmlFor="brand-logo">Logo (PNG, JPEG or WebP, up to 200 kB)</label>
                  <div className="flex items-center gap-3">
                    <input id="brand-logo" type="file" accept="image/png,image/jpeg,image/webp" onChange={pickLogo} className="min-w-0 text-sm text-muted file:mr-3 file:rounded-full file:border file:border-line file:bg-bg file:px-4 file:py-2 file:text-sm file:text-ink hover:file:bg-surface" />
                    {brand.logo && <button type="button" onClick={() => update('logo', null)} className="shrink-0 text-xs text-muted underline decoration-line underline-offset-4 hover:text-ink">Remove</button>}
                  </div>
                </div>
                <label htmlFor="brand-color" className={label}>
                  Brand color
                  <span className="flex items-center gap-3">
                    <input id="brand-color" type="color" value={brand.color} onChange={(e) => update('color', e.target.value)} className="h-11 w-14 shrink-0 cursor-pointer rounded-xl border border-line bg-bg p-1" />
                    <span className="font-mono text-xs text-muted">{brand.color}</span>
                  </span>
                </label>
                <label htmlFor="brand-footer" className={`${label} sm:col-span-2`}>
                  Footer line (optional)
                  <input id="brand-footer" value={brand.footer} onChange={(e) => update('footer', e.target.value)} maxLength={120} className={input} placeholder="Prepared for Northwind by Acme Studio, hello@acme.studio" />
                </label>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button type="submit" disabled={save.kind === 'saving'} className={`${btnPrimary} disabled:opacity-50`}>{save.kind === 'saving' ? 'Saving' : 'Save branding'}</button>
                {saved && <button type="button" onClick={remove} className={btnGhost}>Remove branding</button>}
                {save.kind === 'saved' && <p role="status" className="text-sm text-muted">Saved. Your next PDF uses it.</p>}
                {save.kind === 'error' && <p role="alert" className="text-sm text-danger">{save.message}</p>}
              </div>
              <p className="text-xs leading-relaxed text-muted">The color must stay readable on white paper, so very light colors are refused. In the print dialog, turn off "Headers and footers" for a clean page edge.</p>
            </form>
          )}
        </div>
      </div>
    </section>
  )
}

/** A small, faithful sketch of the PDF cover, so the owner sees the result before printing. */
function CoverPreview({ brand }: { brand: Brand }) {
  return (
    <div aria-label="Preview of the PDF cover" role="img" className="relative aspect-[1.414/1] overflow-hidden rounded-2xl border border-line bg-white sm:aspect-[1.8/1]">
      <div className="absolute inset-x-0 top-0 h-1.5" style={{ background: brand.color }} />
      <div className="flex h-full flex-col justify-between p-5 sm:p-7">
        <div className="flex items-center gap-3">
          {brand.logo ? <img src={brand.logo} alt="" className="h-7 max-w-[8rem] object-contain" /> : <span className="grid size-7 place-items-center rounded-md text-[10px] font-medium text-white" style={{ background: brand.color }}>{(brand.name.trim()[0] ?? 'A').toUpperCase()}</span>}
          <span className="truncate text-xs text-ink">{brand.name.trim() || 'Your company'}</span>
        </div>
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.18em]" style={{ color: brand.color }}>Launch readiness report</p>
          <p className="mt-1.5 text-lg font-extralight leading-tight text-ink sm:text-xl">yourclient.com</p>
          <p className="mt-1 truncate text-[11px] text-muted">{brand.footer.trim() || `Prepared by ${brand.name.trim() || 'your company'}`}</p>
        </div>
      </div>
    </div>
  )
}

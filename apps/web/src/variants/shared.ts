// Shared plumbing for the three home-page variants (/variants). Preview only: nothing here is used by the live site.
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollSmoother } from 'gsap/ScrollSmoother'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useState, type FormEvent, type RefObject } from 'react'
import { useNavigate } from 'react-router'

gsap.registerPlugin(useGSAP, ScrollTrigger, ScrollSmoother)

export const reduced = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** Buttery scroll for one variant. Call it FIRST in the component, before any hook that makes ScrollTriggers, so the
 *  triggers are measured against the smoother. Off for reduced motion; touch keeps native scrolling. */
export function useSmoother(wrapper: RefObject<HTMLElement | null>, content: RefObject<HTMLElement | null>, smooth = 1.15) {
  useGSAP(() => {
    if (reduced() || !wrapper.current || !content.current) return
    const smoother = ScrollSmoother.create({ wrapper: wrapper.current, content: content.current, smooth, effects: true, normalizeScroll: false })
    return () => smoother.kill()
  }, [])
}

/** In-page links under ScrollSmoother: the native jump would fight the smoother, so glide there instead. */
export function scrollToId(id: string, offset = 72) {
  const el = document.getElementById(id)
  if (!el) return
  const smoother = ScrollSmoother.get()
  if (smoother) smoother.scrollTo(el, true, `top ${offset}px`)
  else el.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth' })
}

/** The live Instant Scan, same rules as the current home page's form (components/Shared.tsx ScanForm). */
export function useScan() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const raw = String(new FormData(e.currentTarget).get('url') ?? '').trim()
    let site: string
    try {
      const u = new URL(raw.startsWith('http') ? raw : `https://${raw}`)
      if (!u.hostname.includes('.') && !u.hostname.startsWith('127.')) throw new Error()
      site = u.href
    } catch {
      setError('Enter a full website address, like yoursite.com')
      return
    }
    setError('')
    setBusy(true)
    try {
      const { instantScan } = await import('../lib/runs')
      const { run_id, reuse } = await instantScan(site)
      navigate(`/r/${run_id}`, { state: { reuse } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The scan failed. Try again in a minute.')
      setBusy(false)
    }
  }
  return { submit, error, busy }
}

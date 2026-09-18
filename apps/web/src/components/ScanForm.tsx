import { CheckCircleIcon } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'

// Front end only for now: validates and shows a confirmation. Wired to the Instant Scan API in T11.
export function ScanForm() {
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    const url = String(data.get('url')).trim()
    try {
      const u = new URL(url.startsWith('http') ? url : `https://${url}`)
      if (!u.hostname.includes('.')) throw new Error()
    } catch {
      setError('Enter a full website address, like yoursite.com')
      return
    }
    setError('')
    setDone(true)
  }

  if (done)
    return (
      <div role="status" className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100">
        <CheckCircleIcon weight="fill" className="mt-0.5 size-5 shrink-0" />
        <p className="text-sm leading-relaxed">You are on the list. Instant Scan opens on October 20 and your first report will arrive by email.</p>
      </div>
    )

  const input =
    'w-full rounded-xl border border-zinc-300 bg-paper px-4 py-3 text-sm text-zinc-900 placeholder:text-zinc-500 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/30 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-400'

  return (
    <form onSubmit={submit} noValidate className="grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
      <div className="grid gap-2">
        <label htmlFor="url" className="text-sm font-medium">Website</label>
        <input id="url" name="url" type="text" inputMode="url" placeholder="yoursite.com" className={input} aria-invalid={!!error} aria-describedby="url-error" />
      </div>
      <div className="grid gap-2">
        <label htmlFor="email" className="text-sm font-medium">Email for the report</label>
        <input id="email" name="email" type="email" required placeholder="you@yoursite.com" className={input} />
      </div>
      <button type="submit" className="rounded-full bg-emerald-700 px-6 py-3 text-sm font-medium whitespace-nowrap text-white transition hover:bg-emerald-800 active:scale-[0.98] dark:bg-emerald-400 dark:text-zinc-950 dark:hover:bg-emerald-300">
        Scan my site
      </button>
      <p id="url-error" className="text-sm text-rose-700 sm:col-span-3 dark:text-rose-400">{error}</p>
    </form>
  )
}

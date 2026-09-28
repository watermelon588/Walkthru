import { DownloadSimpleIcon, PrinterIcon } from '@phosphor-icons/react'
import { useState, type ReactNode } from 'react'
import { brand } from '../brand'
import { downloadCsv, printPage, type Cell } from '../lib/export'
import { btnGhost } from './Shared'

/** Export CSV and Save PDF for any workspace page. The PDF is the page itself through print styles, headed by
 *  <PrintHeader>, so it always matches what is on screen. */
export function ExportBar({ csv, filename, children, className = '' }: { csv?: () => Cell[][]; filename: string; children?: ReactNode; className?: string }) {
  const [msg, setMsg] = useState<string | null>(null)
  return (
    <div className={`no-print flex flex-wrap items-center gap-2 ${className}`}>
      {children}
      {csv && (
        <button type="button" onClick={() => { downloadCsv(`${filename}.csv`, csv()); setMsg('CSV downloaded. Open it in Sheets or Excel.') }} className={btnGhost}>
          <DownloadSimpleIcon weight="light" className="size-4" /> Export CSV
        </button>
      )}
      <button type="button" onClick={printPage} className={btnGhost}>
        <PrinterIcon weight="light" className="size-4" /> Save PDF
      </button>
      {msg && <p role="status" className="basis-full text-xs text-muted">{msg}</p>}
    </div>
  )
}

/** First block of a printed page: the mark, what this is and when it was exported. Hidden on screen. */
export function PrintHeader({ title, detail }: { title: string; detail?: string }) {
  return (
    <header className="print-only print-header">
      <div className="print-header-brand"><img src={brand.mark} alt="" width={22} height={22} /> {brand.name}</div>
      <h1>{title}</h1>
      <p>{detail ? `${detail} · ` : ''}Exported {new Date().toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}</p>
    </header>
  )
}

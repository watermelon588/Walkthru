export type Cell = string | number | boolean | null | undefined

/** RFC 4180 CSV. Cells that a spreadsheet would run as a formula (text from scanned sites and AI answers can start
 *  with = + - @) get a leading apostrophe, so opening the file never executes anything. */
export function toCsv(rows: Cell[][]): string {
  const cell = (v: Cell) => {
    let s = v == null ? '' : String(v)
    if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`
    return `"${s.replace(/"/g, '""')}"`
  }
  return rows.map((r) => r.map(cell).join(',')).join('\n')
}

export function downloadCsv(filename: string, rows: Cell[][]) {
  // The BOM makes Excel read the file as UTF-8 (brand names, quotes, accents).
  const blob = new Blob(['﻿', toCsv(rows)], { type: 'text/csv;charset=utf-8' })
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: filename })
  a.click()
  window.setTimeout(() => URL.revokeObjectURL(a.href), 0)
}

/** The browser's own Save as PDF, with every collapsed section opened so nothing is left out of the file. */
export function printPage() {
  const closed = [...document.querySelectorAll<HTMLDetailsElement>('main details:not([open])')]
  closed.forEach((d) => { d.open = true })
  window.addEventListener('afterprint', () => closed.forEach((d) => { d.open = false }), { once: true })
  window.print()
}

export const fileStamp = () => new Date().toISOString().slice(0, 10)
export const slug = (text: string) => text.replace(/^https?:\/\//, '').replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase().slice(0, 40) || 'export'

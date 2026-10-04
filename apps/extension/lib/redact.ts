/** Mask PII in text before it leaves the browser. Runs on every string in a snapshot. */

const EMAIL = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
// 8+ digits with optional spaces, dashes or dots between groups: cards, phones, account numbers, IBAN tails.
const LONG_NUMBER = /(?<!\w)(?:\+?\d[\d \-.]{6,}\d)(?!\w)/g;
const KEY_LIKE = /\b(?:sk|pk|rk|ghp|gho|xox[abp]|AKIA)[_-]?[A-Za-z0-9_-]{16,}\b/g;
const OPAQUE_TOKEN = /\b[A-Za-z0-9_-]{32,}\b/g;
const URL_TEXT = /https?:\/\/[^\s<>"']+/gi;

export function redact(text: string): string {
  return text
    .replace(URL_TEXT, (raw) => {
      try {
        const url = new URL(raw);
        if (url.username || url.password) { url.username = ''; url.password = ''; }
        for (const key of new Set(url.searchParams.keys())) url.searchParams.set(key, '[redacted]');
        if (url.hash) url.hash = '[redacted]';
        return url.toString();
      } catch { return '[url]'; }
    })
    .replace(EMAIL, "[email]")
    .replace(KEY_LIKE, "[key]")
    .replace(OPAQUE_TOKEN, (token) => /[A-Za-z]/.test(token) && /[0-9_-]/.test(token) ? '[token]' : token)
    .replace(LONG_NUMBER, (m) => (m.replace(/\D/g, "").length >= 8 ? "[number]" : m));
}

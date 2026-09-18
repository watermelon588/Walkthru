/** Mask PII in text before it leaves the browser. Runs on every string in a snapshot. */

const EMAIL = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
// 8+ digits with optional spaces, dashes or dots between groups: cards, phones, account numbers, IBAN tails.
const LONG_NUMBER = /(?<!\w)(?:\+?\d[\d \-.]{6,}\d)(?!\w)/g;
const KEY_LIKE = /\b(?:sk|pk|rk|ghp|gho|xox[abp]|AKIA)[_-]?[A-Za-z0-9_-]{16,}\b/g;

export function redact(text: string): string {
  return text
    .replace(EMAIL, "[email]")
    .replace(KEY_LIKE, "[key]")
    .replace(LONG_NUMBER, (m) => (m.replace(/\D/g, "").length >= 8 ? "[number]" : m));
}

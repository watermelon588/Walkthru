/** Client-side mirror of app/agent/safety.py. Enforced before any action runs in the tab. */

/** Never done for real, anywhere: money moves or data disappears. */
export const DESTRUCTIVE = /\b(delete|remove|cancel\s+subscription|pay|purchase|buy|checkout|transfer|unsubscribe)\b/i;
/** Reaches a real person. Allowed only on a domain the owner verified, after they confirm in the side panel. */
export const SENDING = /\b(send|invite)\b/i;

export function isDestructive(text: string): boolean {
  return DESTRUCTIVE.test(text ?? "");
}

export function isSending(text: string): boolean {
  return SENDING.test(text ?? "");
}

export function isDangerous(text: string): boolean {
  return isDestructive(text) || isSending(text);
}

// Visitor mode (unverified site), mirroring app/agent/safety.py: keep both verb lists identical.
const SOCIAL_VERBS = String.raw`like|unlike|love|upvote|downvote|follow|unfollow|comment|reply|post|publish|tweet|retweet|repost|reblog|share|subscribe|vote|react|message|send\s+(?:a\s+)?(?:message|request|friend\s+request|connection\s+request)|connect|add\s+friend|endorse`;
const COMMERCE_VERBS = String.raw`add\s+to\s+(?:cart|bag|basket|wish\s?list|watch\s?list|portfolio)|buy(?:\s+now)?|check\s?out|place\s+(?:an\s+)?order|order\s+now|pre-?order|trade|invest|bid|donate`;
const START = String.raw`(?:^|[.|·:;]\s*)\W*(?:\d[\d.,]*\s*[kKmM]?\s+)?`;
export const SOCIAL = new RegExp(String.raw`${START}(?:${SOCIAL_VERBS})\b(?!-)`, "i");
export const COMMERCE = new RegExp(String.raw`${START}(?:${COMMERCE_VERBS})\b(?!-)`, "i");
export const BASKET = /\badd\s+to\s+(?:cart|bag|basket|wish\s?list|watch\s?list|portfolio)\b/i;
const SEARCH = /\bsearch\b/i;

export const isSocial = (label: string) => SOCIAL.test(label ?? "");
export const isCommerce = (label: string) => COMMERCE.test(label ?? "");
export const isBasket = (label: string) => BASKET.test(label ?? "");

/** The one field a visitor-mode run may type into: the site's search box. */
export function isSearchField(el: Element): boolean {
  const input = el as HTMLInputElement;
  if (el.tagName === "INPUT" && input.type === "search") return true;
  if (el.closest('[role="search"], form[role="search"]')) return true;
  const label = [el.getAttribute("aria-label"), input.placeholder, input.name, el.id].filter(Boolean).join(" ");
  return SEARCH.test(label);
}

/** A form whose only job is search: it is or holds a search box. */
export function isSearchForm(form: HTMLFormElement | null): boolean {
  if (!form) return false;
  return form.matches('[role="search"]') || [...form.querySelectorAll("input, textarea")].some(isSearchField);
}

export function sameOrigin(a: string, b: string): boolean {
  try {
    return new URL(a).origin === new URL(b).origin;
  } catch {
    return false;
  }
}

export const MAX_STEPS = 30;
export const MAX_MINUTES = 4;

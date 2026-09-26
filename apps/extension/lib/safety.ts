/** Client-side mirror of app/agent/safety.py. Enforced before any action runs in the tab. */

/** Never done for real, anywhere: money moves or data disappears. */
export const DESTRUCTIVE = /\b(delete|remove|cancel\s+subscription|pay|purchase|buy|checkout|transfer|unsubscribe)\b/i;
/** Reaches a real person. Allowed only on a domain the owner verified, after they confirm in the side panel. */
export const SENDING = /\b(send|invite)\b/i;

/** Visitor mode (a domain the owner has not verified): buttons that write something on the site or the user's account. */
export const SOCIAL = /\b(like|unlike|follow|unfollow|comment|reply|post|share|repost|retweet|reblog|subscribe|vote|upvote|downvote|react|message|connect|add\s+friend|send\s+request|join)\b/i;
export const COMMERCE = /\b(add\s+to\s+(cart|bag|basket)|buy|purchase|checkout|check\s+out|place\s+(your\s+)?order|order\s+now|pre-?order|trade|invest|bid|donate|pay|book\s+now|reserve)\b/i;
/** Signing in with another account (Google, GitHub, Apple): stopped in Visitor mode on links too. */
export const THIRD_PARTY_LOGIN = /\b(continue|sign\s?in|sign\s?up|log\s?in|register)\s+(with|using|via)\b/i;
export const SEARCH = /\bsearch\b/i;

/** Mirrors safety.visitor_blocked in the API. */
export function visitorBlocked(text: string, link: boolean): boolean {
  const t = text ?? "";
  return THIRD_PARTY_LOGIN.test(t) || (!link && (SOCIAL.test(t) || COMMERCE.test(t)));
}

export function isDestructive(text: string): boolean {
  return DESTRUCTIVE.test(text ?? "");
}

export function isSending(text: string): boolean {
  return SENDING.test(text ?? "");
}

export function isDangerous(text: string): boolean {
  return isDestructive(text) || isSending(text);
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

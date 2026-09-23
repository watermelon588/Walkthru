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

export function sameOrigin(a: string, b: string): boolean {
  try {
    return new URL(a).origin === new URL(b).origin;
  } catch {
    return false;
  }
}

export const MAX_STEPS = 25;
export const MAX_MINUTES = 4;

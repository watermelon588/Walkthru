/** Client-side mirror of app/agent/safety.py. Enforced before any action runs in the tab. */

export const DANGER = /\b(delete|remove|cancel\s+subscription|pay|purchase|buy|checkout|send|invite|transfer|unsubscribe)\b/i;

export function isDangerous(text: string): boolean {
  return DANGER.test(text ?? "");
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

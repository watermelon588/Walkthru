/** Goal suggestions from the links and buttons on the current page. Plain code: instant, free, no model. */

import type { Element } from "./snapshot";

const RULES: [RegExp, string][] = [
  [/\b(sign ?up|get started|start (for )?free|create (an )?account|register|join now)\b/i, "Sign up for an account"],
  [/\b(log ?in|sign ?in)\b/i, "Log in and reach the dashboard"],
  [/\b(pricing|plans)\b/i, "Find the pricing and pick the right plan"],
  [/\b(book (a )?(demo|call)|request (a )?demo)\b/i, "Book a demo"],
  [/\b(add to (cart|bag)|buy now|shop now|checkout)\b/i, "Add a product to the cart and reach checkout"],
  [/\b(contact|get in touch|talk to us)\b/i, "Send a message through the contact form"],
  [/\b(work|projects?|case stud(y|ies)|portfolio)\b/i, "Open a project and read its case study"],
  [/\b(docs|documentation|guides?)\b/i, "Find the getting-started documentation"],
];

export function suggestGoals(elements: Element[], max = 4): string[] {
  const labels = elements.filter((e) => e.tag === "a" || e.tag === "button").map((e) => e.text);
  return RULES.filter(([re]) => labels.some((label) => re.test(label))).map(([, goal]) => goal).slice(0, max);
}

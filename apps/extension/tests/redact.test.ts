import { redact } from "../lib/redact";

test("masks emails", () => {
  expect(redact("Contact jane.doe+x@example.co.uk now")).toBe("Contact [email] now");
});

test("masks long numbers but keeps short ones and prices", () => {
  expect(redact("Card 4242 4242 4242 4242, phone +1 415-555-0199")).toBe("Card [number], phone [number]");
  expect(redact("Order #1234 costs $19.99, 3 items, year 2026")).toBe("Order #1234 costs $19.99, 3 items, year 2026");
});

test("masks key-looking tokens", () => {
  // Assembled at runtime so the literal never sits in git (GitHub push protection).
  const stripe = ["sk", "live", "51ABCDEFGHIJKLMNOPQRSTUV"].join("_");
  const github = ["ghp", "abcdefghijklmnopqrstuvwxyz1234"].join("_");
  expect(redact(`key ${stripe}`)).toBe("key [key]");
  expect(redact(`token ${github}`)).toBe("token [key]");
});

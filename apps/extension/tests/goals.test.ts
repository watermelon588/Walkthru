import { describe, expect, it } from "vitest";
import { suggestGoals } from "../lib/goals";

const link = (id: number, text: string) => ({ id, tag: "a", text });

describe("suggestGoals", () => {
  it("suggests goals the page actually offers, in a fixed order", () => {
    const goals = suggestGoals([link(1, "Pricing"), link(2, "Get started"), link(3, "Contact us")]);
    expect(goals).toEqual(["Sign up for an account", "Find the pricing and pick the right plan", "Send a message through the contact form"]);
  });

  it("suggests a case study on a portfolio", () => {
    expect(suggestGoals([link(1, "Selected work"), link(2, "SKYGUIDE AI")])).toContain("Open a project and read its case study");
  });

  it("ignores text fields and caps the list", () => {
    const many = ["Sign up", "Log in", "Pricing", "Book a demo", "Contact", "Docs"].map((t, i) => link(i, t));
    expect(suggestGoals([{ id: 9, tag: "input", text: "Pricing" }])).toEqual([]);
    expect(suggestGoals(many)).toHaveLength(4);
  });
});

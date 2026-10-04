<!-- /founder:user-interviews · 2026-10-04 · input: Validate whether builders and agencies pay for evidence-backed release verification. -->
# Customer interviews: actual release behavior

Assumption: no current paid-demand evidence was supplied. This script is preparation only; no messages were sent.

## Three hypotheses

| Hypothesis | Supporting behavior | Rejecting behavior |
| --- | --- | --- |
| Release investigation is painful enough to buy | Recent costly failure, hours spent, paid workaround | Cannot recall a relevant incident or only wants free checks |
| Evidence and reruns change decisions | Reproduces issue, fixes it, requests verification | Wants a general opinion without acting |
| Owner-browser setup is acceptable | Independently connects a test session and completes task | Install/auth/privacy effort exceeds perceived benefit |

## Recruit 5-8 participants

Must: shipping a logged-in app, release in last 30 days, responsible for checking it, able to authorize a scoped staging/test-account flow. Nice: agency handover or repeated weekly releases. Exclude generic AI enthusiasts without an app or participants unable to authorize testing.

Start with existing contacts, qualified opt-in beta applicants and agency contacts, not unsolicited automated messages. Estimate incentive: optional $10 for an interview, never conditional on praise/purchase. Participation and purchased missions are separate.

## Exact 25-minute script

**Opening, 2 minutes**
"I am trying to understand how you check a release. I want your actual experience, including reasons a new tool would be unnecessary. This is not a sales pitch. May I take notes? If recording is useful, may I record this conversation? Saying no is fine."

**Context, 3 minutes**
- "What did you release most recently?" Follow-up: "Which workflow mattered most?"
- "Who checked it before users saw it?" Follow-up: "Show me the checklist or tools if you have them."

**Problem, 10 minutes**
- "Tell me about the last release where something escaped testing." Ask what users saw and how it was discovered.
- "How did you reproduce it?" Ask for sequence, evidence and time.
- "What did the tools you already use tell you?" Ask what they missed or made harder.
- "How did you decide the fix worked?" Ask whether anyone repeated the original workflow.
- "What did you spend on that investigation?" Separate cash, hours and interruptions.
- "What happened when signup or authentication blocked testing?" Ask who supplied test accounts/OTP.
- "Tell me about the last tool you tried and stopped using." Ask what made it expendable.

Do not mention Sonnet, video, our features or speculative conversion improvement in this section.

**Unprompted priorities, 4 minutes**
- "Which part of that process did you most want to hand to someone else?"
- "What information was missing when you had to decide whether to ship?"
- "What would you refuse to share with a testing service?" Ask for specific policies, not imagined ideal behavior.

**Concept and reaction, 4 minutes**
"We are testing a service that executes one agreed release journey in your authorized browser. It returns reproducible evidence and checks the repaired outcome on a rerun."
- "Which part would duplicate what you already do?"
- "Which claim would you need to verify before trusting the packet?"
- "Looking at this example, which issue could you reproduce or dismiss?" Use a labelled real sample.
- "What would stop you connecting a test account?"

**Closing, 2 minutes**
"Would you be willing to nominate one real staging journey and share its expected result this week?" Offer a clearly priced pilot only after explaining scope; a compliment is not a purchase. Ask for a referral if appropriate. No recording or outreach happens without explicit consent/authorization.

## Analysis sheet

Track role, last failure, tools, time/cost, disputed findings, setup completion, paid offer accepted, repair and rerun. After 5-8 interviews, compare repeated recent behavior, not the loudest feature request.

Proposed signal: at least 3 participants provide a real mission and 2 commit money to a declared pilot. Rejections split into no pain, inadequate trust, excessive setup, wrong price and wrong outcome. Do not interpret "sounds cool" or "add a video" as demand.

Saved to founder/user-interviews.md. Next: validate-idea, mvp-scope.
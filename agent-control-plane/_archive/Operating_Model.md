# Operating Model: shipping without reading code

How Oka actually works with the agent. Written 2026-07-25 after establishing he does not intend to write or review code.

---

## The swap that makes this work

The usual advice is "review the agent's changes before merging." That requires reading code. Replace it with this:

**You do not review code. You test the product.**

Every job the agent does ends with a link you click. You use the page like a customer would. It either does what you asked or it doesn't. That judgement needs no technical skill and catches the failures that matter, because a change that breaks the experience is exactly the thing a code review often misses anyway.

For this to be safe, the machine has to catch the things you can't see. That is what the gates below are for.

---

## The loop

```
1. You describe the job in #code, in plain language
2. Agent works on its own branch, never on the live code
3. GATES RUN AUTOMATICALLY:
      does it build?
      do the types check?
      do the tests pass?
   If any fail, the agent fixes it and tries again. You never see this.
4. Only once the gates pass, you get a preview link
5. You click it and use it like a customer
6. You say "ship it" or "the button does nothing on mobile"
7. Ship goes live. Fix goes back to step 2.
```

Your entire job is steps 1, 5 and 6. Describing and testing.

---

## The gates, and why each one exists

These run without you and are the reason not reading code is survivable.

| Gate | Catches | Without it |
|---|---|---|
| `npm run build` | Code that cannot run at all | Agent reports success, site is a white screen |
| TypeScript check | Wrong data passed between parts | Page loads, breaks on real input |
| Tests (later) | Old features broken by new work | You fix one thing and silently break three |
| Preview deploy | Everything else | You test on your laptop, it behaves differently live |

**The rule: the agent is not allowed to tell you a job is done until every gate is green.** A failing gate is the agent's problem to solve, not yours to look at. This is what keeps the noise away from you.

---

## Three things the agent does not get to freestyle

Not because you can't code. Because failure here is invisible and expensive.

**1. Money.** Use the payment provider's own hosted checkout page. Xendit or Stripe handles the card, the page, the receipt. Your code never touches a payment amount. The agent cannot get the price wrong if the price is set in Xendit's dashboard, not in your code.

**2. Selfies.** One rule, tested by hand on every single release: upload a photo, wait for the report, confirm the image is gone. Put it in a checklist and do it every time. It takes ninety seconds and it is the difference between a product and a lawsuit.

**3. Anything live that already works.** Once real people are paying, the agent works on a branch and you test the preview. No exceptions, no "just this small fix."

---

## When you get stuck (you will)

The stuck loop is the real cost of vibe coding: the agent tries, breaks something else, tries again, and you cannot tell progress from thrashing.

**Rule: three attempts, then stop.** If the agent has failed three times at the same job, do not ask it again. Escalate:

1. Copy the error and the job description, and paste both to me. I read code, that is what I am for.
2. Or split the job into two smaller ones. Most stuck loops are one task that was really three.
3. Or ask whether you need it at all. A surprising amount of stuck work is a feature nobody asked for.

Three attempts is roughly the point where the agent has stopped reasoning and started guessing.

---

## What to say and what not to say

The quality of your instruction sets the ceiling on the result. This is the one skill genuinely worth developing, and it is writing, not programming.

| Weak | Strong |
|---|---|
| "make the quiz better" | "the quiz asks 8 questions on one long page. Split it into 8 screens, one question each, with a back button and a progress bar" |
| "it's broken" | "on my phone, after I upload a photo, the Next button does nothing. On my laptop it works" |
| "add payments" | "after the free teaser email, the unlock link opens a Xendit hosted checkout for Rp 39.000. On success, send the full report" |

Pattern: say what you see, where you saw it, and what should happen instead. Never say how to build it. That is the agent's job and you will slow it down guessing.

---

## What this model cannot do

Honest limits, so they are not a surprise later:

- It will not ship a whole product from one instruction. It ships one task at a time, and there are perhaps sixty tasks in v1.
- It will not catch a bug that looks fine to a user. Slow pages, a subtly wrong report, a mis-set price. You need to look for these deliberately.
- It will not make product decisions. What to build, what to charge, what to cut. That stays yours, and it is the part that actually determines whether this makes money.

The agent removes the typing. It does not remove the judgement, and judgement is where you already have an advantage over people who only know how to code.

---

*Related: `START_HERE.md` (the bot), `Adding_A_Tool.md` (extending it), `../Style Report/Build_The_Skeleton.md` (the product's starting point).*

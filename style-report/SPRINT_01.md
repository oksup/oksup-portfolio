# Sprint 01: First Paying Customer

**Dates:** Mon 27 Jul 2026 to Sun 23 Aug 2026 (4 weeks)
**Team:** Oka, plus the agent control plane
**Sprint goal:** One stranger pays Rp 39.000 for a style report and receives something they would show a friend.

---

## The call I made on your two answers

You chose "the machine" as the target and "first paying customer" as done. Those pull apart. A control plane does not generate revenue; the product does. So:

- **The goal is the customer.** The machine is the means, not the deliverable.
- **The machine gets worked on only where it blocks revenue.** No Outline, no Plane, no Forgejo, no SigNoz, no VPS. None of that gets you a customer and all of it eats the sprint.
- If at the end you have a paying customer and an unglamorous bot, the sprint succeeded.

---

## Capacity

30 h/week x 4 weeks = 120 raw hours. Planned to 75%, because interrupts, quota waits and agent retries are real.

| Week | Available | Planned | Notes |
|---|---|---|---|
| W1 (27 Jul - 2 Aug) | 30h | 22h | Phase A, payment signup started day 1 |
| W2 (3 - 9 Aug) | 30h | 22h | Real AI report. Quality gate at end. |
| W3 (10 - 16 Aug) | 30h | 22h | Delivery and payment. Nakula FIN-003 reminder falls 10 Aug. |
| W4 (17 - 23 Aug) | 30h | 24h | Traffic and selling. Most likely to overrun. |
| **Total** | **120h** | **90h** | 30h buffer |

Your time splits roughly: 20% writing jobs, 30% waiting on agents, 40% testing, 10% unblocking. Only the writing and testing are really yours.

---

## Sprint backlog

| Pri | Item | Est | Week | Blocked by |
|---|---|---|---|---|
| **P0** | Payment rail chosen and signup submitted | 3h | W1 d1 | Nothing. Do this first. |
| **P0** | Phase A: whole flow, fake data (8 queued jobs) | 16h | W1 | Vercel connected |
| **P0** | Quality gate: is the fake report worth paying for? | 3h | W1 end | Phase A |
| **P0** | Gemini paid tier, selfie handling policy written | 2h | W2 | Nothing |
| **P0** | Phase B: teaser and full report from real selfie | 16h | W2 | Phase A |
| **P0** | Report quality loop: test on 10 real people, iterate prompt | 6h | W2 end | Phase B |
| **P0** | Database + own Brevo account with SPF/DKIM | 6h | W3 | Nothing |
| **P0** | Email delivery: teaser instant, full report on payment | 8h | W3 | Database |
| **P0** | Payment integration + unlock link | 8h | W3 | Payment account approved |
| **P0** | Selfie deletion verified + privacy page live | 3h | W3 | Phase B |
| **P0** | 100 real visitors from a channel you control | 10h | W4 | Everything above |
| **P1** | Bot runs as a background service, survives laptop sleep | 3h | W2 | Nothing |
| **P1** | Landing page SEO + one ranking article | 8h | W4 | Phase A |
| **P1** | WhatsApp share card that looks right | 2h | W4 | Phase A |
| **P2** | Second occasion (job interview) | 8h | - | Revenue proven |
| **P2** | Autopilot improvements | - | - | Only if it hurts |

**Load: 90h of 120h available (75%).** P2 does not get started unless P0 finishes early.

---

## Week by week

### W1: a clickable product with fake content
Day 1 is the payment signup, before anything else, because it is the only thing someone else controls. Then run the Phase A queue. End the week by looking hard at the fake report page.

**Exit:** you can click from landing to a finished report on your phone, and you would pay for that layout if the words were real.

### W2: make the words real
Gemini paid tier first, selfie policy written before a single real photo is processed. Then teaser and full report generation. Spend the back half of the week on prompt quality with 10 real people, not on features.

**Exit:** 10 reports generated from real selfies. At least 7 of those people say they would pay.

### W3: take money and deliver
Database, your own Brevo, email delivery, payment, selfie deletion, privacy page.

**Exit:** you can pay yourself Rp 39.000 from a different phone and receive the report.

### W4: find one stranger
Not SEO. SEO is your edge but it does not deliver inside four weeks. This week is manual: Instagram, WhatsApp groups, kondangan communities, friends of friends, one paid test if needed.

**Exit:** one payment from someone you are not related to.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Payment account rejected or slow** | Kills the goal entirely. Xendit typically wants a registered business. | Submit day 1. If individual accounts are refused, fall back to a service that accepts individuals, or static QRIS with manual confirmation for the first customers. Manual is fine at n=1. |
| **Report is not worth paying for** | Everything downstream is wasted | Hard gate at end of W2. If under 7 of 10 would pay, stop and fix the prompt before touching payment. |
| **SEO will not deliver in 4 weeks** | No traffic, no customer | Already assumed. W4 is manual distribution. SEO is a month 2-3 asset. |
| **Selfie privacy incident** | Ends the product | Delete after generation, manual 90-second check every release, privacy page before any public traffic, paid Gemini tier only. |
| **Antigravity quota (5h reset)** | Throughput stalls | Queue jobs in batches, run autopilot when stepping away. |
| **Nakula work spikes** | Sprint slips | 30h buffer exists for this. FIN-003 reminder lands 10 Aug. |
| **You are the only tester** | Blind to obvious problems | The 10-person test in W2 is not optional. |

---

## Definition of done

Adapted, because you do not review code.

- [ ] Build passes (machine-checked, you never see failures)
- [ ] Tested on your actual phone, not a shrunk browser
- [ ] Shipped to live and confirmed working there
- [ ] For anything touching photos: selfie deletion verified by hand
- [ ] For anything touching money: tested with a real Rp 39.000 payment from another phone

---

## Key dates

| Date | Event |
|---|---|
| Mon 27 Jul | Sprint starts. Payment signup submitted same day. |
| Sun 2 Aug | W1 review: is the fake report worth paying for? |
| Sun 9 Aug | **Quality gate.** 10 real reports, 7 must say they would pay. Go or fix. |
| Sun 16 Aug | W3 review: you can pay yourself and receive the report |
| Sun 23 Aug | Sprint end. Retro. |

---

## What I will not do this sprint

Written down so it does not creep back in.

Self-hosted Outline, Plane, Forgejo, SigNoz, OpenPanel. A VPS. Analytics beyond Vercel's built-in. A second occasion. English translation. A brand identity beyond a name and a favicon. Subscriptions. User accounts or login. A mobile app.

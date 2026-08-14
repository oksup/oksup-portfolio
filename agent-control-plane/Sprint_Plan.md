# Blueprint Roadmap: Autonomous AI Agent Control Plane

*Filed 2026-07-26. The plan as Oka specified it, marked against what is built, with the cheap path chosen at every fork.*

## System overview

An autonomous, 24/7 Discord-orchestrated business engine that executes products from idea to revenue using a "One Agent, Many CLIs" pattern powered by the Gemini API.

Six sprints. Four of them are now built. What remains is Sprint 4 execution and the parts of Sprint 5 that touch real customers.

---

## Standing decisions

These override the sprint text below wherever they disagree. Each one was made because the alternative cost money or time for nothing.

| Decision | Instead of | Why |
|---|---|---|
| Runs on the Mac | VPS, 16GB, 4 vCPU | Nothing in Sprints 1 to 5 needs a server. Move it when the laptop needs to close |
| LiteLLM | `google-genai` SDK direct | Provider swap stays one line in `config.py`. Importing a vendor SDK undoes that |
| SQLite and markdown | Outline, Plane, Forgejo | 15 to 20 containers, four databases, zero revenue. Wrapper pattern means swapping later changes one function body |
| Sentry and Vercel logs | SigNoz | SigNoz hard-minimums 4GB RAM and idles at 1.5 to 2GB. It is the single line item that would blow the budget |
| QRIS, manual confirmation | Xendit, Stripe | Personal business, no entity. QRIS costs nothing at this ticket size. See below |
| 900s coding timeout | 120s | Real `agy` jobs run in minutes. 120s kills them mid-write and leaves a dirty tree |

### The QRIS finding

Bank Indonesia sets MDR for **Usaha Mikro Individu at 0% on transactions of Rp 500.000 or less**. Above that it is 0.3% for UMI, and 0.7% for registered small, medium and large merchants.

A Rp 39.000 ticket therefore costs **Rp 0 to collect**. This kills the old worry that fixed per-transaction gateway fees would force the price up to Rp 59.000. They would have, but only because a gateway was assumed. There is no reason to use one yet.

Two consequences worth holding on to:

- MDR is borne by the merchant and **may not be passed to the customer**. Do not add a "biaya admin" line.
- A static QRIS code cannot notify anything. Payment confirmation is a human step: you see it land, you say so in `#payments`. That is the trade for zero fees, and at low volume it is the right trade.

Swap in a provider with callbacks when confirming by hand becomes the bottleneck, not before. iPaymu and GDCPay both onboard individuals with a KTP and no business entity, so the door stays open.

---

## Sprint 1: Core foundation and gateway setup

**Goal:** Local infrastructure, Discord command center, Gemini function-calling gateway.

| # | Task | Status | Note |
|---|---|---|---|
| 1.1 | Provision VPS, install Docker Compose | Deferred | Standing decision. Revisit when the laptop needs to close |
| 1.2 | Private Discord server and channels | Partial | 6 channels have tools now. `#deployments` and `#alerts` are webhook sinks, see Sprint 5 |
| 1.3 | Register Discord app, Message Content Intent, API keys | Done | Both keys in `orchestrator/.env` |
| 1.4 | `discord.py` bot with channel-based tool routing | Done | Routes through **LiteLLM**, not `google-genai` |
| 1.5 | Channel scoping enforced at runtime | Done | Twice: absent from the schema list, rejected again at execution |

**Acceptance criteria:** all three met.

---

## Sprint 2: Specification and task engine

**Goal:** Automate ideation, spec creation, and task generation.

| # | Task | Status | Note |
|---|---|---|---|
| 2.1 | Knowledge base | Done, as stub | Markdown under `data/notes/` |
| 2.2 | Task tracker | Done, as stub | SQLite at `data/tasks.db` |
| 2.3 | Read/write spec documents | Done | `tools/notes.py` |
| 2.4 | Create, update, list tasks | Done | `tools/tasks.py` |
| 2.5 | Spec-to-task pipeline | Done | `tools/plan.py::plan_work` reads every spec `.md`, writes 4 to 10 sized jobs into the tracker |

**The value in 2.5 is sizing, not text generation.** One job equals one screen, one section, or one specific change. Oversized jobs are the single biggest cause of bad agent output.

---

## Sprint 3: Autonomous coding and CI/CD engine

**Goal:** Autonomous code generation, repository management, deployment previews.

| # | Task | Status | Note |
|---|---|---|---|
| 3.1 | Self-hosted Git | Skipped | GitHub already drives Vercel previews. Forgejo removes the preview link |
| 3.2 | Headless coding agent | Done | `agy -p "$(cat FILE)" --mode=accept-edits --dangerously-skip-permissions`. The absolute repo path must be carried in the prompt text |
| 3.3 | Async subprocess isolation | Done | `asyncio.to_thread`, 900s timeout |
| 3.4 | Branch per job, never `main` | Done | Refuses to start on a dirty tree |
| 3.5 | Preview URL posted automatically | Partial | `gh pr create` runs, Vercel comments the preview on the PR, URL comes back in `#code`. Routing it to `#deployments` is a Discord webhook, no code |

**Job loop as built:**

```
branch -> run agent -> did git change anything? -> commit
  -> build must pass -> up to 3 self-fix attempts -> stop
  -> protected-path check -> merge or hold
  -> push, open PR so the preview appears -> report where to look
```

Git is the source of truth. The agent's stdout is never parsed to decide whether a job worked.

---

## Sprint 4: Growth, marketing and content engine

**Goal:** Automate creative generation, SEO pages, ad copy.

| # | Task | Status | Where |
|---|---|---|---|
| 4.1 | Creative generation | **Done** | `#creatives`: `write_ad_copy`, `write_social_post`, `image_prompt` |
| 4.2 | SEO generation | **Done** | `#seo`: `keyword_map`, `write_metadata`, `queue_seo_page` |
| 4.3 | Email delivery | **Done, needs key** | `tools/email.py` via Brevo. Set `BREVO_API_KEY` and `BREVO_SENDER_EMAIL` |
| 4.4 | Ad campaign pipeline | Not built | Deliberate. No traffic to optimise yet, and copy generation already covers the useful half |

**Two things these tools deliberately will not do.**

They never name a price. Prices change and copy that hardcodes one goes stale the day it does.

They never state a search volume or difficulty score. A model does not know them and will invent a plausible number. `keyword_map` writes `?` in those columns for a real tool to fill. The judgement half is where the model helps; the data half is where it lies.

`queue_seo_page` writes a build job and puts it straight in the queue, so an SEO page goes from keyword to live page without leaving Discord. It runs the same FORBIDDEN filter the planner uses.

---

## Sprint 5: Analytics, payments and observability

**Goal:** Monitoring, funnel analytics, transaction alerts.

| # | Task | Status | Note |
|---|---|---|---|
| 5.1 | Observability stack | Replaced | Sentry free tier plus Vercel logs. No SigNoz, no VPS, no ClickHouse |
| 5.2 | Alerts into `#alerts` | Setup only | Discord channel webhook. No bot code needed, see below |
| 5.3 | Funnel analytics | Replaced | Vercel Analytics free tier until there is volume worth a real tool |
| 5.4 | **Payments** | **Done** | `#payments`: `record_payment`, `list_payments`, `revenue_summary`, `deliver_report`, `email_status`. QRIS, manual confirmation |
| 5.5 | AI support agent | Not built | Premature. No customers to support yet |

**5.2 and 3.5 need no code, but not the way it first looked.** In Discord: channel settings, Integrations, Webhooks, New Webhook, copy the URL.

`#deployments` goes through **GitHub, not Vercel**. Vercel account webhooks are Pro and Enterprise only, and the payload is not Discord-shaped, so a Discord URL pasted into Vercel fails on both counts. GitHub repo Settings, Webhooks, Add webhook, Payload URL is the Discord URL plus `/github`, events Pull requests and Deployment statuses. Vercel comments the preview on the PR, so the link lands in the channel anyway. Third-party forwarders exist (vercord, verceldiscord.dev) if raw Vercel events are ever wanted; not worth a dependency for this.

`#alerts` goes through Sentry's native Discord integration, free tier, and uses **no webhook URL**: Sentry installs a bot via OAuth (Settings, Integrations, Discord, Add Installation) and then each alert rule names a target channel by **ID or URL**, never by name. Requires owner, manager or admin on the Sentry org and Manage Server in Discord. Sentry also has to be installed into the Next.js app before it reports anything, which edits config files, so it is a human step and the protected-path gate would hold it anyway. `#deployments` and `#alerts` get **no tools on purpose**: a channel with no tools cannot be used to reach anything, so a notification sink stays a notification sink.

**`deliver_report` refuses to send to an address with no payment on record.** There is deliberately no general-purpose `send_email` tool sitting next to it, because a model with both would route around that check, and that check is the only thing stopping a paid report going out free.

---

## Sprint 6: Autopilot loop, guardrails and human escalation

**Goal:** Multi-channel autonomous handoffs with safe failure boundaries.

| # | Task | Status | Note |
|---|---|---|---|
| 6.1 | Cross-channel handoff | Partial | `#tasks` to `#code` via `work_next_task`. `#seo` to `#code` via `queue_seo_page`. `#wiki` entry point not wired |
| 6.2 | Restore points | Done | `autopilot-MMDD-HHMM` tag before anything is touched. `rewind <tag>` undoes a whole run |
| 6.3 | Halt after 3 failures | Done | `MAX_FIX_ATTEMPTS=3`. Past three the agent is guessing |
| 6.4 | **Sensitive action guardrails** | **Done, two layers** | See below |
| 6.5 | Cost caps | Done | 20 jobs or 90 minutes, stop on first failure, `stop_queue` to halt after the current job |

### 6.4: two independent layers, because one is not enough

**Layer one, write-time.** `FORBIDDEN` in `tools/plan.py` stops the planner from *writing* a job about price, payment, checkout, secrets or `.env`, in English and Bahasa. This exists because the planner emitted a pricing job despite being told in the prompt not to. A prompt instruction is not a safety property.

**Layer two, merge-time.** `PROTECTED_PATHS` in `config.py`, enforced in `tools/code.py`. Autopilot merges passing builds automatically, except any job that touched a payment, auth, middleware, config or env file. Those get pushed with a PR opened and **held** for a human. The queue carries on with the rest.

Layer one only covers jobs the planner wrote. Layer two also covers jobs typed by hand in `#code`, and jobs where the agent wandered into a sensitive file on its own. Matching deliberately over-matches: a false positive costs one manual merge, a false negative costs unreviewed payment code.

---

## Cost model

Efficient, not free. Where a paid option is clearly better, it is chosen.

| Line | Choice | Monthly |
|---|---|---|
| Orchestrator model | Flash-Lite on `#tasks`, `#wiki`, `#seo`. Flash on `#code`, `#creatives`, `#payments` | $1 to $5 at this volume |
| Coding agent | Antigravity CLI | Its own plan |
| Hosting | Vercel free tier | $0 |
| Git | GitHub free | $0 |
| Email | Brevo free, 300/day | $0 |
| Payments | QRIS, 0% MDR at this ticket size | $0 |
| Errors | Sentry free tier | $0 |
| Analytics | Vercel Analytics free tier | $0 |
| Server | None, runs on the Mac | $0 |

The channel split is the lever. Chatty channels run at $0.30/$2.50 per million tokens instead of $1.50/$7.50, so `#tasks` and `#wiki` cost roughly a fifth of what they did. Quality stays on the channels where a customer sees the output.

`spend_report` in `#tasks` reads `data/costs.csv`, which every model call appends to, and gives a per-channel breakdown and a monthly run rate. Check it after the first heavy day rather than guessing.

**Selfie handling is the one place to pay without hesitating.** Paid Gemini tier only. The free tier may train on prompts, and the product takes photographs of people's faces.

---

## Channels and tools

Six channels with tools, two notification sinks. 28 tools registered. A channel over about 8 tools should be split: a model choosing between 4 tools beats one choosing between 30.

| Channel | Model | Tools |
|---|---|---|
| `#tasks` | fast | plan_work, create_task, list_tasks, set_due_date, complete_task, delete_task, spend_report |
| `#wiki` | fast | write_note, list_notes, read_note |
| `#code` | smart | plan_work, run_queue, stop_queue, work_next_task, assign_coding_task, list_jobs, ship_job, rewind |
| `#creatives` | smart | write_ad_copy, write_social_post, image_prompt |
| `#seo` | fast | keyword_map, write_metadata, queue_seo_page |
| `#payments` | smart | record_payment, list_payments, revenue_summary, deliver_report, email_status |
| `#deployments` | none | webhook sink |
| `#alerts` | none | webhook sink |

The bot does not create its own channels and cannot grant itself tools. It has write access to the repo, so a self-granted tool is a self-modifying agent. It can propose; Oka approves.

---

## What is next

Ordered by distance to a paying customer.

| Order | Action | Blocked on |
|---|---|---|
| 1 | Run Phase A, judge the fake report page | nothing |
| 2 | Create `#creatives`, `#seo`, `#payments` in Discord | nothing, 2 minutes |
| 3 | Brevo API key into `.env`, verify the sender address | Brevo dashboard |
| 4 | Discord webhooks for `#deployments` and `#alerts` | nothing, 5 minutes |
| 5 | Static QRIS code from the banking app, put it on the checkout screen | bank app |
| 6 | First real customer, confirmed by hand in `#payments` | traffic |

## The boundary that moves

Autopilot merges unreviewed code into `main`. That is acceptable because the protected-path gate now holds back anything touching money, auth or config, and because the site has no users.

When real customers exist, the question changes from "can this break the build" to "can this lose someone's money or their photo". At that point either every merge gets a human, or the protected path list grows to cover the whole payment and upload flow. Do not let this drift.

## Sources

- [Ragam Tarif QRIS, Indonesia Baik](https://indonesiabaik.id/infografis/ragam-tarif-qris)
- [MDR QRIS Bagi Merchant, Bank Indonesia](https://www.bi.go.id/id/publikasi/ruang-media/cerita-bi/Pages/mdr-qris.aspx)
- [Biaya MDR QRIS 2026 untuk Merchant, GetQRIS](https://getqris.id/biaya-mdr-qris-2026-getqris/)
- [Payment Gateway Murah untuk UMKM dan Perorangan, GDCPay](https://gdcpay.id/payment-gateway-murah-untuk-umkm/)
- [iPaymu](https://ipaymu.com/)

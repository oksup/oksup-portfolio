# Project Summary: Autonomous Agent Control Plane + Style Report

*Context document. Current as of 2026-07-25.*

---

## 1. What this is

Two linked projects:

**Agent Control Plane** — a Python bot running on a Mac that listens in a private Discord server, decides which tool to call from plain-English messages, and drives a coding agent that builds a website unattended.

**Style Report** — the first product it builds. A Bahasa-Indonesian AI style report: one selfie plus a 6-question quiz produces a personalised "what to wear" plan, emailed. Free teaser captures the email, paid full report (target Rp 39.000) contains buyable Indonesian items. V1 covers one occasion only: kondangan (Indonesian wedding guest).

Inspired by FaceCard.fyi (founder Radja Thaher) and his "lazymaxxing" model: human as CEO setting direction, agent swarm as workforce. Same category, own build, no copied assets.

---

## 2. Operator profile

Important for anyone assisting on this.

- Fluent in Python, data and finance. **Beginner** in Discord bots, web infrastructure, JavaScript, Docker.
- **Does not write or read code, by choice.** Vibe coding deliberately. Never design a workflow whose safety depends on him reviewing a diff.
- Wants clicks and exact commands, not architecture discussion. One action, one file, one thing to type.
- Hard rules: no emojis, no em-dashes, no filler, be brief.
- Feedback given: "you only overcomplicate things." Default to the next concrete action over a new system.

His review model: **he tests, he does not review.** Machine gates catch what he cannot see; he judges the result as a user would.

---

## 3. Architecture

```
Discord (private server)
  #tasks  -> task tracker tools
  #wiki   -> note tools
  #code   -> planning, coding agent, autopilot
      |
Python orchestrator (discord.py + LiteLLM)
      |
  +---+----------------------------+
  |                                |
Gemini (decides which tool)   Antigravity CLI `agy` (writes code)
                                   |
                            ~/dev/style-report (git repo)
                                   |
                            GitHub -> Vercel (live site + previews)
```

**One agent, many CLIs.** The model never gets raw shell access. Every capability is a scoped Python function with an explicit JSON schema.

**Channel scoping is the security boundary and the top accuracy lever.** A model choosing between 4 tools beats one choosing between 30. Enforced twice: tools not listed for a channel are absent from the schema list, and rejected again at execution time.

**LiteLLM abstraction.** Nothing imports `google.genai` or `anthropic` directly. Provider swap is one line in `config.py`.

---

## 4. Current state

Working:

| Component | State |
|---|---|
| Discord bot, 6 channels, 28 tools | Running locally on Mac |
| Task tracker (SQLite, stands in for Plane) | Working, with due dates |
| Notes (markdown files, stands in for Outline) | Working |
| Coding agent via `agy` | Working end to end |
| Autopilot: whole queue unattended, auto-merged | Built, with rewind restore points |
| `plan_work`: writes its own job queue from specs | Built |
| Protected-path merge gate | Built 2026-07-26. Money, auth and config jobs are held for a human |
| `#creatives`, `#seo`, `#payments` channels | Built 2026-07-26. 28 tools across 6 channels |
| Brevo email delivery, QRIS payment log, cost tracking | Built 2026-07-26 |
| Next.js skeleton on GitHub | Done |
| Vercel deploy + per-branch previews | In progress |

Not started: the product itself beyond the skeleton. Phase A (8 jobs, whole flow with fake data, no signups needed) is queued.

**Build order was deliberately inverted from the original blueprint.** The original called for self-hosting Outline, Plane, Forgejo, SigNoz and OpenPanel first, which is roughly 15 to 20 Docker containers and four databases before a single agent message. Instead: agent loop first against SQLite and markdown stubs, real services later. The CLI wrapper pattern means swapping a stub for the real thing changes only a function body.

---

## 5. Hard-won technical facts

The expensive lessons. Most cost a debugging cycle to find.

**Gemini models go stale fast.** `gemini-2.5-flash` was retired for new API keys around 2026-07-21. Current: `gemini-3.5-flash-lite` (fast, $0.30/$2.50 per M) and `gemini-3.6-flash` (smart, $1.50/$7.50 per M). `list_models.py` queries the key directly rather than trusting any hardcoded name.

**Antigravity CLI (`agy`) headless invocation.** Working form:
```
agy -p "$(cat FILE)" --mode=accept-edits --dangerously-skip-permissions
```
There is no `--yes`, no `--no-color`, no `run` subcommand, no `--output json`. Invalid flags give exit 2 plus usage text. `agy run ...` treats "run" as prompt text and opens the interactive UI, which hangs forever in a script.

**`agy` ignores the process working directory.** With no active workspace it writes into `~/.gemini/antigravity-cli/scratch/`, exits 0, and reports success. A git repo in cwd does not fix it. There is no `--cwd` or `--workspace` flag. **The absolute repo path has to be carried in the prompt text.**

**`~/.gemini/antigravity-cli/settings.json` is more reliable than flags.** Set `agentMode: accept-edits`, `toolPermission: always-proceed`, `artifactReviewPolicy: always-proceed`, `allowNonWorkspaceAccess: true`, `altScreenMode: never` (forces inline output instead of the alternate screen buffer, which is what makes output capturable).

**Claude Code headless (`claude -p`) no longer draws on a Pro/Max subscription** as of 2026-06-15. It bills at API rates. Gemini CLI's free tier ended 2026-06-18, replaced by Antigravity CLI.

**Environment gotchas.** macOS ships Python 3.9, so `X | None` type hints need `from __future__ import annotations`. `tenacity` is a LiteLLM dependency that does not install automatically. A config module must load its own `.env` at import time; if the entry point calls `load_dotenv()` after importing config, every setting reads as empty and defaults silently mask it.

**Vercel preview hostnames cap at 63 characters,** so branch name slugs are capped at 14. Longer names still work but get hashed and become unreadable.

---

## 6. Safety model

Guardrails, all enforced in code rather than by prompt instruction:

- **Never commits to `main` directly.** Every job is its own branch.
- **Build must pass** before anything is reported or merged. Failures go back to the agent, up to 3 attempts, then it stops.
- **Autopilot tags a restore point** before touching anything. One command undoes an entire unattended run.
- **Stop on first failure,** so a bad result cannot compound across later jobs.
- **Caps:** 20 jobs or 90 minutes per run.
- **Forbidden-job filter.** The planner is told never to write jobs touching price, payment, checkout, Xendit, Stripe, API keys or secrets. It did anyway, in testing, so a regex now holds those back for a human. *A prompt instruction is not a safety property.*
- **Escalation rule:** three failed agent attempts, then stop and ask a human. Past that the agent is guessing, and someone who does not read code cannot tell the difference.

Unattended auto-merging is acceptable **only** because the site has no users and no payment code yet. This must be revisited before payments are wired in.

---

## 7. The product

**Wedge:** occasion-specific, Bahasa-first, with locally buyable items. At least six English-first competitors use some version of the "FaceCard" name and none own the term; they compete on paid acquisition. The operator's real edge is professional SEO and SEM skill in a market the incumbents do not serve in-language.

**Stack:** Next.js on Vercel, deliberately not Streamlit or a Python web framework, because client-rendered pages cannot be indexed and SEO is the entire thesis.

**Payments:** QRIS direct, no gateway. Revised 2026-07-26. This is a personal business with no entity, and Xendit and most aggregators want one. It turns out not to matter: Bank Indonesia sets MDR for Usaha Mikro Individu at **0% on transactions of Rp 500.000 or less**, so a Rp 39.000 ticket costs nothing to collect. The old worry that fixed per-transaction fees would force the price to Rp 59.000 only applied because a gateway was assumed. The trade is that a static QRIS code cannot notify anything, so payment confirmation is a human step in `#payments`. MDR may not be passed to the customer, so no "biaya admin" line. iPaymu and GDCPay onboard individuals with a KTP if callbacks ever become worth the fee.

**Phasing:** Phase A builds the entire flow with hardcoded fake content, needing no signups or API keys, so the flow and design can be judged before spending anything and so the AI is the only new variable when it is added. Then B (AI), C (database and email), D (payments), E (SEO content).

**Standing risks:**
- Selfie handling is existential. Paid Gemini tier only (free tier may train on prompts), delete after generation, state the policy. Tested manually every release.
- Email must use a separate personal Brevo account. The operator's employer's Brevo and its lists are a work asset and must not be borrowed.
- Prices are set in the Xendit dashboard, never in code.

---

## 8. What is next

1. Finish Vercel connection so every agent branch produces a preview link.
2. Run Phase A: 8 queued jobs, whole flow with fake data.
3. Judge the fake report page. If the layout is not worth Rp 39.000, stop and rethink before wiring anything real.
4. Generate a static QRIS from the banking app and put it on the checkout screen. No signup, no verification, no fees at this ticket size.

Open decisions: brand name and domain, final price, report delivery as PDF or hosted page, whether v1 covers women only.

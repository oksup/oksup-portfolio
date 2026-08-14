# Build Plan

Revised 2026-07-25 after reviewing the original blueprint. The architecture from `Context_Summary.md` holds. The build order does not, and is inverted here.

---

## The one change that matters

The blueprint builds infrastructure first: five self-hosted services, then the agent. That is backwards.

Counting real containers, not logical services:

| Service | Actually needs |
|---|---|
| Outline | Postgres + Redis + S3-compatible storage |
| Plane | Postgres + Redis + MinIO + several app containers |
| Forgejo | Postgres |
| SigNoz | ClickHouse + Zookeeper + collector (4GB RAM hard minimum, 1.5-2GB at idle) |
| OpenPanel | ClickHouse + Redis |

That is roughly 15 to 20 containers, four separate databases, and weeks of Docker debugging before a single agent message has ever been handled. At the end of it you would still not know whether your tool schemas work.

**Inverted order:** build the agent loop against stub backends, prove the pattern, then replace stubs with real services one at a time, only when the stub actually hurts.

The CLI wrapper pattern is what makes this safe. A tool is a function with a schema. Whether its body writes to SQLite or shells out to `plane-cli` is invisible to the agent, the registry, and the bot. Swapping is a body edit.

---

## Phases

| Phase | What ships | Backends | Where | Cost |
|---|---|---|---|---|
| **0** | Product one-pager | none | paper | $0 |
| **1** | Discord agent, 2 channels, 7 tools, evals | SQLite + markdown files | your Mac | $0 |
| **2** | Product tool + `#code` with GitHub read | + `gh` CLI | your Mac | $0 |
| **3** | Always-on | same | $6-12 VPS | ~$8/mo |
| **4** | Real trackers | Plane + Outline (Docker) | 8GB VPS | ~$15-25/mo |
| **5** | Payments + analytics | Xendit/Stripe webhooks, OpenPanel | same | + per transaction |
| **6** | Observability | SigNoz, needs its own headroom | 16GB VPS | ~$35-50/mo |

Phase 6 is genuinely optional. Until you have paying users, a log file and a `#alerts` webhook do the same job for free.

**Realistic cost through phase 4: under $25/month.** The blueprint's $15-35 estimate is achievable, just not for the full stack it describes. The full stack lands closer to $50.

---

## Model strategy

Decided 2026-07-25: **Gemini, because a Claude.ai subscription does not include API access.** The Claude Platform API is separate billing, so building on Claude means turning on pay-per-token from day one. Not worth it for phase 1.

The quality split that actually matters:

- **Opus (Cowork) as the architect.** Design, tool schemas, code review, debugging. Already paid for.
- **Gemini as the runtime.** It only has to pick the right tool from a short list, which is a much easier job than writing the code that defines the list.

Within Gemini:

| | Model | When |
|---|---|---|
| Building | **Pro**, forced on every channel via `FORCE_ROLE=smart` | Phase 1-2. Removes "is it the model or is it me" from every debug session. |
| Running | **Flash** for parse/classify/simple calls, **Pro** for code and money | After evals pass per channel. |

The downgrade is per channel, decided by eval pass rate, never global. `#tasks` on Flash and `#code` on Pro is the correct end state.

**LiteLLM stays regardless.** Nothing imports `google.genai` or `anthropic` directly. If Gemini pricing moves or Claude gets a cheap tier, the swap is `config.py`.

**Free tier caveat:** free-tier prompts may be used to train Google's models, and RPM caps sit around 5-15. Fine for `create_task("test")`. Move to pay-as-you-go before real product logic flows through it.

---

## Quality levers, ranked

Given a cheaper model at runtime, these are what keep accuracy high. Roughly in order of impact:

1. **Short tool lists per channel.** Choosing between 4 tools is a different problem from choosing between 30. This is why channel scoping is a quality feature and not just a security one. Over ~8 tools in a channel, split the channel.
2. **Descriptions that say when NOT to use the tool.** Most misfires are two plausible readings of an ambiguous description, not the model being stupid.
3. **Worked examples per channel** (`CHANNEL_HINTS` in `registry.py`). Show the ambiguous cases. Include at least one "no tool needed" example.
4. **Enums over free-form strings** in schemas. `status: enum[open, done, all]` cannot be got wrong the way a free string can.
5. **`temperature=0`.** Tool selection should not be a dice roll, and it makes evals reproducible.
6. **Errors as readable strings, never exceptions.** `execute()` catches everything and returns text the model can act on. A crashed bot teaches the model nothing.
7. **Step cap** (`MAX_STEPS=6`). Bounds the damage and the bill when a loop goes wrong.
8. **Evals before and after every change.** Non-negotiable. It is the only way to know a prompt edit fixed one case without breaking two others.

---

## Safety rules, carried forward and sharpened

The blueprint's four rules were right. Made concrete:

| Rule | Where it lives now |
|---|---|
| Channel scoping | `registry.CHANNEL_TOOLS` plus a second allowlist check in `tools.base.execute()`. Two layers, deliberately. |
| Non-interactive execution | `tools.base.run_cli()` forces `capture_output`, no TTY, hard timeout |
| Execution guardrails | `TOOL_TIMEOUT_SECONDS=30`, `MAX_STEPS=6`, `high_impact=True` tools blocked without `confirm=true` |
| Data privacy | Pay-as-you-go tier before real business content flows |

Two the blueprint was missing, needed before phase 4:

- **Secrets.** Phase 1-3 use `.env`, gitignored. Before anything touches money, move to Docker secrets or Infisical. Never a plaintext key on a box an agent can read.
- **Blast radius.** Before the agent gets git write or deploy rights: off-VPS backups, branch protection on main, and deploys behind an explicit confirm tool. An agent with push access and no gate can break prod while you sleep.

---

## Open questions

| # | Question | Status |
|---|---|---|
| 1 | What is the product? | **Blocking phase 0.** Everything downstream is shaped by it. |
| 2 | VPS provider and size | Deferred to phase 3. Decide when you want it running with the laptop closed. |
| 3 | Which channels ship when | Resolved: `#tasks` + `#wiki` in phase 1, `#code` in phase 2, rest as their tools become real. |
| 4 | Secrets management | Deferred to phase 4, `.env` until then. |
| 5 | Does `plane-cli` exist | Resolved: yes. Community CLIs (cpatrickalves, aaronshaf) plus an official MCP server. Note Plane's own "Prime CLI" is for instance management, not issues. |
| 6 | Backup and blast radius | Open. Must close before phase 4. |

---

## What is out of scope, and why

The blueprint's "idea → spec → code → deploy → market → monetise, unattended" is not achievable today. Agents are good at scoped tasks with a human reviewing output. They are not good at owning a product end to end without supervision.

This does not weaken the plan, it just relocates the value. The realistic win is compressing the boring middle: spec drafting, task breakdown, boilerplate, PR descriptions, log triage, changelog writing. You stay the one who decides what gets built and whether it shipped correctly. That is `human-on-the-loop`, which the original doc already said. The build just needs to match it.

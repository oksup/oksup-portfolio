# 24/7 Autonomous AI-Agent Control Plane: Context Summary

*Captured 2026-07-25. Status: concept / blueprint, nothing built yet.*

---

## 1. Vision & Core Philosophy

- **Goal:** an autonomous, 24/7 business system. Inspired by founder @radjathaher (creator of FaceCard.fyi).
- **Operating model ("Lazymaxxing"):** human is CEO/strategist (human-on-the-loop), providing vision and approving milestones. An AI agent swarm is the workforce, executing end to end: idea → spec → code → deploy → market → monetise.
- **Target LLM engine:** standardised entirely on the **Gemini API** (Google AI Studio) for cost efficiency, large context window, and native function calling.

---

## 2. Architecture: "One Agent, Many CLIs"

No consumer chat apps, no fleet of separate bots. A single headless orchestrator on a VPS.

**Control plane:** a private Discord server acting as the virtual company office.

| Channel | Purpose | Integration |
|---|---|---|
| `#wiki` | Raw ideas converted into technical specs | Outline |
| `#tasks` | Task breakdown and management | Plane |
| `#design` | Visual specs and UI layouts | Paper |
| `#code` | Git commits, PRs, code generation | Forgejo |
| `#deployments` | CI/CD status and build alerts | ArgoCD / Cloudflare / Actions |
| `#alerts` | Crash and performance monitoring | SigNoz |
| `#analytics` | Funnel performance, drop-off tracking | OpenPanel |
| `#payments` | Transaction webhooks, revenue alerts | Xendit / Stripe |

**CLI wrapper pattern:** the orchestrator never gives the LLM raw terminal access. Each system feature is wrapped in a deterministic, scoped CLI tool exposed to Gemini via native function calling (`google-genai` Python SDK).

---

## 3. Tech Stack & Infrastructure

| Layer | Technology | Hosting / Billing |
|---|---|---|
| Orchestrator | Python (`discord.py` + `google-genai` SDK) | Self-hosted on VPS |
| LLM engine | Gemini API (`gemini-2.5-flash` / `gemini-2.5-pro`) | Google AI Studio, pay-as-you-go |
| Control UI | Discord webhooks + bot gateway | Free |
| Wiki / knowledge | Outline | Self-hosted (Docker) |
| Task tracker | Plane | Self-hosted (Docker) |
| Git repository | Forgejo | Self-hosted (Docker) |
| Observability | SigNoz | Self-hosted (Docker) |
| Analytics | OpenPanel | Self-hosted (Docker) |
| Payments | Xendit / Stripe | Webhook, pay per transaction |

---

## 4. Cost Structure & Model Strategy

**Total estimated cost: ~$15 to $35 / month** (vs $300-800/mo for commercial SaaS equivalents).

| Item | Cost |
|---|---|
| VPS (Hetzner / DigitalOcean / Contabo, mid-tier Linux) | $10-20/mo |
| Domain & DNS (Cloudflare free tier for DNS/SSL) | $1-2/mo |
| Gemini API | $0 during development (free-tier daily quota); pennies per million tokens in production |

**Routing strategy:**

- **Gemini Flash / Flash-Lite:** 90% of high-frequency work (channel listening, webhook parsing, task creation, log checking).
- **Gemini Pro / Claude Sonnet (optional):** reserved for complex code generation and architectural decisions.

---

## 5. Security & Safety Rules

1. **Channel scoping:** tools mapped strictly by Discord channel. `#tasks` only loads `plane_cli`; `#code` only loads `forgejo_cli`.
2. **Non-interactive execution:** all CLI wrappers forced to non-interactive output (`--json`, `--no-input`).
3. **Execution guardrails:** subprocess timeouts (30s), and high-impact actions require an explicit confirmation parameter.
4. **Data privacy:** use the paid Gemini API tier when live so prompt data stays private and exempt from model training.

---

## 6. Implementation Blueprint (Python orchestrator)

```python
from google import genai
import discord
import subprocess
import json

# Initialize Gemini Client
client = genai.Client(api_key="GEMINI_API_KEY")

# Define Agent Tool Wrapper
def run_plane_cli(action: str, title: str) -> str:
    """Interacts with Plane issue tracker."""
    cmd = ["plane-cli", action, "--title", title, "--json"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return res.stdout

# Tool Registry mapped to channels
CHANNEL_TOOLS = {
    "tasks": [run_plane_cli]
}

# Core orchestrator loop, inside the discord.py event handler:
# 1. Capture message in channel
# 2. Pass to client.models.generate_content with tools=CHANNEL_TOOLS[channel]
# 3. Check response.function_calls -> execute local tool -> feed result back
# 4. Post final result back to the Discord channel
```

---

## 7. Open Questions (Tara's flags)

| # | Question | Why it matters |
|---|---|---|
| 1 | What is the first product this swarm actually ships? | The control plane is infrastructure. Without a target product it is a hobby build with recurring VPS cost. |
| 2 | Which VPS and what specs? | Outline + Plane + Forgejo + SigNoz + OpenPanel is 5 Docker stacks. SigNoz alone (ClickHouse) wants 4GB+ RAM. $10/mo is likely optimistic; budget closer to $25-40/mo or drop SigNoz early. |
| 3 | Do all 8 channels ship at once? | Suggest phase 1 = `#tasks` + `#code` only. Prove the wrapper pattern before adding observability and payments. |
| 4 | Where do secrets live? | Gemini key, Forgejo token, Xendit key. Needs a decision (env file vs Docker secrets vs Infisical) before any of this touches money. |
| 5 | Does a `plane-cli` binary actually exist? | Plane ships a REST API; the CLI in the blueprint may need to be written first. Same check needed for Outline and Forgejo. |
| 6 | Backup and blast radius? | An agent with git write and deploy access can break prod at 3am. Confirmation gates and off-VPS backups are prerequisites, not nice-to-haves. |

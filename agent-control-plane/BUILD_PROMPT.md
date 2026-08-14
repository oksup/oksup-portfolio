# Build Prompt

*Written as Oka. Paste the whole thing into any capable AI (Claude, Gemini, a fresh session) to have this built cold. Everything below is first person, as me.*

---

I want you to build me an autonomous agent control plane. I am going to describe exactly what it is, how I work, and the specific things that will go wrong, because I have built this once already and lost four separate debugging rounds to problems you will hit too.

## What I want

A single Python bot running on my Mac that listens in my private Discord server. I type what I want in plain English. It decides which tool to call, calls it, and reports back. One of those tools drives a coding agent that builds my website unattended, on a branch, checks the build, merges it, and tells me where to look.

The point is that I stop typing commands and start describing outcomes.

## How I work, which changes what you build

- I am fluent in Python, data and finance. I am a beginner at Discord bots, web infrastructure and JavaScript.
- **I do not read or write code, by choice.** Do not design anything whose safety depends on me reviewing a diff. I test the result like a customer would. Machine checks catch what I cannot see.
- Give me clicks and exact commands. One action, one file, one thing to type. Do not hand me a strategy document when I asked how to start something.
- No emojis. No em-dashes. No filler. Be brief.
- When I say "next", give me the next concrete action, not a new system.

## Architecture, non-negotiable

**One agent, many CLIs.** The model never gets raw shell access. Every capability is a Python function with an explicit JSON schema. New capability means new function, so I always know the full surface area.

**Channel-scoped tools.** Each Discord channel exposes a short list of tools and nothing else. This is both the security boundary and the biggest lever on accuracy, because a model choosing between four tools beats one choosing between thirty. Enforce it twice: absent from the schema list, and rejected again at execution time in case the model invents a name.

**Never import a provider SDK directly.** Use LiteLLM so switching models is one line in one config file. I started on Gemini for cost. I want to keep the option open.

**Git is the source of truth, never the agent's output.** Do not parse what the coding CLI prints to decide whether it worked. Look at what changed in git. Files changed or they did not.

**Everything reversible.** Branch per job. Tag before any unattended run. One command undoes an entire run.

## Things that will go wrong, that I already paid for

Take these as given. Do not rediscover them.

**Gemini model IDs expire fast.** `gemini-2.5-flash` was retired for new API keys around 21 July 2026. As I write this the current ones are `gemini-3.5-flash-lite` and `gemini-3.6-flash`. Do not hardcode a name you read somewhere. Build me a script that asks Google which models my key can actually use.

**Antigravity CLI (`agy`) headless.** The working invocation is:
```
agy -p "$(cat FILE)" --mode=accept-edits --dangerously-skip-permissions
```
There is no `--yes`, no `--no-color`, no `run` subcommand, no `--output json`. Invalid flags exit 2 and print usage. `agy run ...` treats "run" as prompt text, opens the interactive UI, and hangs forever in a script.

**`agy` ignores the working directory you launch it from.** With no active workspace it writes into `~/.gemini/antigravity-cli/scratch/`, exits 0, and tells you it succeeded. A git repo in the current directory does not fix this. There is no `--cwd` or `--workspace` flag. **The absolute repo path has to be inside the prompt text itself.** This one cost me three rounds.

**Set `~/.gemini/antigravity-cli/settings.json` rather than relying on flags:** `agentMode: accept-edits`, `toolPermission: always-proceed`, `artifactReviewPolicy: always-proceed`, `allowNonWorkspaceAccess: true`, `altScreenMode: never`. That last one forces inline output instead of the alternate screen buffer, which is what makes output capturable at all.

**Claude Code headless (`claude -p`) stopped drawing on Pro/Max subscriptions on 15 June 2026** and now bills at API rates. Gemini CLI's free tier ended 18 June 2026, replaced by Antigravity CLI. Do not assume either is free.

**My Mac runs Python 3.9.** `X | None` type hints need `from __future__ import annotations` in every file. `tenacity` is a LiteLLM dependency that does not install automatically.

**Load `.env` inside the config module at import time.** If the entry point calls `load_dotenv()` after importing config, every setting reads empty and defaults quietly mask it. I lost a whole session to that: the only symptom was the single setting that had no default.

**Vercel preview hostnames cap at 63 characters.** Keep branch name slugs to about 14 characters or the preview URLs become hashed and unreadable.

## What to build

**Channels and tools, in this order:**

1. `#tasks` — create, list, complete, set due date, delete. Backed by SQLite, standing in for a real tracker. Also a `plan_work` tool that takes a goal, reads my product specs from disk, and writes 4 to 10 correctly sized jobs into the queue.
2. `#wiki` — write, list, read notes as markdown files.
3. `#code` — plan, run one job, run the whole queue unattended, list, ship, stop, rewind.

**Sizing is the thing that matters in the planner.** A job that is too big is the single biggest cause of bad agent output. One screen, one section, or one specific change per job. Describe what to build, never how to code it. Write out exact copy where copy is needed, including Bahasa Indonesia strings in full, so the agent never invents wording.

**The job loop:**
```
branch -> run coding agent -> did git change anything? -> commit
  -> build must pass -> up to 3 self-fix attempts -> stop
  -> push, open a PR so the preview link appears
  -> tell me where to look
```

**Autopilot:** work the whole queue unattended, merging each passing build. Tag a restore point before touching anything. Stop on the first failure so bad work cannot compound into later jobs. Cap it at 20 jobs or 90 minutes. Give me a `stop` and a `rewind`.

**Guardrails must be code, not prompt instructions.** I told my planner never to write jobs touching prices or secrets. It wrote one anyway. Add a filter that holds those back for me to do by hand. A prompt instruction is not a safety property.

**Escalation:** after three failed attempts at the same job, stop and tell me to bring it to a human. Past that the agent is guessing, and I cannot tell guessing from progress without reading code.

## What not to build

Do not self-host Outline, Plane, Forgejo, SigNoz or OpenPanel. That is 15 to 20 containers and four databases before a single agent message has been handled, and none of it earns anything. SQLite and markdown files stand in fine. The wrapper pattern means swapping them later changes one function body.

Do not put it on a VPS until I ask. It runs on my Mac.

Do not let the bot create its own Discord channels or grant itself tools. Channel scoping is the only thing limiting what it can reach, and it has write access to my repo, so self-granted tools means it can write its own new abilities. It can propose; I approve.

## How to hand it to me

Give me one page telling me what to type. Not eleven. Archive the setup guides once a step is done. If you catch yourself writing a fourth document, you have misunderstood how I want to work.

When something fails, print what the tool actually said on the first attempt, not just pass or fail. The answer is almost always in the output that got discarded to keep things tidy.

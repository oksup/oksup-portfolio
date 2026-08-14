# Phase 1 Walkthrough: Discord agent running on your Mac

**Goal:** a Discord bot that takes plain-English messages, decides which tool to call, calls it, and reports back. Channel-scoped, with a confirm gate on anything destructive, and an eval suite that proves it works.

**Time:** 2 to 3 hours, mostly waiting on installs.

**Not in phase 1:** no VPS, no Docker, no Plane, no Outline, no SigNoz. Tasks go in a SQLite file and notes go in markdown files. The whole point of the CLI wrapper pattern is that swapping those for real services later does not touch the agent code.

The code is already written and tested. It lives in `orchestrator/`. You are wiring it up and verifying each piece.

---

## Step 0: Name the product (do this first, 30 minutes)

You picked "a new side product to monetise" as the agent's first job. It does not exist yet, and everything downstream is shaped by it. A tracker with no project in it teaches you nothing.

Fill this in before writing code. Keep it to one page.

```markdown
# Product One-Pager

**What it is (one sentence):**
**Who pays for it:**
**What they do today instead:**
**Why they would switch:**
**First version scope (what ships in week 1):**
**What it costs to run:**
**How money arrives (Stripe? Xendit? one-off? subscription?):**
**How I know it failed (the number that would tell me to stop):**
```

Save it as `Product_One_Pager.md` in this folder. If you cannot fill in "who pays" and "why they would switch," that is the signal to pick a different idea, not to start coding.

Two constraints worth respecting: it should be small enough to ship a v1 in a week, and it should be something you can test yourself without needing someone else's data or approval.

**Checkpoint:** the one-pager exists and you would be willing to show it to someone.

---

## Step 1: Prerequisites

Open Terminal.

```bash
python3 --version
```

You need 3.11 or higher. If you are below that:

```bash
brew install python@3.12
```

**Checkpoint:** `python3 --version` prints 3.11 or higher.

---

## Step 2: Create the Discord server

1. Open Discord. Click the **+** in the left server rail, choose **Create My Own**, then **For me and my friends**.
2. Name it something like `Control Plane`.
3. Delete the default `general` channel to avoid confusion.
4. Create two text channels for now: `tasks` and `wiki`.

Only two. You will add `code`, `deployments`, `alerts`, `analytics`, and `payments` in later phases, once each has a real tool behind it. An empty channel is a channel you have to remember to ignore.

**Checkpoint:** your server has exactly `#tasks` and `#wiki`.

---

## Step 3: Create the bot

1. Go to https://discord.com/developers/applications and sign in.
2. **New Application**, name it `Orchestrator`, accept the terms.
3. Left sidebar, **Bot**.
4. Scroll to **Privileged Gateway Intents** and turn on **MESSAGE CONTENT INTENT**. Save.
   This one is the classic beginner trap. Without it your bot connects fine but every message arrives with empty content, and nothing works with no error explaining why.
5. Scroll up, click **Reset Token**, then **Copy**. Paste it somewhere safe for a minute. You cannot view it again, only reset it.
6. Left sidebar, **OAuth2** -> **URL Generator**.
   - Scopes: check **bot**
   - Bot permissions: check **Send Messages**, **Read Message History**, **View Channels**
7. Copy the generated URL at the bottom, open it in a browser, and invite the bot to your server.

**Checkpoint:** the bot appears in your server's member list, greyed out (offline).

---

## Step 4: Set up the project

```bash
cd ~/Documents/"Cowork OS"/"Personal Projects"/"Agent Control Plane"/orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The install pulls a lot of packages because LiteLLM supports every provider. Give it a minute.

**Checkpoint:**

```bash
python -c "import discord, litellm; print('deps ok')"
```

Prints `deps ok`.

---

## Step 5: Get your Gemini key and fill in .env

1. Go to https://aistudio.google.com/apikey and click **Create API key**.
2. Back in Terminal:

```bash
cp .env.example .env
open -e .env
```

3. Paste your Discord token into `DISCORD_TOKEN=` and your Google key into `GEMINI_API_KEY=`. Save and close.

Leave `FORCE_ROLE=smart` in place. That pins every channel to Gemini Pro while you are building. When something misbehaves you then know it is your schema or your prompt, not the model being too weak to follow instructions. You drop down to Flash in step 10, after the evals pass.

Two things about the free tier, so they do not surprise you:

- Free-tier prompts may be used to improve Google's models. Fine for `create_task("test")`. Not fine once your product one-pager and real business logic are flowing through it. Switch to pay-as-you-go before that happens; it is a billing toggle in AI Studio and costs pennies at your volume.
- Free tier caps at roughly 5 to 15 requests per minute. An always-on bot with you typing at it will occasionally hit that. `config.NUM_RETRIES` handles it with backoff, so you will see a pause rather than an error.

**Checkpoint:** `.env` has both keys filled in. Confirm it is ignored by git:

```bash
cat .gitignore | grep .env
```

---

## Step 6: First run

```bash
python bot.py
```

You should see something like:

```
14:32:01 bot      INFO  connected as Orchestrator#1234 | provider=gemini | models={'fast': 'gemini/gemini-2.5-flash', 'smart': 'gemini/gemini-2.5-pro'}
```

The bot goes green in Discord.

**Checkpoint:** in `#tasks`, type:

```
add a task to build the landing page
```

Expected reply: something like `Created task #1: Build the landing page`. Your terminal shows `tools used: create_task`.

If nothing happens at all, you missed the Message Content Intent in step 3. Go back and turn it on, then restart the bot.

---

## Step 7: Verify the tool loop

Run these in `#tasks`, in order. You are checking that the model picks the right tool from a plain sentence, not that it can chat.

| You type | Expected tool | Expected reply |
|---|---|---|
| `add a task to write pricing copy` | `create_task` | Created task #2 |
| `what's on the list?` | `list_tasks` | Both tasks, both open |
| `1 is done` | `complete_task` | Task #1 marked done |
| `show me everything including finished` | `list_tasks` | #1 done, #2 open |
| `what is the capital of France` | none | Paris, no tool call |

That last row matters as much as the others. A model that reaches for a tool on every message is a model that will eventually reach for the wrong one.

**Checkpoint:** all five behave as described, and the terminal log matches.

---

## Step 8: Verify the safety boundaries

These are the two mechanisms that stop a 3am agent from ruining your week. Test them deliberately.

**The confirm gate.** In `#tasks`:

```
delete task 2
```

The tool returns `BLOCKED: ... requires confirm=true`, the model reads that and asks you to confirm. Then:

```
yes, delete task 2 permanently
```

Now it passes `confirm=true` and the task is gone. Terminal shows both calls.

**Channel scoping.** In `#wiki`:

```
add a task to fix the login bug
```

The model should tell you that belongs in `#tasks` and not call anything. It literally does not have `create_task` in its schema list there. Even if it hallucinated the name, `tools/base.py:execute()` rejects it against the allowlist.

Then confirm `#wiki` works for what it does own:

```
save a note called Pricing Model with the body: three tiers, free, pro and team
what notes do we have
read me the pricing model note
```

**Checkpoint:** the gate blocks then allows, and `#wiki` refuses task creation. Look in `orchestrator/data/` and you will see `tasks.db` and `notes/pricing-model.md`.

---

## Step 9: Run the evals

Stop the bot (Ctrl+C) and run:

```bash
python evals/run_evals.py
```

Twelve cases run against the same `run_agent()` the bot uses. You want 12/12.

```
provider=gemini models={...} force_role=smart
running 12 cases

  1. pass   #tasks  add a task to set up the landing page   expected=create_task  got=create_task
  ...

12/12 passed
```

If a case fails, the fix is almost always one of three things, in this order of likelihood:

1. The tool **description** is ambiguous. The model is choosing between two plausible readings. Rewrite the description to say when to use it and when not to.
2. The **channel hint** in `registry.py` is missing that case. Add the example.
3. The **schema** allows a free-form string where an enum would do. Constrain it.

Fix, re-run, repeat until green. This loop is the actual skill. Everything else is plumbing.

**Checkpoint:** 12/12 on `FORCE_ROLE=smart`.

---

## Step 10: Downgrade to Flash and re-run

This is the moment the cost model kicks in.

```bash
FORCE_ROLE=fast python evals/run_evals.py
```

Three possible outcomes:

- **12/12.** Delete the `FORCE_ROLE` line from `.env`. Per-channel routing in `registry.py` takes over and `#tasks` and `#wiki` run on Flash at roughly a tenth the cost.
- **10 or 11 out of 12.** Look at which cases broke. Usually it is the ambiguous ones. Tighten the description or add a hint, re-run. Prompt fixes recover most Flash failures.
- **Below 10.** Leave that channel on `smart` in `CHANNEL_MODEL`. This is a per-channel decision, not a global one. `#tasks` on Flash and `#code` on Pro is the correct end state, not a compromise.

**Checkpoint:** you know your pass rate on both models and have set `CHANNEL_MODEL` accordingly.

---

## Step 11: Commit it

```bash
cd ~/Documents/"Cowork OS"/"Personal Projects"/"Agent Control Plane"/orchestrator
git init
git add .
git commit -m "Phase 1: channel-scoped Discord agent on Gemini"
```

Confirm `.env` did not go in:

```bash
git show --stat HEAD | grep -c "\.env$"
```

Should print `0`.

**Checkpoint:** clean commit, no secrets.

---

## What you now have

- A working agent loop with a real security boundary, not a demo.
- Two tools you understand end to end.
- An eval suite that catches regressions before Discord does.
- A provider swap that is one line, proven by having run both.

## What to do next, in order

1. **Add one tool for your actual product.** Not a category of tools. One. Whatever the one-pager says the first manual step is, wrap that.
2. **Add `#code` with a GitHub tool.** Use the `gh` CLI through `run_cli()` in `tools/base.py`. Read-only first: list issues, read a file. Write access comes after you trust it.
3. **Then, and only then, consider a VPS.** The trigger is wanting it running while your laptop is closed, not "the blueprint said VPS."

See `Build_Plan.md` for the full phase map.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Bot online, ignores every message | Message Content Intent off | Dev portal -> Bot -> enable, restart |
| `DISCORD_TOKEN missing` | No `.env`, or you are in the wrong folder | `cp .env.example .env`, fill it in |
| `AuthenticationError` from LiteLLM | Bad or unset `GEMINI_API_KEY` | Regenerate at AI Studio, no quotes or spaces around the value |
| `RateLimitError` after several messages | Free-tier RPM cap | Wait a minute, or switch to pay-as-you-go |
| Model invents a tool that does not exist | Too many tools, or vague descriptions | Shorten the channel's tool list, sharpen descriptions |
| `sqlite3.OperationalError: disk I/O error` | Running from a cloud-synced or network folder | Set `DATA_DIR=/Users/you/agent-data` in `.env` |
| `ModuleNotFoundError` | venv not active | `source .venv/bin/activate` |
| Replies are chatty and long | Prompt drift | The system prompt in `config.py` says be terse; check you did not edit it out |

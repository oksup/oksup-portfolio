# How to use it

Everything. One page.

## Start the bot

```bash
~/Documents/"Cowork OS"/"Personal Projects"/"Agent Control Plane"/orchestrator/start
```

Leave the Terminal window open. Ctrl+C stops it.

## One-time setup, three things

**1. Make three more channels in Discord.** Right click the server, Create Channel. Name them exactly:

```
creatives
seo
payments
```

**2. Two notification channels.** Same, but named `deployments` and `alerts`. The bot ignores both on purpose. They connect differently, so do not make a webhook for `alerts`.

`deployments` connects through **GitHub, not Vercel**. Vercel account webhooks are a paid feature and its payload is not the shape Discord accepts. GitHub is free and Discord parses it natively. In your repo: Settings, Webhooks, Add webhook. Payload URL is the Discord URL with `/github` stuck on the end. Content type `application/json`. Choose "let me select individual events", tick **Pull requests** and **Deployment statuses**, untick Pushes. Vercel already comments the preview link on the PR, so it arrives in the channel that way.

`alerts` connects through **Sentry, and uses no webhook URL at all**. Sentry installs a bot instead. Sentry: Settings, Integrations, Discord, Add Installation, pick your server, Authorize. Then Alerts, Create Alert, Issues, and under THEN pick "Send a Discord notification". The channel field wants the channel **ID or URL**, not the name: right click `#alerts` in Discord, Copy Link, paste that.

Sentry can wait. It reports nothing until the site has real traffic, and installing it in the app is its own step (`npx @sentry/wizard@latest -i nextjs`, run by you, not the agent, because it edits config files).

**3. Brevo key.** Open `orchestrator/.env`, fill in these two lines from your personal Brevo account (SMTP & API, API Keys):

```
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
```

Then type `is email working?` in `#payments` to check.

## What to type

### `#code`

| Say | It does |
|---|---|
| `plan phase B` | Writes the jobs for that phase into the queue |
| `run everything` | Builds the whole queue and puts it live |
| `stop` | Halts after the current job |
| `rewind autopilot-0726-1150` | Undoes an entire run |
| anything else, in plain words | Treated as one job. "the heading is too small on my phone" |

### `#tasks`

| Say | It does |
|---|---|
| `what's left?` | Lists the queue |
| `add a task to call the bank besok` | Adds it with a real date |
| `what is this costing me?` | Model spend by channel, plus a monthly run rate |

### `#creatives`

| Say | It does |
|---|---|
| `write me ads for brides` | Five headline and body options |
| `tiktok script for the quiz` | A 20 second spoken script |
| `image ideas for the hero` | Prompts for an image generator |

Copy is written in Bahasa. It will never put a price in an ad, on purpose.

### `#seo`

| Say | It does |
|---|---|
| `keywords for baju kondangan` | A keyword map, one primary keyword per page |
| `title and description for the quiz page` | Metadata, ready to paste |
| `build a page for baju kondangan wanita` | Writes the job and queues it for `#code` |

It leaves search volume blank. It does not know volume and will not invent one.

### `#payments`

| Say | It does |
|---|---|
| `budi@gmail.com paid` | Logs Rp 39.000 received |
| `got 39000 from sari@mail.com ref BCA1234` | Same, with the bank reference |
| `who is waiting?` | Everyone paid but not yet delivered |
| `how much this month?` | Revenue, customers, reports still owed |
| `send budi his report` | Emails it and closes the payment |

You confirm payments by hand: QRIS cannot notify anything. That is why it costs you nothing to collect.

## When something is held

Autopilot merges everything except jobs that touch payment, auth, config or env files. Those stop and you get a PR link. Look at the preview, then `ship agent/whatever-branch` if it is right.

## When it breaks

Paste the error to Claude. Don't ask the bot the same thing a fourth time.

## Where things are

- Your website: `~/dev/style-report`
- The bot: `orchestrator/`
- What to build: `../style-report/Job_Queue.md`
- The roadmap: `Sprint_Plan.md`
- Why you're building it: `../style-report/Product_One_Pager.md`

Old setup guides are in `_archive/` if you ever need to redo a step.

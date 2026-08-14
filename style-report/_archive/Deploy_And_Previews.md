# Deploy, and get preview links

**Goal:** your site is live on the internet, and every job the agent does gets its own test link you can open on your phone. About 20 minutes.

**Why this before building features:** right now, testing means checking out a branch and running a dev server. That is the code-adjacent work you do not want to be doing. After this, the bot hands you a link, you tap it, you say ship or fix.

---

## Part 1: Connect Vercel to GitHub (10 minutes)

Vercel is where the site actually lives. Free for what you are doing.

1. Go to **https://vercel.com/signup**
2. Choose **Continue with GitHub**. Authorise it.
3. On the dashboard, click **Add New** then **Project**.
4. Find `style-report` in the list, click **Import**.
5. Change nothing on the settings page. Vercel recognises Next.js on its own.
6. Click **Deploy**.

Wait two minutes. You get a congratulations screen with a link like `style-report-xxxx.vercel.app`.

**Checkpoint:** open that link on your phone. Your site is on the internet.

---

## Part 2: Confirm previews are on (2 minutes)

This is the part that matters, and it is on by default. Every branch pushed to GitHub gets its own separate URL, so the agent's unfinished work never touches your live site.

To confirm: in Vercel, open your project, click **Settings**, then **Git**. Under **Deploy Hooks** and branch settings you should see production is `main`. Anything not `main` becomes a preview.

Nothing to change. Just know that `main` is live and everything else is a private test copy.

---

## Part 3: Restart the bot

I have taught it to open a pull request for each job, which is where Vercel posts the preview link.

```bash
cd ~/Documents/"Cowork OS"/"Personal Projects"/"Agent Control Plane"/orchestrator
source .venv/bin/activate
python bot.py
```

---

## Part 4: The loop from now on

In `#code`:

```
change the heading to say Temukan Gaya Terbaikmu
```

You get back:

```
agent/change-the-hea-0725-1930 is ready. Build passes.
1 file(s) changed in ~2 min:
  app/page.tsx

Open this, wait about a minute for the preview link to appear, then click it:
https://github.com/okasuprayana/style-report/pull/1

Happy with it? Say: ship agent/change-the-hea-0725-1930
```

Tap the link. On that page a bot comment appears within a minute with **Visit Preview**. Tap that, and you are looking at the change on a real URL, on your phone.

If it is right:

```
ship agent/change-the-hea-0725-1930
```

That merges it, and Vercel redeploys the live site within a minute.

If it is wrong, say what you saw:

```
the heading is right but it is squashed against the top on my phone
```

---

## What you never have to do again

- No `git checkout`
- No `npm run dev`
- No reading a diff
- No terminal at all, once the bot is running

The only terminal command in your life is starting the bot.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| No PR link in the message, just terminal instructions | `gh` is not signed in. Run `gh auth login` and restart the bot. |
| PR opens but no preview link after 3 minutes | Check Vercel's dashboard, the build may have failed there even though it passed locally. Paste the error to me. |
| Preview looks right, live site does not change after shipping | Vercel takes a minute. Refresh. If still stale, check the Deployments tab for a failed production build. |
| "A pull request already exists" | The branch was already pushed once. Harmless, the existing PR is the one to open. |

---

## After this

The site is live and testable. Next is the first real feature, and the build order in `V1_Spec.md` starts at the quiz.

Give the agent one screen at a time. "Build the quiz" is too big and you will get something vague. "Add a page at /quiz with one question, what event are you attending, with four options" is the right size.

# Set up the #code channel

**Goal:** you type a job in Discord, the agent writes the code, and it tells you when it's ready to test. About 30 minutes.

**Before you start:** the skeleton must be done. You need a working app at `~/dev/style-report` that's on GitHub.

---

## Part 1: Add the channel (1 minute)

In Discord, next to "TEXT CHANNELS", click **+**, name it `code`, click **Create Channel**.

---

## Part 2: Install the coding agent (10 minutes)

In Terminal:

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

This puts the program at `~/.local/bin/agy` and adds that folder to your shell settings.

**Now quit Terminal completely with Cmd+Q and open it again.** A new tab is not enough. Shell settings are only read when a fresh Terminal starts, so without this you get `command not found` even though it installed fine.

```bash
agy --version
```

Should print a version number.

**If you get `zsh: command not found: agy`:**

```bash
ls -l ~/.local/bin/agy
```

- **"No such file"** means the install did not actually run. Run the curl command again and read the output for errors.
- **Shows a file** means it installed but your Terminal is not looking there. Fix it with:

  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
  source ~/.zshrc
  ```

Do not install the Homebrew package called `antigravity`. That is the desktop app and it creates a command named `antigravity`, not `agy`. If you prefer Homebrew, the right one is `brew install --cask antigravity-cli`.

Now sign in:

```bash
agy
```

It opens your browser. Sign in with Google. Once you are back at a prompt, press **Ctrl+C** to quit. You only needed it authenticated.

---

## Part 3: Find the invocation that works (5 minutes)

This step exists because of a real bug. Antigravity's scriptable mode currently returns nothing when another program runs it instead of a human. Which command form works depends on your version, so we test rather than guess.

```bash
cd ~/Documents/"Cowork OS"/"Personal Projects"/"Agent Control Plane"/orchestrator
source .venv/bin/activate
python check_agent.py
```

It does two things:

1. Turns off every confirmation prompt in the agent's settings file, so it can never sit waiting for a keypress nobody will make. Your other preferences are kept and the old file is backed up.
2. Tries several ways of running the agent in a throwaway folder, each time asking it to create one file, and checks whether the file appeared.

Takes a few minutes. At the end it prints a line starting with `CODING_AGENT_CMD=`.

**If it says nothing worked:** it now prints exactly what each attempt said. Paste the whole thing to me and I'll read the errors.

---

## Part 4: Put it in your settings (2 minutes)

```bash
open -e .env
```

Add the two lines it printed, plus the repo path:

```
PROJECT_REPO=~/dev/style-report
CODING_AGENT_CMD=agy -p "$(cat {prompt_file})" --mode=accept-edits --dangerously-skip-permissions
AGENT_PROMPT_STYLE=path
```

Leave `{prompt_file}` exactly as it is. That is a placeholder the bot fills in with the job description each time, not something you replace.

Save with Cmd+S, close.

---

## Part 5: Restart and try it

```bash
python bot.py
```

In `#code`, type something small on purpose:

```
change the heading on the home page to say Style Report
```

What should happen:

1. It replies within seconds: `Started on branch agent/change-the-heading-...`
2. Nothing for two to ten minutes. This is normal, it's working.
3. It posts again: which files changed, and that the build passes.

Then check it yourself:

```bash
cd ~/dev/style-report && git checkout agent/change-the-heading-0725-1430 && npm run dev
```

Open localhost:3000. If the heading changed, it worked.

Back in `#code`:

```
ship agent/change-the-heading-0725-1430
```

---

## What protects you

| Rule | What it means |
|---|---|
| Never touches `main` | Every job is a separate branch. Your working code cannot be altered by a job. |
| Build must pass | If the code doesn't compile, the agent has to fix it. You're never shown broken work. |
| Three strikes | After three failed attempts it stops and tells you. It won't loop forever burning quota. |
| One at a time | Two jobs can't edit the same file simultaneously. |
| Clean tree required | If you have unsaved changes it refuses to start, so your work and its work can't tangle. |
| Shipping is explicit | Merging to live code needs you to say it, by name. |

**If a job goes wrong, nothing is lost.** Delete the branch and it's like it never happened:

```bash
cd ~/dev/style-report && git checkout main && git branch -D <branch-name>
```

---

## How to describe a job well

This is the only skill that matters here. The rule: **say what you see and what should happen, never how to build it.**

| Weak | Strong |
|---|---|
| "make the quiz better" | "the quiz is one long page with 8 questions. Make it 8 separate screens with a back button and a progress bar" |
| "it's broken" | "on my phone, after I pick a photo, the Next button does nothing. On my laptop it works fine" |
| "add the report page" | "after the quiz, show a page with the person's colour palette as swatches, their face shape, and 5 outfit suggestions" |

Don't guess at the cause. The agent reads the whole codebase and will do better with your symptom than with your theory.

---

## When it fails

**Three attempts, then stop.** If the agent has failed the same job three times, don't ask again. It's guessing rather than reasoning at that point. Paste the error to me instead.

Other things that will happen:

| What you see | What it means |
|---|---|
| "the agent ran but changed nothing" | Job was too vague. Rewrite it with what you see and what should happen. |
| "Already working on agent/..." | One job at a time. Wait for the first. |
| "You have uncommitted changes" | You edited something by hand. Run `cd ~/dev/style-report && git add . && git commit -m "my changes"` |
| Nothing after 15 minutes | Antigravity's free quota resets roughly every 5 hours. You may have hit it. |
| "Command not found" | Terminal was not restarted after installing. Close it and reopen. |

---

## Next

Once a small job works end to end, give it a real one from `../Style Report/V1_Spec.md`. Start with step 1 or 2 of the build order, not the whole thing.

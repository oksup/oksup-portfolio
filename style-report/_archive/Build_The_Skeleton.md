# Build the Skeleton

**Goal:** your own website running in your browser, saved to GitHub. About 45 minutes.

**Why this first:** a coding agent pointed at an empty folder produces nonsense. It needs a working app to change.

**You are not learning to code here.** You are setting up the workshop the agent works in, and getting one look at what a page is so that "the button does nothing" means something concrete to you later. Your job from here on is describing jobs and testing results, never writing or reading code. See `../Agent Control Plane/Operating_Model.md`.

**Where it goes:** `~/dev/style-report`, not inside the Cowork OS folder. Two reasons. It will download several hundred megabytes of libraries, and later the agent gets write access to this folder, so it should contain nothing but this project. Your specs stay where they are.

---

## Step 1: Check you have Node

Node is to JavaScript what Python is to Python. Open Terminal:

```bash
node --version
```

If you see a number like `v22.x.x`, skip to Step 2.

If you see `command not found`, go to **https://nodejs.org**, download the **LTS** version, open the installer, click through it. Then close Terminal, open it again, and run `node --version` to confirm.

---

## Step 2: Create the app

```bash
mkdir -p ~/dev && cd ~/dev
```

```bash
npx create-next-app@latest style-report --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"
```

If it asks `Ok to proceed? (y)`, type `y` and press Enter. If it asks anything else, just press Enter to take the default.

This takes two or three minutes and prints a lot of text.

**About TypeScript:** you are a Python person and TypeScript will look noisy. Keep it anyway. It checks the code for mistakes automatically, which means when the agent writes something wrong, the error shows up immediately instead of silently breaking a page. You are giving the agent a way to catch itself.

---

## Step 3: See it running

```bash
cd ~/dev/style-report
```

```bash
npm run dev
```

You will see a line with `http://localhost:3000`. Open that in your browser.

That is your website, running on your Mac. Nobody else can see it yet.

**Checkpoint:** a page loads in your browser.

Leave it running for the next step.

---

## Step 4: Prove it's yours (2 minutes, optional but do it)

Open a **second** Terminal window (Cmd+N) so the first one keeps running the site.

```bash
open -e ~/dev/style-report/app/page.tsx
```

TextEdit opens. Ignore everything that looks like code, find any normal English word you can see on the page, and type `Halo Bali` over it. Save with Cmd+S.

Look at your browser. It changed by itself, without you reloading.

**Checkpoint:** your text is on the page.

This is not you learning to code. It is one look at the thing so that when the agent says "I updated the home page," you know what it touched. `app/page.tsx` is your home page. You will not open it again.

---

## Step 5: Turn on version history

Git records every version of your code so nothing is ever permanently broken. This is what makes it safe to let an agent touch things later.

In the second Terminal window:

```bash
cd ~/dev/style-report
```

```bash
git init
```

```bash
git add .
```

```bash
git commit -m "Starting point"
```

If git complains it does not know who you are, run these two with your own details, then repeat the commit:

```bash
git config --global user.name "Oka Suprayana"
git config --global user.email "webdev@nakula.com"
```

**Checkpoint:** `git log --oneline` shows one line.

---

## Step 6: Put it on GitHub

GitHub is the online backup and the place the agent's work will show up for you to review.

Install GitHub's command line tool:

```bash
brew install gh
```

If `brew` is not found, go to **https://brew.sh**, copy the single command on that page, run it, then come back.

Sign in:

```bash
gh auth login
```

Answer the questions: **GitHub.com**, then **HTTPS**, then **Y** to authenticate with your GitHub credentials, then **Login with a web browser**. It shows you a code, press Enter, paste the code in the browser, authorise.

Create the repo and upload:

```bash
gh repo create style-report --private --source=. --push
```

**Checkpoint:**

```bash
gh repo view --web
```

Your browser opens your code on GitHub.

---

## Done. What you now have

- A real website you can change
- Every version saved, so nothing can be permanently broken
- A private copy on GitHub
- A clean folder the agent can be pointed at safely

## Two commands to remember

Start the site:

```bash
cd ~/dev/style-report && npm run dev
```

Save your work:

```bash
cd ~/dev/style-report && git add . && git commit -m "what I changed"
```

---

## Next time

We install Antigravity CLI and add a `#code` channel, so you can type a job in Discord and the agent does it on a branch for you to review.

The `#code` tool will be built so that the agent has to pass automatic checks (does it build, do the types pass) before it is even allowed to tell you a job is finished. You get a link, you click it, you say ship or fix. Read `../Agent Control Plane/Operating_Model.md` for how that loop works.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `command not found: node` | Install from nodejs.org, then close and reopen Terminal |
| `command not found: brew` | Install from brew.sh, then close and reopen Terminal |
| `npm run dev` fails with a port error | Something else is on port 3000. Run `npm run dev -- -p 3001` and use localhost:3001 |
| Browser shows "This site can't be reached" | The first Terminal window stopped. Go back to it and run `npm run dev` again |
| `Author identity unknown` | Run the two `git config` commands in Step 5 |
| `gh: command not found` | `brew install gh` did not finish. Run it again and read the output |
| Anything else | Paste me the red text |

# Start Here

Ignore every other file in this folder. This is the only one you need today.

**Goal:** you type "add a task to buy milk" in a chat window, and a bot replies "Created task #1: Buy milk". That is it. About 45 minutes.

**Cost:** nothing. No credit card anywhere in this guide.

---

## First, what are these things?

**Discord** is a free chat app. Like WhatsApp, but you can make your own private space.

**A server** is your private space inside Discord. It is free, it takes two clicks, and you are the only person in it.

**A channel** is a room inside your server. Like a WhatsApp group, but for one topic. We will make two.

**A bot** is a small program that sits in your server and reads what you type. That program is the code already sitting in the `orchestrator` folder. You are not writing it. You are just plugging it in.

**A token** is a long password that lets your program log into Discord as the bot.

**An API key** is a long password that lets your program talk to Google's AI.

That is the whole vocabulary. Nothing else to learn.

---

## Part 1: Get Discord (5 minutes)

1. Go to **https://discord.com/download** and install it on your Mac.
2. Open it and sign up. Any email, any password.

You now have Discord. Nothing to build.

---

## Part 2: Make your private space (5 minutes)

1. On the far left of the Discord window there is a vertical strip of circles. At the bottom of it is a **+** button. Click it.
2. Click **Create My Own**.
3. Click **For me and my friends**.
4. Name it `Control Plane`. Click **Create**.

You now have a server. On the left you will see a channel called `# general`.

5. Hover over `# general`, click the small gear icon that appears, scroll to the bottom, click **Delete Channel**, confirm.
6. Next to where it said "TEXT CHANNELS", click the **+**. Name it `tasks`. Click **Create Channel**.
7. Do it again. Name it `wiki`.

You should now see exactly two channels: `# tasks` and `# wiki`.

---

## Part 3: Create the bot (15 minutes)

This part has the most clicks and is the part people get stuck on. Go slowly.

1. Open **https://discord.com/developers/applications** in your browser. Sign in with the same account.
2. Top right, click **New Application**.
3. Name it `Orchestrator`. Tick the box to agree to the terms. Click **Create**.
4. On the left sidebar, click **Bot**.
5. Scroll down until you see a section called **Privileged Gateway Intents**.
6. Find the switch labelled **MESSAGE CONTENT INTENT** and turn it **ON**.
7. Scroll to the bottom and click **Save Changes**.

**Do not skip step 6.** Without it the bot will connect fine and then ignore every message you send, with no error telling you why. This is the single most common place beginners get stuck.

8. Scroll back to the top of that Bot page. Click **Reset Token**, then **Yes, do it!**.
9. Click **Copy**. Open TextEdit and paste it there for now. You cannot see this token again later, only make a new one.

Now you invite the bot to your server.

10. On the left sidebar, click **OAuth2**.
11. Scroll to **OAuth2 URL Generator**. In the **SCOPES** box, tick **bot**.
12. A new box appears below called **BOT PERMISSIONS**. Tick these three:
    - **Send Messages**
    - **Read Message History**
    - **View Channels**
13. Scroll to the very bottom. There is a long URL in a box. Click **Copy**.
14. Paste that URL into a new browser tab and press Enter.
15. Choose `Control Plane` from the dropdown. Click **Continue**, then **Authorize**. Solve the captcha if it asks.

Go back to Discord. On the right side of your server you will see a member list. `Orchestrator` is now in it, greyed out. Greyed out means offline, which is correct. It is offline because you have not started the program yet.

---

## Part 4: Get your free Google AI key (5 minutes)

1. Go to **https://aistudio.google.com/apikey**.
2. Sign in with a Google account.
3. Click **Create API key**. If it asks you to pick a project, let it make a new one.
4. Click the copy button. Paste it into the same TextEdit note, under your Discord token.

This is free. It does not ask for a card.

---

## Part 5: Set up the code (10 minutes)

Open the **Terminal** app on your Mac. Press Cmd+Space, type `terminal`, press Enter.

Copy and paste each of these lines one at a time. Press Enter after each and wait for it to finish before doing the next.

```bash
cd ~/Documents/"Cowork OS"/"Personal Projects"/"Agent Control Plane"/orchestrator
```

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

After that one, your Terminal line should now start with `(.venv)`. That is normal and means it worked.

```bash
pip install -r requirements.txt
```

This one takes two or three minutes and prints a lot of text. Let it finish.

Now make your settings file:

```bash
cp .env.example .env
```

```bash
open -e .env
```

A TextEdit window opens. You will see lines like `DISCORD_TOKEN=` and `GEMINI_API_KEY=`.

Paste your Discord token right after the `=` on the `DISCORD_TOKEN=` line. No spaces, no quotes.
Paste your Google key right after the `=` on the `GEMINI_API_KEY=` line.

It should look like this (with your own long strings):

```
DISCORD_TOKEN=MTIzNDU2Nzg5...
GEMINI_API_KEY=AIzaSyD...
```

Save with Cmd+S and close the window.

---

## Part 6: Turn it on

Back in Terminal:

```bash
python bot.py
```

You should see a line appear that says `connected as Orchestrator...`.

Go look at Discord. `Orchestrator` in the member list is now green.

**Leave this Terminal window open.** The bot is only running while it is open. Closing it turns the bot off.

---

## Part 7: Talk to it

Click on `# tasks` in Discord and type:

```
add a task to buy milk
```

It should reply something like `Created task #1: Buy milk`.

Now try these, one at a time:

| Type this | It should |
|---|---|
| `add a task to call the bank` | Make a second task |
| `what's on my list?` | Show you both tasks |
| `1 is done` | Mark the first one finished |
| `what is the capital of France` | Just answer Paris, no task |

Then click on `# wiki` and type:

```
add a task to fix something
```

It should tell you that belongs in the tasks channel and refuse. That is the safety boundary working: the bot can only touch tasks in the tasks room.

---

## That is it. You are done.

You now have a working AI agent. It reads plain English, decides what to do, does it, and tells you.

To turn it off: click the Terminal window and press **Ctrl+C**.

To turn it on again later:

```bash
cd ~/Documents/"Cowork OS"/"Personal Projects"/"Agent Control Plane"/orchestrator
source .venv/bin/activate
python bot.py
```

Those three lines are all you ever need to start it.

---

## If something went wrong

| What you see | What to do |
|---|---|
| Bot is green but ignores everything you type | You missed **MESSAGE CONTENT INTENT** in Part 3, step 6. Go turn it on, then press Ctrl+C in Terminal and run `python bot.py` again. |
| `DISCORD_TOKEN missing` | Your `.env` file is empty or you are in the wrong folder. Redo Part 5. |
| `command not found: python3` | Run `brew install python@3.12`, then start Part 5 again. |
| `ModuleNotFoundError` | You forgot `source .venv/bin/activate`. Run it, then try again. |
| Something about `AuthenticationError` | Your Google key is wrong. Make a new one at aistudio.google.com/apikey and paste it in again, with no spaces around it. |
| Something about `RateLimitError` | You are typing faster than the free allowance. Wait one minute. |
| `TypeError: unsupported operand type(s) for \|` | Old Python. Already fixed in the code, just run `python bot.py` again. |
| Anything else | Copy the whole red error text, paste it to me, and I will tell you what it means. |

---

## What happens after this

Nothing today. Get it running, play with it for ten minutes, then stop.

When you come back, tell me it works and I will show you how to add one new thing it can do. One at a time, no strategy documents.

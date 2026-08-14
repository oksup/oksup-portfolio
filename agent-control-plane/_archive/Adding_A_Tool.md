# How to add a new tool

Worked example: the deadline feature we just added. Every future tool follows these same five steps.

---

## The big idea first

Your bot has two halves, and they have opposite jobs.

**The model** handles messy human language. It figures out that "by friday" means `2026-07-31`.

**The tool** is dumb and strict on purpose. It only accepts `2026-07-31`. If you hand it "friday" it refuses.

Beginners usually try to make the tool clever, teaching it to understand "friday" and "besok" and "next week". Don't. Every bit of cleverness you put in the tool is a bit you have to debug, and a bit that can silently get it wrong. Put the fuzzy part in the prompt where the model already handles it, keep the code exact.

That split is the whole craft. Everything else is typing.

---

## The five places a tool touches

### 1. Write the function (`tools/tasks.py`)

```python
@tool(
    name="set_due_date",
    description="Set, change or clear the deadline on a task that already exists.",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer"},
            "due_date": {"type": "string", "description": "YYYY-MM-DD only."},
        },
        "required": ["task_id", "due_date"],
    },
)
def set_due_date(task_id: int, due_date: str = "") -> str:
    ...
```

The `description` fields are not documentation. They are the only thing the model reads when deciding whether to use this tool. Vague description, wrong tool chosen. This is where almost every bug lives.

### 2. Let the channel see it (`registry.py`)

```python
"tasks": ["create_task", "list_tasks", "set_due_date", "complete_task", "delete_task"],
```

A tool not in this list does not exist as far as that channel is concerned. That is your safety boundary.

### 3. Show an example (`registry.py`, `CHANNEL_HINTS`)

```
- "push task 3 to next monday" -> set_due_date(task_id=3, due_date="2026-08-03")
```

One or two examples is the cheapest accuracy improvement available. Show the confusing cases, not the obvious ones.

### 4. Add test cases (`evals/cases.jsonl`)

```json
{"channel": "tasks", "message": "push task 3 to next monday", "expect_tool": "set_due_date"}
```

Always add a nearby case that should **not** fire the new tool. A tool that fires too eagerly is worse than one that never fires.

### 5. Restart the bot

Ctrl+C, then `python bot.py`. There is no reload; the code loads once at startup.

---

## Two extra things this change needed

**The bot didn't know today's date.** Obvious in hindsight. It cannot work out "friday" without it. It's now added to the prompt in `agent.py`, computed fresh on every message rather than once at startup, so a bot left running for a week doesn't still think it's the day you launched it.

**A parameter beat a new tool.** For "what's overdue?" I didn't write a `list_overdue` tool. I added `overdue` to the existing `list_tasks` status options. Fewer tools means better tool-picking, so when you can express something as a parameter on a tool that already exists, do that instead. Add a new tool only when the action is genuinely different.

---

## Your existing tasks are safe

The database gains a `due_date` column automatically the first time the new code runs. Your old tasks stay exactly as they are, just with no deadline set, which you can add later with "task 1 is due friday". Nothing is deleted or rewritten. I tested this against a database created with the old layout.

---

## Try it yourself

Add a `priority` field to tasks (high, normal, low). It touches the same five places and there is nothing new to learn, which is the point. Use an `enum` in the schema like `status` does, so the model cannot invent "super urgent".

If you get stuck, paste me what you wrote.

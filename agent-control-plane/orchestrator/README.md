# Orchestrator

Phase 1 of the Agent Control Plane. A Discord bot that routes plain-English messages to channel-scoped tools via Gemini.

Setup instructions: `../_archive/Phase_1_Walkthrough.md`. Phase map: `../_archive/Build_Plan.md`.

## Run

```bash
source .venv/bin/activate
python bot.py                              # start the bot
python evals/run_evals.py                  # check nothing regressed
FORCE_ROLE=fast python evals/run_evals.py  # check the cheap model still holds
```

## Files

| File | Job |
|---|---|
| `config.py` | The only file that names a model. Provider swap happens here. |
| `llm.py` | The only file that calls an LLM. Wraps LiteLLM. |
| `agent.py` | The loop: ask model, run tools, feed results back, repeat. No Discord in it, so evals drive the same code path the bot does. |
| `bot.py` | Discord front end. Thin on purpose. |
| `registry.py` | Which tools and which model each channel gets. The security boundary. |
| `tools/base.py` | Tool registration, schemas, allowlist check, confirm gate, subprocess helper. |
| `tools/tasks.py` | SQLite task tools. Stand-in for Plane. |
| `tools/notes.py` | Markdown note tools. Stand-in for Outline. |
| `evals/` | Cases plus the runner. |

## Adding a tool

1. Write the function in `tools/`, decorate it with `@tool(...)`, give it an explicit JSON schema.
2. Add its name to the right channel in `registry.CHANNEL_TOOLS`.
3. Add an example to `registry.CHANNEL_HINTS` for that channel.
4. Add two eval cases: one where it should fire, one nearby case where it should not.
5. Run the evals on both `FORCE_ROLE=smart` and `FORCE_ROLE=fast`.

Destructive tools get `high_impact=True` and a `confirm` boolean in their schema. `execute()` blocks them until the model passes `confirm=true`.

## Swapping a stub for a real backend

Only the function body changes. Schema, registry, evals, and bot all stay put.

```python
# before
def create_task(title: str, notes: str = "") -> str:
    with _conn() as conn:
        ...

# after
def create_task(title: str, notes: str = "") -> str:
    return run_cli(["plane-cli", "issue", "create", "--title", title, "--json"])
```

`run_cli()` already enforces non-interactive execution and a 30 second timeout.

"""
Finds a way to run your coding agent from a script that actually works.

Two jobs:
  1. Make sure the agent's settings file has confirmations turned off, so it
     cannot sit waiting for a keypress nobody will make.
  2. Try each known invocation in a throwaway folder and report which one
     actually created a file.

Run:  python check_agent.py

Then copy the winning line into .env as CODING_AGENT_CMD.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile

# Flags verified against antigravity.google/docs/cli/modes (CLI v1.1.5).
# There is no --yes, no --no-color, and no `run` subcommand. --mode=accept-edits
# is what auto-approves file writes; --dangerously-skip-permissions covers
# shell commands.
CANDIDATES = [
    {
        "binary": "agy",
        "cmd": 'agy -p "$(cat {prompt_file})" --mode=accept-edits --dangerously-skip-permissions',
    },
    {
        # Fakes a terminal. Needed if your version drops output when piped.
        "binary": "agy",
        "cmd": 'script -q /dev/null agy -p "$(cat {prompt_file})" --mode=accept-edits --dangerously-skip-permissions',
    },
    {
        "binary": "agy",
        "cmd": 'agy -p "$(cat {prompt_file})" --mode=accept-edits',
    },
    {
        # Costs money per run. Only if the free ones fail.
        "binary": "claude",
        "cmd": 'claude -p "$(cat {prompt_file})" --permission-mode acceptEdits',
    },
]

SETTINGS_PATH = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")

# Turns off every prompt and forces plain inline output, which is what makes
# the CLI usable from a script. allowNonWorkspaceAccess lets it write to a
# folder we name in the prompt rather than only its own workspace root.
HEADLESS_SETTINGS = {
    "agentMode": "accept-edits",
    "toolPermission": "always-proceed",
    "artifactReviewPolicy": "always-proceed",
    "allowNonWorkspaceAccess": True,
    "verbosity": "low",
    "altScreenMode": "never",
    "showTips": False,
    "showFeedbackSurvey": False,
    "notifications": False,
}

JOB = "Create a file called PONG.txt containing exactly the word PONG. Do nothing else."

# agy has no flag for "work in this folder", so the path has to be carried in
# the instruction. These are the ways of saying it, worth testing rather than
# guessing, because with no workspace set it writes to its own scratch folder
# and still reports success.
PROMPT_STYLES = {
    "path": (
        "Work inside the git repository at {repo}.\n"
        "Every file you create or edit must be inside that folder.\n\n{job}"
    ),
    "abspath": (
        "Work in {repo}. Use absolute paths starting with {repo} for every "
        "file you create or edit. Do not use a scratch folder.\n\n{job}"
    ),
    "adddir": "/add-dir {repo}\n\n{job}",
    "plain": "{job}",
}

TIMEOUT = 240


def fix_settings() -> None:
    """Merge the headless keys into the agent's settings file, keeping a backup."""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)

    current = {}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as fh:
                current = json.load(fh)
        except (json.JSONDecodeError, OSError):
            print(f"  (could not read {SETTINGS_PATH}, will write a fresh one)")

    missing = {k: v for k, v in HEADLESS_SETTINGS.items() if current.get(k) != v}
    if not missing:
        print("  settings already correct")
        return

    if os.path.exists(SETTINGS_PATH):
        shutil.copy(SETTINGS_PATH, SETTINGS_PATH + ".backup")
        print(f"  backed up your old settings to {SETTINGS_PATH}.backup")

    current.update(HEADLESS_SETTINGS)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as fh:
        json.dump(current, fh, indent=2)
    print(f"  updated {len(missing)} setting(s) in {SETTINGS_PATH}")


def make_test_repo() -> str:
    """
    A real git repo, because agy works out where it is allowed to write from
    the git root. In a plain folder it ignores the current directory and
    writes into its own scratch space instead, which looks like a failure
    but is really just a missing repo.
    """
    workdir = tempfile.mkdtemp(prefix="agentcheck-")
    with open(os.path.join(workdir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# test\n")
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "user.name", "Test"],
        ["git", "add", "-A"],
        ["git", "commit", "-qm", "init"],
    ):
        subprocess.run(cmd, cwd=workdir, capture_output=True, check=False)
    return workdir


def try_one(cmd_template: str, style: str = "plain") -> tuple[bool, str, str]:
    """Returns (made_the_file, note, output_tail)."""
    workdir = make_test_repo()
    prompt = os.path.join(workdir, "job.md")
    with open(prompt, "w", encoding="utf-8") as fh:
        fh.write(PROMPT_STYLES[style].format(repo=workdir, job=JOB))

    cmd = cmd_template.format(prompt_file=shlex.quote(prompt))
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        made = os.path.exists(os.path.join(workdir, "PONG.txt"))
        note = f"exit {proc.returncode}, {len(out)} chars out"
        # The specific failure worth naming: it did the work, in the wrong place.
        if not made and "scratch" in out:
            note += " - wrote to its own scratch folder, not the repo"
        return made, note, out[-1200:]
    except subprocess.TimeoutExpired:
        return False, f"hung for {TIMEOUT}s (waiting for a prompt that never came)", ""
    except Exception as exc:  # noqa: BLE001
        return False, f"error: {exc}", ""
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    print("\nStep 1: turning off confirmation prompts in the agent's settings")
    fix_settings()

    print("\nStep 2: finding a command form that runs")
    print("Each test asks it to create one file. This takes a few minutes.\n")

    working_cmd = None
    failures = []

    for i, cand in enumerate(CANDIDATES, 1):
        template = cand["cmd"]
        if not shutil.which(cand["binary"]):
            print(f"{i}. skipped   ({cand['binary']} is not installed)")
            continue

        print(f"{i}. testing   {template[:78]}", flush=True)
        made, note, out = try_one(template, "path")

        if made:
            print(f"   WORKS. {note}")
            working_cmd = template
            break
        print(f"   no: {note}")
        failures.append((f"command {i}", template, note, out))

    # If the command runs but writes to the wrong place, the fix is in how we
    # word the instruction, not in the flags. Try the other phrasings.
    winning_style = "path"
    if working_cmd is None and failures:
        ran_but_misplaced = [f for f in failures if "scratch" in f[2]]
        if ran_but_misplaced:
            working_cmd = ran_but_misplaced[0][1]
            print("\nIt runs fine but writes to the wrong folder.")
            print("Trying different ways of telling it where to work.\n")
            for style in ("abspath", "adddir", "plain"):
                print(f"   style '{style}'...", end=" ", flush=True)
                made, note, out = try_one(working_cmd, style)
                if made:
                    print(f"WORKS. {note}")
                    winning_style = style
                    break
                print(f"no: {note}")
                failures.append((f"style {style}", working_cmd, note, out))
            else:
                working_cmd = None

    print("\n" + "=" * 64)

    if working_cmd:
        print("\nSorted. Put these two lines in your .env file:\n")
        print(f"CODING_AGENT_CMD={working_cmd}")
        print(f"AGENT_PROMPT_STYLE={winning_style}\n")
        return 0

    print("\nNothing worked. Here is what each attempt actually said, so Claude")
    print("can tell you why:\n")
    for label, template, note, out in failures:
        print(f"--- {label}: {template}")
        print(f"    {note}")
        if out:
            for line in out.splitlines()[:20]:
                print(f"    | {line}")
        print()
    print("Copy everything above and paste it to Claude.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

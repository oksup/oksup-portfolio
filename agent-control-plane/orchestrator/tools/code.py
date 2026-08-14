"""
Coding tools for the #code channel.

Design notes, because this is the part that can actually break things:

1. GIT IS THE SOURCE OF TRUTH, NOT THE AGENT'S OUTPUT.
   We never trust what the CLI prints. We look at what changed in git. Files
   changed or they did not; that cannot be faked or lost.

2. GATES BEFORE ANYTHING SHIPS.
   The build must pass. If it fails, the agent gets the error back and
   retries, up to MAX_FIX_ATTEMPTS, then stops.

3. EVERY RUN IS REVERSIBLE.
   Autopilot tags the starting commit before it touches anything, so an
   entire unattended run can be undone with one command. This is the whole
   reason unattended merging is survivable.

4. RUNS IN THE BACKGROUND.
   Jobs take minutes. Returning immediately keeps Discord responsive.
"""

from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
import fnmatch
import tempfile
import threading
import time
from datetime import datetime

from config import (
    AGENT_PROMPT_STYLE,
    BUILD_CMD,
    CODING_AGENT_CMD,
    CODING_TIMEOUT_SECONDS,
    MAIN_BRANCH,
    MAX_FIX_ATTEMPTS,
    PROJECT_REPO,
    PROMPT_STYLES,
    PROTECTED_PATHS,
)
from tools import tasks as task_store
from tools.base import tool

log = logging.getLogger("code")

_REPORTER = None
_RUNNING: set[str] = set()
_LOCK = threading.Lock()
_STOP = threading.Event()

# Autopilot limits. A runaway loop should cost minutes, not a whole evening.
MAX_QUEUE_JOBS = 20
MAX_QUEUE_MINUTES = 90


def set_reporter(fn) -> None:
    global _REPORTER
    _REPORTER = fn


def _report(text: str) -> None:
    if _REPORTER:
        try:
            _REPORTER("code", text)
        except Exception:  # noqa: BLE001
            log.exception("could not post result to Discord")
    else:
        log.info("REPORT: %s", text)


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------


def _git(*args: str, timeout: int = 120) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=PROJECT_REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _repo_problem() -> str | None:
    if not os.path.isdir(PROJECT_REPO):
        return f"No repo at {PROJECT_REPO}. Check PROJECT_REPO in .env."
    if not os.path.isdir(os.path.join(PROJECT_REPO, ".git")):
        return f"{PROJECT_REPO} is not a git repository. Run `git init` there."
    if not CODING_AGENT_CMD:
        return (
            "CODING_AGENT_CMD is empty. Three usual causes, in order: (1) .env has "
            "two CODING_AGENT_CMD lines and the empty one from the template wins, "
            "so delete it; (2) the bot was not restarted after editing .env; "
            "(3) run `python check_agent.py` if you never set it."
        )
    if "{prompt_file}" not in CODING_AGENT_CMD:
        return (
            "CODING_AGENT_CMD is missing the {prompt_file} placeholder. Leave that "
            "text exactly as check_agent.py printed it; the bot substitutes it."
        )
    code, out = _git("status", "--porcelain")
    if code != 0:
        return f"git is unhappy: {out}"
    if out:
        return (
            "You have uncommitted changes in the repo. Commit or discard them "
            "first, so the agent's work stays separate from yours."
        )
    return None


def _slug(text: str) -> str:
    # Short because the branch name becomes part of Vercel's preview hostname,
    # capped at 63 characters.
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:14] or "job").rstrip("-")


def _changed_files(base: str) -> list[str]:
    code, out = _git("diff", "--name-only", f"{base}...HEAD")
    return [line for line in out.splitlines() if line] if code == 0 else []


def _open_pr(branch: str, job: str) -> str | None:
    try:
        proc = subprocess.run(
            [
                "gh", "pr", "create",
                "--head", branch,
                "--base", MAIN_BRANCH,
                "--title", job[:70],
                "--body", f"Agent job:\n\n{job}\n\nBuild passed before this was opened.",
            ],
            cwd=PROJECT_REPO,
            capture_output=True,
            text=True,
            timeout=90,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    for line in (proc.stdout or "").splitlines():
        if line.startswith("https://"):
            return line.strip()
    return None


# ---------------------------------------------------------------------------
# Running the coding agent
# ---------------------------------------------------------------------------


def _run_agent_cli(prompt_path: str) -> tuple[int, str]:
    # shell=True on purpose: the working invocation needs $(cat ...). The job
    # text never reaches the shell, only the prompt file path, quoted by us.
    cmd = CODING_AGENT_CMD.format(prompt_file=shlex.quote(prompt_path))
    log.info("running coding agent: %s", cmd)
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=PROJECT_REPO,
            capture_output=True,
            text=True,
            timeout=CODING_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"Agent ran past {CODING_TIMEOUT_SECONDS // 60} minutes and was stopped."
    combined = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 127:
        return 127, f"Command not found. Is the coding agent installed?\n{combined[-300:]}"
    return proc.returncode, combined


def _run_build() -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            shlex.split(BUILD_CMD),
            cwd=PROJECT_REPO,
            capture_output=True,
            text=True,
            timeout=CODING_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return False, f"Build command not found: {BUILD_CMD}"
    except subprocess.TimeoutExpired:
        return False, "Build timed out."
    if proc.returncode == 0:
        return True, ""
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-40:]
    return False, "\n".join(tail)


def _write_prompt(path: str, body: str) -> None:
    """
    Wraps the instruction with the repo path. agy has no flag for this, and
    with no workspace set it writes to its own scratch folder and reports
    success, so the path has to be part of the instruction.
    """
    template = PROMPT_STYLES.get(AGENT_PROMPT_STYLE, PROMPT_STYLES["path"])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(template.format(repo=PROJECT_REPO, job=body))


def _execute_job(job: str, branch: str) -> tuple[bool, str, list[str]]:
    """
    Does one job on its own branch: agent, then build, then fix attempts.

    Returns (ok, message, changed_files). Leaves the branch checked out on
    success so the caller can push, PR, or merge it. Never pushes or merges
    itself; that decision belongs to the caller.
    """
    # Outside the repo, or `git add -A` sweeps the instruction file into the commit.
    fd, prompt_path = tempfile.mkstemp(prefix="agent-job-", suffix=".md")
    os.close(fd)

    try:
        _git("checkout", "-b", branch)
        _write_prompt(
            prompt_path,
            f"{job}\n\n"
            "Rules:\n"
            "- Make the change directly in the files. Do not ask questions.\n"
            "- Keep the change as small as it can be while doing the job.\n"
            "- Do not add new dependencies unless the job cannot be done without one.\n"
            "- Do not touch payment handling, secrets, or environment files.\n",
        )

        rc, output = _run_agent_cli(prompt_path)
        if rc in (124, 127):
            return False, output, []

        _, dirty = _git("status", "--porcelain")
        if not dirty:
            return False, (
                "The agent ran but changed nothing. Usually the job was too vague."
            ), []

        _git("add", "-A")
        _git("commit", "-m", f"agent: {job[:60]}")

        ok, err = _run_build()
        attempts = 1
        while not ok and attempts < MAX_FIX_ATTEMPTS and not _STOP.is_set():
            attempts += 1
            _write_prompt(
                prompt_path,
                "Your last change broke the build. Fix it.\n\n"
                f"The original job was:\n{job}\n\n"
                f"The build failed with:\n{err}\n",
            )
            _run_agent_cli(prompt_path)
            _, dirty = _git("status", "--porcelain")
            if dirty:
                _git("add", "-A")
                _git("commit", "-m", f"agent: fix build (attempt {attempts})")
            ok, err = _run_build()

        files = _changed_files(MAIN_BRANCH)
        if ok:
            return True, "", files
        return False, f"Build still broken after {attempts} attempts.\n{err[-800:]}", files
    finally:
        if os.path.exists(prompt_path):
            os.remove(prompt_path)


def _discard(branch: str, task_id: int | None) -> None:
    _git("checkout", MAIN_BRANCH)
    _git("branch", "-D", branch)
    if task_id:
        task_store.clear_branch(task_id)


# ---------------------------------------------------------------------------
# Manual mode: one job, stops for your approval
# ---------------------------------------------------------------------------


def _job_thread(job: str, branch: str, task_id: int | None = None) -> None:
    started = time.time()
    try:
        ok, err, files = _execute_job(job, branch)
        mins = int((time.time() - started) / 60)

        if not ok:
            _report(f"**{branch}** failed.\n{err}")
            if "Build still broken" in err:
                _report(
                    "Three strikes. Do not ask again, bring this to Claude. "
                    f"Branch kept: `git checkout {branch}`"
                )
                if task_id:
                    task_store.clear_branch(task_id)
            else:
                _discard(branch, task_id)
            return

        _git("push", "-u", "origin", branch)
        pr_url = _open_pr(branch, job)
        file_list = "\n".join(f"  {f}" for f in files[:12])
        where = (
            f"\nOpen this, wait a minute for the preview link, then tap it:\n{pr_url}\n"
            if pr_url
            else f"\nTo test:\n  cd {PROJECT_REPO} && git checkout {branch} && npm run dev\n"
        )
        label = f"Task #{task_id}: " if task_id else ""
        _report(
            f"{label}**{branch}** is ready. Build passes.\n"
            f"{len(files)} file(s) changed in ~{mins} min:\n{file_list}\n"
            f"{where}\nHappy with it? Say: ship {branch}"
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("job thread crashed")
        _report(f"**{branch}** crashed: {exc}")
    finally:
        _git("checkout", MAIN_BRANCH)
        with _LOCK:
            _RUNNING.discard(branch)


_PROTECTED_RE = None


def _glob_re(pattern: str):
    """
    Turn a path glob into a regex. fnmatch is not usable here: its `*` crosses
    slashes, so `**/payments/**` degrades into matching every file.

    `**` matches any number of path segments. `*` matches within one segment.
    """
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
            if pattern.startswith("/", i):
                out += "/?"
                i += 1
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$", re.IGNORECASE)


def _protected_hits(files: list[str]) -> list[str]:
    """
    Files a job touched that must not be merged without a human.

    Second, independent layer from the FORBIDDEN regex in plan.py. That one
    stops such jobs being WRITTEN by the planner. This one stops them being
    MERGED, which also covers jobs typed by hand in #code and jobs where the
    agent wandered into a sensitive file on its own.

    Each pattern is tested against the full path, every path suffix that
    starts at a segment boundary, and every single segment. Deliberately
    over-matches: a false positive costs one manual merge, a false negative
    costs unreviewed payment code.
    """
    global _PROTECTED_RE
    if _PROTECTED_RE is None:
        _PROTECTED_RE = [(p, _glob_re(p)) for p in PROTECTED_PATHS]

    hits = []
    for path in files:
        name = path.replace(os.sep, "/")
        if name.startswith("./"):
            name = name[2:]
        parts = name.split("/")
        candidates = {name}
        candidates.update("/".join(parts[i:]) for i in range(len(parts)))
        candidates.update(parts)
        for _pattern, rx in _PROTECTED_RE:
            if any(rx.match(c) for c in candidates):
                hits.append(path)
                break
    return hits


# ---------------------------------------------------------------------------
# Autopilot: whole queue, unattended, auto-merged
# ---------------------------------------------------------------------------


def _queue_thread(rewind_tag: str) -> None:
    started = time.time()
    done, failed = 0, None
    held: list = []

    try:
        for _ in range(MAX_QUEUE_JOBS):
            if _STOP.is_set():
                _report("Stopped on request.")
                break
            if (time.time() - started) / 60 > MAX_QUEUE_MINUTES:
                _report(f"Stopping: hit the {MAX_QUEUE_MINUTES} minute limit for one run.")
                break

            row = task_store.next_open_task()
            if row is None:
                break

            task_id, title, notes = row
            job = (notes or "").strip() or title
            branch = f"agent/{_slug(title)}-{datetime.now():%m%d-%H%M%S}"
            task_store.attach_branch(task_id, branch)
            _report(f"Starting #{task_id}: {title}")

            ok, err, files = _execute_job(job, branch)

            if not ok:
                failed = (task_id, title, err)
                _discard(branch, task_id) if "Build still broken" not in err else task_store.clear_branch(task_id)
                break

            # Protected-path gate. Auto-merge is fine for ordinary product
            # code. Anything touching money, auth or config waits for a human,
            # even though the build passed.
            hits = _protected_hits(files)
            if hits:
                _git("push", "-u", "origin", branch)
                pr_url = _open_pr(branch, job) or "(no PR, run `gh auth login`)"
                held.append((task_id, title, branch, hits, pr_url))
                _report(
                    f"**Held #{task_id}: {title}**\n"
                    f"Build passed, but it touched protected files:\n"
                    + "\n".join(f"  {h}" for h in hits[:8])
                    + f"\nNot merged. Review it yourself: {pr_url}\n"
                    f"To take it anyway: ship {branch}"
                )
                _git("checkout", MAIN_BRANCH)
                continue

            # Merge straight into main. This is the part that needs the tag.
            _git("checkout", MAIN_BRANCH)
            code, out = _git("merge", "--no-ff", branch, "-m", f"ship {branch}")
            if code != 0:
                _git("merge", "--abort")
                failed = (task_id, title, f"Could not merge cleanly: {out[-300:]}")
                task_store.clear_branch(task_id)
                break

            _git("push", "origin", MAIN_BRANCH)
            _git("branch", "-d", branch)
            task_store.complete_by_branch(branch)
            done += 1
            _report(f"Done #{task_id}: {title} ({len(files)} file(s)). Shipped.")

        mins = int((time.time() - started) / 60)
        left = task_store.open_count()

        if failed:
            task_id, title, err = failed
            _report(
                f"**Stopped at #{task_id}: {title}**\n```\n{err[-700:]}\n```\n"
                f"{done} job(s) shipped before this. {left} left in the queue.\n"
                f"Bring this to Claude. To undo the whole run: rewind {rewind_tag}"
            )
        else:
            held_note = ""
            if held:
                held_note = "\n**{} job(s) held for you** (touched protected files):\n".format(
                    len(held)
                ) + "\n".join(f"  #{t}: {ti}  {url}" for t, ti, _b, _h, url in held) + "\n"
            _report(
                f"**Queue finished.** {done} job(s) shipped in ~{mins} min. "
                f"{left} left.\n{held_note}"
                f"Live site updates in about a minute. Look at it.\n"
                f"If anything is wrong, undo the entire run with: rewind {rewind_tag}"
            )
    except Exception as exc:  # noqa: BLE001
        log.exception("queue thread crashed")
        _report(f"Autopilot crashed: {exc}\nTo undo: rewind {rewind_tag}")
    finally:
        _git("checkout", MAIN_BRANCH)
        with _LOCK:
            _RUNNING.clear()
        _STOP.clear()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def _start(job: str, task_id: int | None = None) -> str:
    problem = _repo_problem()
    if problem:
        return f"ERROR: {problem}"
    with _LOCK:
        if _RUNNING:
            return f"Already working on {', '.join(sorted(_RUNNING))}. Wait for it."
        branch = f"agent/{_slug(job)}-{datetime.now():%m%d-%H%M}"
        _RUNNING.add(branch)
    if task_id:
        task_store.attach_branch(task_id, branch)
    threading.Thread(target=_job_thread, args=(job, branch, task_id), daemon=True).start()
    label = f"Task #{task_id}: " if task_id else ""
    return f"{label}started on branch {branch}. I will post here when the build passes."


@tool(
    name="assign_coding_task",
    description=(
        "Give the coding agent one job on the website. It works on its own branch "
        "and reports back for your approval. Use for any request to build, change, "
        "fix or add something."
    ),
    parameters={
        "type": "object",
        "properties": {
            "job": {
                "type": "string",
                "description": (
                    "The job in plain language, as specific as the user made it. "
                    "Pass their wording through; do not turn it into technical steps."
                ),
            }
        },
        "required": ["job"],
    },
)
def assign_coding_task(job: str) -> str:
    return _start(job)


@tool(
    name="work_next_task",
    description=(
        "Build the next unfinished task from the tracker, then stop for approval. "
        "Use when the user says 'next' or 'do the next one'."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)
def work_next_task() -> str:
    row = task_store.next_open_task()
    if row is None:
        return "Nothing left in the queue. Add tasks in #tasks, or say what you want built."
    task_id, title, notes = row
    return _start((notes or "").strip() or title, task_id)


@tool(
    name="run_queue",
    description=(
        "AUTOPILOT. Work through every remaining task without stopping, merging each "
        "one into the live site as it passes. Destructive: changes go live with no "
        "review. Requires confirm=true, only when the user has clearly asked to run "
        "the whole queue automatically."
    ),
    parameters={
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "Must be true to proceed."}
        },
        "required": ["confirm"],
    },
    high_impact=True,
)
def run_queue(confirm: bool = False) -> str:
    problem = _repo_problem()
    if problem:
        return f"ERROR: {problem}"

    pending = task_store.open_count()
    if not pending:
        return "Queue is empty. Nothing to run."

    with _LOCK:
        if _RUNNING:
            return f"Already working on {', '.join(sorted(_RUNNING))}. Wait for it."
        _RUNNING.add("autopilot")

    _STOP.clear()
    # The undo button. Taken before anything is touched.
    tag = f"autopilot-{datetime.now():%m%d-%H%M}"
    _git("checkout", MAIN_BRANCH)
    _git("tag", tag)

    threading.Thread(target=_queue_thread, args=(tag,), daemon=True).start()
    return (
        f"Autopilot running. {pending} task(s), auto-merged as each build passes.\n"
        f"Saved a restore point: **{tag}**. If the finished site is wrong, "
        f"say `rewind {tag}` and everything goes back.\n"
        f"Say `stop` to halt after the current job."
    )


@tool(
    name="stop_queue",
    description="Halt autopilot after the job it is currently on finishes.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def stop_queue() -> str:
    if not _RUNNING:
        return "Nothing is running."
    _STOP.set()
    return "Will stop after the current job. Already-shipped jobs stay shipped."


@tool(
    name="rewind",
    description=(
        "Undo an entire autopilot run, putting the live site back to how it was "
        "before it started. Destructive. Requires confirm=true."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tag": {"type": "string", "description": "The restore point, e.g. autopilot-0725-2130"},
            "confirm": {"type": "boolean", "description": "Must be true to proceed."},
        },
        "required": ["tag", "confirm"],
    },
    high_impact=True,
)
def rewind(tag: str, confirm: bool = False) -> str:
    if not tag.startswith("autopilot-"):
        return "ERROR: only autopilot-* restore points can be rewound to."
    code, _ = _git("rev-parse", "--verify", tag)
    if code != 0:
        return f"No restore point called {tag}."
    if _RUNNING:
        return "Autopilot is still running. Say `stop` first."

    _git("checkout", MAIN_BRANCH)
    code, out = _git("reset", "--hard", tag)
    if code != 0:
        return f"Could not rewind: {out[-300:]}"
    code, out = _git("push", "--force-with-lease", "origin", MAIN_BRANCH)
    if code != 0:
        return f"Rewound locally but could not push: {out[-300:]}"
    return (
        f"Rewound to {tag}. The live site goes back in about a minute.\n"
        "The tasks are still marked done; say so if you want them reopened."
    )


@tool(
    name="list_jobs",
    description="Show agent branches waiting to be shipped, and what autopilot is doing.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_jobs() -> str:
    problem = _repo_problem()
    if problem and "uncommitted" not in problem:
        return f"ERROR: {problem}"
    code, out = _git("branch", "--list", "agent/*", "--format=%(refname:short)")
    branches = [b for b in out.splitlines() if b.strip()] if code == 0 else []
    running = f"\nRunning: {', '.join(sorted(_RUNNING))}" if _RUNNING else ""
    left = task_store.open_count()
    tail = f"\n{left} task(s) still queued." if left else ""
    if not branches:
        return "No branches waiting." + running + tail
    return "Waiting for you to test:\n" + "\n".join(f"  {b}" for b in branches) + running + tail


@tool(
    name="ship_job",
    description=(
        "Merge a finished agent branch into the live site. Destructive. Requires "
        "confirm=true, only when the user says they tested it and want it shipped."
    ),
    parameters={
        "type": "object",
        "properties": {
            "branch": {"type": "string", "description": "Full branch name."},
            "confirm": {"type": "boolean", "description": "Must be true to proceed."},
        },
        "required": ["branch", "confirm"],
    },
    high_impact=True,
)
def ship_job(branch: str, confirm: bool = False) -> str:
    problem = _repo_problem()
    if problem:
        return f"ERROR: {problem}"
    if not branch.startswith("agent/"):
        return "ERROR: only agent/* branches can be shipped this way."
    code, _ = _git("rev-parse", "--verify", branch)
    if code != 0:
        return f"No branch called {branch}. Use list_jobs to see what exists."

    _git("checkout", MAIN_BRANCH)
    code, out = _git("merge", "--no-ff", branch, "-m", f"ship {branch}")
    if code != 0:
        _git("merge", "--abort")
        return f"Merge failed, nothing changed: {out[-400:]}"
    code, out = _git("push", "origin", MAIN_BRANCH)
    if code != 0:
        return f"Merged locally but could not push: {out[-300:]}"
    _git("branch", "-d", branch)

    done_id = task_store.complete_by_branch(branch)
    remaining = task_store.open_count()
    parts = [f"Shipped {branch}. Live site updates in about a minute."]
    if done_id:
        parts.append(f"Task #{done_id} marked done.")
    if remaining:
        parts.append(f"{remaining} task(s) left. Say 'next' or 'run everything'.")
    return " ".join(parts)

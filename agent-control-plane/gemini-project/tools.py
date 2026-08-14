import subprocess
import json
import os

def run_task_cli(action: str, title: str) -> str:
    """Creates or lists tasks in the local task queue.
    
    Args:
        action: 'create' or 'list'
        title: Title of the task
    """
    tasks_file = "tasks.json"
    tasks = []
    
    if os.path.exists(tasks_file):
        with open(tasks_file, "r") as f:
            try:
                tasks = json.load(f)
            except json.JSONDecodeError:
                tasks = []
                
    if action == "create":
        tasks.append({"id": len(tasks) + 1, "title": title, "status": "pending"})
        with open(tasks_file, "w") as f:
            json.dump(tasks, f, indent=2)
        return f"Created task #{len(tasks)}: {title}"
    elif action == "list":
        return json.dumps(tasks)
    return "Invalid action"

def run_code_cli(prompt: str) -> str:
    """Invokes Antigravity CLI (agy) to generate or edit code in the local workspace.
    
    Args:
        prompt: Detailed coding instructions for agy
    """
    repo_path = os.getcwd()
    cmd = [
        "agy",
        "-p", prompt,
        "--mode=accept-edits",
        "--dangerously-skip-permissions"
    ]
    try:
        res = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=120)
        return res.stdout if res.returncode == 0 else f"Execution failed: {res.stderr}"
    except Exception as e:
        return f"Error calling agy: {str(e)}"

CHANNEL_TOOLS = {
    "tasks": [run_task_cli],
    "code": [run_code_cli]
}

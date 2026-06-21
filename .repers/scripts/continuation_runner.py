import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from objective_audit import DEFAULT_OBJECTIVE, build_objective_audit


CONTINUATION_RUN_SCHEMA = "repers.continuation_run.v1"


def split_command(command):
    return shlex.split(command, posix=os.name != "nt")


def run_command(command, cwd):
    proc = subprocess.run(
        split_command(command),
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    parsed = None
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "command": command,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "json": parsed,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def action_selected(action, action_ids):
    if not action_ids:
        return True
    return action.get("id") in set(action_ids)


def build_continuation_run(
    workspace_root,
    install_root,
    output_dir="dist",
    objective=None,
    deep=False,
    apply=False,
    action_ids=None,
):
    workspace = Path(workspace_root).resolve()
    audit, audit_path = build_objective_audit(
        workspace,
        Path(install_root).resolve(),
        output_dir=output_dir,
        objective=objective or DEFAULT_OBJECTIVE,
        deep=deep,
    )
    continuation = audit["continuation"]
    local_actions = [
        action
        for action in continuation.get("local_actions", [])
        if action_selected(action, action_ids)
    ]
    ready_actions = [action for action in local_actions if action.get("status") == "ready"]
    deferred_actions = [action for action in local_actions if action.get("status") != "ready"]
    executions = []

    if apply:
        for action in ready_actions:
            executions.append(
                {
                    "id": action["id"],
                    "title": action["title"],
                    "result": run_command(action["command"], workspace),
                }
            )

    failed = [
        execution
        for execution in executions
        if not execution.get("result", {}).get("ok")
    ]
    return {
        "schema": CONTINUATION_RUN_SCHEMA,
        "ok": not failed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(Path(install_root).resolve()),
        "output_dir": str(Path(output_dir).resolve()),
        "mode": "apply" if apply else "dry-run",
        "audit_path": str(Path(audit_path).resolve()),
        "objective_complete": audit["objective_complete"],
        "blocking_incomplete": audit["blocking_incomplete"],
        "continuation_status": continuation["status"],
        "selected_action_ids": [action["id"] for action in local_actions],
        "ready_action_ids": [action["id"] for action in ready_actions],
        "deferred_action_ids": [action["id"] for action in deferred_actions],
        "external_action_ids": [
            action["id"] for action in continuation.get("external_actions", [])
        ],
        "local_actions": local_actions,
        "external_actions": continuation.get("external_actions", []),
        "executions": executions,
        "errors": [
            f"{execution['id']} failed with return code {execution['result']['returncode']}"
            for execution in failed
        ],
    }

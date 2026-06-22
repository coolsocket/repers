import json
from datetime import datetime, timezone
from pathlib import Path

from objective_audit import DEFAULT_OBJECTIVE, build_objective_audit


STATE_REPORT_SCHEMA = "repers.state_report.v1"


def load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def by_requirement(audit, requirement_id):
    for requirement in audit.get("requirements", []):
        if requirement.get("id") == requirement_id:
            return requirement
    return None


def requirement_evidence(audit, requirement_id):
    requirement = by_requirement(audit, requirement_id)
    return requirement.get("evidence", {}) if requirement else {}


def first_action(actions, statuses):
    for action in actions:
        if action.get("status") in statuses:
            return action
    return None


def build_state_markdown(state):
    lines = [
        "# RePERS State",
        "",
        f"- Generated: `{state['generated_at']}`",
        f"- Status: `{state['status']}`",
        f"- Objective complete: `{state['objective']['complete']}`",
        f"- Blockers: `{', '.join(state['objective']['blocking_incomplete']) or 'none'}`",
        "",
        "## Git",
        "",
        f"- Branch: `{state['git']['branch']}`",
        f"- Head: `{state['git']['head_sha']}`",
        f"- Dirty: `{state['git']['dirty']}`",
        f"- Remotes: `{state['git']['remote_count']}`",
        "",
        "## Package",
        "",
        f"- OK: `{state['package']['ok']}`",
        f"- Round trip: `{state['package']['roundtrip_ok']}`",
        f"- Archive: `{state['package']['archive_path']}`",
        "",
        "## Continuation",
        "",
        f"- Status: `{state['continuation']['status']}`",
        f"- Ready local action: `{state['next']['local_action_id'] or 'none'}`",
        f"- External action: `{state['next']['external_action_id'] or 'none'}`",
        "",
    ]
    if state["next"].get("local_command"):
        lines.extend(["```powershell", state["next"]["local_command"], "```", ""])
    if state["next"].get("external_command"):
        lines.extend(["```powershell", state["next"]["external_command"], "```", ""])
    return "\n".join(lines)


def build_state_report(workspace_root, install_root, output_dir="dist", objective=None, deep=False):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    audit, audit_path = build_objective_audit(
        workspace,
        install,
        output_dir=output,
        objective=objective or DEFAULT_OBJECTIVE,
        deep=deep,
    )
    release = load_json(output / "repers-release-evidence.json") or {}
    readiness = load_json(output / "repers-0.1.0-readiness.json") or {}
    continuation = audit.get("continuation", {})
    git = requirement_evidence(audit, "publication_ready").get("git", {}) or release.get("git") or {}
    package = release.get("package", {})
    registry_requirement = by_requirement(audit, "agent_reusable_capabilities") or {}
    tests_requirement = by_requirement(audit, "tests_and_package_gates") or {}

    ready_local = first_action(continuation.get("local_actions", []), {"ready"})
    external = first_action(continuation.get("external_actions", []), {"needs_remote_url", "after_remote", "after_push"})
    status = "complete" if audit.get("objective_complete") else continuation.get("status", "incomplete")
    state = {
        "schema": STATE_REPORT_SCHEMA,
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "audit_path": str(Path(audit_path).resolve()),
        "deep": bool(deep),
        "status": status,
        "objective": {
            "complete": audit.get("objective_complete"),
            "blocking_incomplete": audit.get("blocking_incomplete", []),
            "requirements_total": len(audit.get("requirements", [])),
            "requirements_passed": len([item for item in audit.get("requirements", []) if item.get("passed")]),
        },
        "git": {
            "branch": git.get("branch"),
            "head_sha": git.get("head_sha"),
            "dirty": git.get("dirty"),
            "status_count": git.get("status_count"),
            "remote_count": git.get("remote_count"),
        },
        "package": {
            "ok": package.get("ok", readiness.get("ok")),
            "roundtrip_ok": package.get("roundtrip_ok"),
            "archive_path": package.get("archive_path", readiness.get("archive_path")),
            "readiness_warnings": package.get("readiness_warnings", readiness.get("warnings", [])),
        },
        "capabilities": {
            "entry_count": registry_requirement.get("evidence", {}).get("entry_count"),
            "missing": registry_requirement.get("evidence", {}).get("missing", []),
        },
        "tests": {
            "passed": tests_requirement.get("passed"),
            "smoke_ok": tests_requirement.get("evidence", {}).get("smoke_ok"),
            "bundle_status_ok": tests_requirement.get("evidence", {}).get("bundle_status_ok"),
        },
        "continuation": {
            "status": continuation.get("status"),
            "local_action_ids": [action.get("id") for action in continuation.get("local_actions", [])],
            "external_action_ids": [action.get("id") for action in continuation.get("external_actions", [])],
        },
        "next": {
            "local_action_id": ready_local.get("id") if ready_local else None,
            "local_command": ready_local.get("command") if ready_local else None,
            "external_action_id": external.get("id") if external else None,
            "external_command": external.get("command") if external else None,
        },
        "artifacts": {
            "state_json": str((output / "repers-state.json").resolve()),
            "state_markdown": str((output / "repers-state.md").resolve()),
            "objective_audit": str(Path(audit_path).resolve()),
            "continuation_markdown": audit.get("continuation_markdown_path"),
            "release_evidence": str((output / "repers-release-evidence.json").resolve()),
        },
    }
    json_path = output / "repers-state.json"
    markdown_path = output / "repers-state.md"
    json_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(build_state_markdown(state), encoding="utf-8")
    return state, json_path, markdown_path

"""Slim state report for the RePERS workspace.

v0.2 BREAKING: this module no longer depends on `objective_audit` /
`continuation_runner`. The state output now contains only git + package +
capabilities — the three signals a receiver cares about. The old
`objective` / `next` fields were specific to RePERS's own publication
goals and have been removed (see CHANGELOG v0.2.0).
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


STATE_REPORT_SCHEMA = "repers.state_report.v1"


def _run(cmd, cwd, default=""):
    try:
        result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else default
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return default


def _git_state(repo_root):
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root, default="(unknown)")
    head = _run(["git", "rev-parse", "HEAD"], repo_root, default="(none)")
    porcelain = _run(["git", "status", "--porcelain"], repo_root, default="")
    return {
        "branch": branch,
        "head_sha": head,
        "has_head": head != "(none)",
        "dirty": bool(porcelain.strip()),
        "status_count": len([ln for ln in porcelain.splitlines() if ln.strip()]),
        "remote_count": len([ln for ln in _run(["git", "remote"], repo_root).splitlines() if ln.strip()]),
        "errors": [],
    }


def _package_state(install_root):
    manifest = Path(install_root) / "manifest.json"
    if not manifest.exists():
        return {"ok": False, "error": "manifest.json missing"}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "schema": data.get("schema"),
        "version": data.get("version"),
        "file_count": data.get("file_count"),
    }


def _capability_state(install_root):
    registry = Path(install_root) / "capabilities" / "registry.json"
    if not registry.exists():
        return {"ok": False, "count": 0}
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
        entries = data.get("entries", [])
        return {"ok": True, "count": len(entries), "schema": data.get("schema"), "version": data.get("version")}
    except Exception as exc:
        return {"ok": False, "count": 0, "error": str(exc)}


def build_state_report(repo_root, install_root, output_dir, deep=False):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    git = _git_state(repo_root)
    package = _package_state(install_root)
    capabilities = _capability_state(install_root)

    state = {
        "schema": STATE_REPORT_SCHEMA,
        "ok": git["errors"] == [] and package["ok"] and capabilities["ok"],
        "status": "ok" if (package["ok"] and capabilities["ok"]) else "incomplete",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(Path(repo_root).resolve()),
        "install_root": str(Path(install_root).resolve()),
        "git": git,
        "package": package,
        "capabilities": capabilities,
    }

    json_path = output_dir / "repers-state.json"
    md_path = output_dir / "repers-state.md"
    json_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_format_markdown(state), encoding="utf-8")

    state["artifacts"] = {
        "state_json": str(json_path.resolve()),
        "state_md": str(md_path.resolve()),
    }
    return state, json_path, md_path


def _format_markdown(state):
    lines = [
        "# RePERS State",
        "",
        f"_Generated: {state['generated_at']}_",
        "",
        f"- **Status**: `{state['status']}`",
        f"- **Branch**: `{state['git']['branch']}` @ `{state['git']['head_sha'][:12]}`",
        f"- **Dirty**: {state['git']['dirty']}",
        f"- **Package**: schema={state['package'].get('schema')}, version={state['package'].get('version')}, file_count={state['package'].get('file_count')}",
        f"- **Capabilities**: {state['capabilities']['count']} entries (schema={state['capabilities'].get('schema')}, version={state['capabilities'].get('version')})",
    ]
    return "\n".join(lines) + "\n"

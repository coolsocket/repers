"""Compare snapshotted JSON evidence artifacts against live git state.

Detects drift and staleness between recorded release/audit snapshots and the
current working tree, surfacing artifacts that need to be regenerated.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from release_evidence import git_publish_state, load_json


SNAPSHOT_FRESHNESS_SCHEMA = "repers.snapshot_freshness.v1"


def nested_get(data, keys):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def comparable_git_snapshot(data, artifact_name):
    if artifact_name == "state":
        return nested_get(data, ["git"]) or {}
    if artifact_name == "release_evidence":
        return nested_get(data, ["git"]) or {}
    if artifact_name == "objective_audit":
        requirements = data.get("requirements", []) if isinstance(data, dict) else []
        for requirement in requirements:
            if requirement.get("id") == "publication_ready":
                return nested_get(requirement, ["evidence", "git"]) or {}
    if artifact_name == "verify_all":
        gates = data.get("gates", []) if isinstance(data, dict) else []
        for gate in gates:
            if gate.get("name") == "state_deep":
                return nested_get(gate, ["json", "state", "git"]) or {}
    return {}


def compare_git_snapshot(snapshot, live_git):
    fields = ["branch", "head_sha", "dirty", "remote_count"]
    mismatches = []
    for field in fields:
        if snapshot.get(field) != live_git.get(field):
            mismatches.append(
                {
                    "field": field,
                    "snapshot": snapshot.get(field),
                    "live": live_git.get(field),
                }
            )
    return mismatches


def artifact_record(output, name, filename, live_git):
    path = output / filename
    record = {
        "name": name,
        "path": str(path.resolve()),
        "exists": path.exists(),
        "comparable": False,
        "fresh": False,
        "generated_at": None,
        "mismatches": [],
    }
    if not path.exists():
        record["mismatches"].append({"field": "exists", "snapshot": False, "live": True})
        return record

    try:
        payload = load_json(path) or {}
    except Exception as exc:
        record["mismatches"].append({"field": "json", "snapshot": str(exc), "live": "valid JSON"})
        return record

    if name == "state":
        payload = payload.get("state", payload)
    elif name == "verify_all":
        payload = payload.get("verify_all", payload)
    elif name == "objective_audit":
        payload = payload.get("objective_audit", payload)

    record["generated_at"] = payload.get("generated_at")
    snapshot = comparable_git_snapshot(payload, name)
    record["comparable"] = bool(snapshot)
    if not snapshot:
        record["mismatches"].append({"field": "git", "snapshot": None, "live": "present"})
        return record

    record["mismatches"] = compare_git_snapshot(snapshot, live_git)
    record["fresh"] = not record["mismatches"]
    return record


def build_snapshot_freshness(workspace_root, output_dir="dist", strict=False):
    workspace = Path(workspace_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    live_git = git_publish_state(workspace)
    artifacts = [
        artifact_record(output, "state", "repers-state.json", live_git),
        artifact_record(output, "release_evidence", "repers-release-evidence.json", live_git),
        artifact_record(output, "objective_audit", "repers-objective-audit.json", live_git),
        artifact_record(output, "verify_all", "repers-verify-all.json", live_git),
    ]
    checked = [item for item in artifacts if item["exists"] and item["comparable"]]
    stale = [item for item in checked if not item["fresh"]]
    missing = [item for item in artifacts if not item["exists"]]
    fresh = bool(checked) and not stale
    errors = []
    if strict and live_git.get("errors"):
        errors.extend(live_git["errors"])
    if strict and not fresh:
        errors.append("one or more comparable generated snapshots do not match live Git state")

    result = {
        "schema": SNAPSHOT_FRESHNESS_SCHEMA,
        "ok": not errors,
        "fresh": fresh,
        "strict": bool(strict),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "output_dir": str(output),
        "live_git": live_git,
        "artifact_count": len(artifacts),
        "checked_count": len(checked),
        "stale_count": len(stale),
        "missing_count": len(missing),
        "artifacts": artifacts,
        "errors": errors,
    }
    json_path = output / "repers-snapshot-freshness.json"
    markdown_path = output / "repers-snapshot-freshness.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(build_snapshot_freshness_markdown(result), encoding="utf-8")
    return result, json_path, markdown_path


def build_snapshot_freshness_markdown(result):
    lines = [
        "# RePERS Snapshot Freshness",
        "",
        f"- Generated: `{result['generated_at']}`",
        f"- OK: `{result['ok']}`",
        f"- Fresh: `{result['fresh']}`",
        f"- Strict: `{result['strict']}`",
        f"- Live head: `{result['live_git'].get('head_sha')}`",
        f"- Live dirty: `{result['live_git'].get('dirty')}`",
        f"- Live remotes: `{result['live_git'].get('remote_count')}`",
        "",
        "## Artifacts",
        "",
    ]
    for artifact in result["artifacts"]:
        lines.append(
            f"- `{artifact['name']}`: exists=`{artifact['exists']}`, comparable=`{artifact['comparable']}`, fresh=`{artifact['fresh']}`"
        )
        for mismatch in artifact["mismatches"]:
            lines.append(
                f"  - `{mismatch['field']}`: snapshot=`{mismatch['snapshot']}`, live=`{mismatch['live']}`"
            )
    if result["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in result["errors"]:
            lines.append(f"- {error}")
    return "\n".join(lines)

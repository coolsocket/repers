import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


VERIFY_ALL_SCHEMA = "repers.verify_all.v1"


def command_result(name, command, cwd, env=None):
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, env=env)
    parsed = None
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "name": name,
        "command": command,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "json": parsed,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def write_markdown(report, markdown_path):
    lines = [
        "# RePERS Verify All",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- OK: `{report['ok']}`",
        f"- Status: `{report['status']}`",
        f"- Objective complete: `{report['state']['objective_complete']}`",
        f"- Objective blockers: `{', '.join(report['state']['blocking_incomplete']) or 'none'}`",
        "",
        "## Gates",
        "",
    ]
    for gate in report["gates"]:
        lines.append(f"- `{gate['name']}`: `{gate['ok']}`")
    lines.extend(["", "## Next", ""])
    if report["next"].get("external_command"):
        lines.extend(
            [
                f"- External action: `{report['next']['external_action_id']}`",
                "",
                "```powershell",
                report["next"]["external_command"],
                "```",
                "",
            ]
        )
    else:
        lines.append("- None")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def build_verify_all(workspace_root, install_root, output_dir="dist"):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    repers = install / "scripts" / "repers.py"
    temp_root = Path(tempfile.mkdtemp(prefix="repers-verify-all-"))

    gates = []
    gates.append(
        command_result(
            "verify_install",
            [sys.executable, "-B", str(repers), "verify-install", "--json"],
            workspace,
        )
    )
    gates.append(
        command_result(
            "capabilities_validate",
            [sys.executable, "-B", str(repers), "capabilities", "--action", "validate", "--json"],
            workspace,
        )
    )
    gates.append(
        command_result(
            "capabilities_search_state",
            [
                sys.executable,
                "-B",
                str(repers),
                "capabilities",
                "--action",
                "search",
                "--query",
                "repository state status dashboard publish package",
                "--json",
            ],
            workspace,
        )
    )
    gates.append(
        command_result(
            "bundle_status_package_roundtrip",
            [
                sys.executable,
                "-B",
                str(repers),
                "bundle-status",
                "--package",
                "--verify-roundtrip",
                "--output",
                str(temp_root / "bundle"),
                "--json",
            ],
            workspace,
        )
    )
    gates.append(
        command_result(
            "receiver_fixture",
            [
                sys.executable,
                "-B",
                str(repers),
                "receiver-fixture",
                "--output",
                str(temp_root / "receiver"),
                "--json",
            ],
            workspace,
        )
    )
    gates.append(
        command_result(
            "remote_bootstrap_fixture",
            [
                sys.executable,
                "-B",
                str(repers),
                "remote-bootstrap-fixture",
                "--output",
                str(temp_root / "remote"),
                "--json",
            ],
            workspace,
        )
    )
    smoke_env = {
        **os.environ,
        "REPERS_SMOKE_DIST": str(temp_root / "smoke-dist"),
        "REPERS_INDEX_DB_PATH": str(temp_root / "smoke-index" / "repers.db"),
        "REPERS_SKIP_VERIFY_ALL_SMOKE": "1",
    }
    gates.append(
        command_result(
            "smoke_tests",
            [sys.executable, "-B", str(workspace / "tests" / "smoke_repers.py")],
            workspace,
            env=smoke_env,
        )
    )
    gates.append(
        command_result(
            "state_deep",
            [
                sys.executable,
                "-B",
                str(repers),
                "state",
                "--deep",
                "--output",
                str(temp_root / "state"),
                "--json",
            ],
            workspace,
            env={**os.environ, "REPERS_SKIP_VERIFY_ALL_SMOKE": "1"},
        )
    )

    state_json = gates[-1].get("json", {}).get("state") if gates[-1].get("json") else {}
    blocking = state_json.get("objective", {}).get("blocking_incomplete", [])
    local_gate_ok = all(gate["ok"] for gate in gates)
    external_only = set(blocking) <= {"publication_ready"}
    status = "complete" if state_json.get("objective", {}).get("complete") else "blocked_external" if local_gate_ok and external_only else "local_failure"
    report = {
        "schema": VERIFY_ALL_SCHEMA,
        "ok": bool(local_gate_ok and external_only),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "temp_root": str(temp_root),
        "status": status,
        "gates": gates,
        "state": {
            "status": state_json.get("status"),
            "objective_complete": state_json.get("objective", {}).get("complete"),
            "blocking_incomplete": blocking,
            "package_ok": state_json.get("package", {}).get("ok"),
            "tests_passed": state_json.get("tests", {}).get("passed"),
            "capability_count": state_json.get("capabilities", {}).get("entry_count"),
        },
        "next": {
            "external_action_id": state_json.get("next", {}).get("external_action_id"),
            "external_command": state_json.get("next", {}).get("external_command"),
        },
        "errors": [
            f"{gate['name']} failed with return code {gate['returncode']}"
            for gate in gates
            if not gate["ok"]
        ],
    }
    json_path = output / "repers-verify-all.json"
    markdown_path = output / "repers-verify-all.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, markdown_path)
    return report, json_path, markdown_path

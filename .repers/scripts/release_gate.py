import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from doctor import run_doctor
from reviewer import review_task
from shipping import create_shipping_report


def run_command(command, cwd):
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return {
        "command": command,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def create_release_gate(
    task,
    task_dir,
    workspace_root,
    install_root,
    index_db_path,
    lsp_guard_path,
    installed_target=None,
    strict_warnings=False,
    update_status=False,
):
    task_path = Path(task_dir)
    workspace = Path(workspace_root)
    repers_cli = Path(install_root) / "scripts" / "repers.py"

    review = review_task(task_path, update_status=update_status)
    doctor = run_doctor(workspace_root, install_root, index_db_path, lsp_guard_path)
    shipping, shipping_path = create_shipping_report(
        task,
        task_path,
        workspace,
        doctor,
        installed_target=installed_target,
    )

    audit_command = [sys.executable, "-B", str(repers_cli), "audit", "--task", task]
    if strict_warnings:
        audit_command.append("--strict-warnings")
    audit = run_command(audit_command, workspace)

    errors = []
    warnings = []
    if not review.get("ok"):
        errors.append("review gate failed")
    if not doctor.get("ok"):
        errors.append("doctor gate failed")
    if not shipping.get("summary", {}).get("ok"):
        errors.extend(shipping.get("summary", {}).get("errors", []) or ["shipping gate failed"])
    if not audit.get("ok"):
        errors.append("audit gate failed")

    warnings.extend(shipping.get("summary", {}).get("warnings", []))
    if audit.get("ok") and "Warning" in audit.get("stdout_tail", ""):
        warnings.append("audit completed with warnings")

    release = {
        "schema": "repers.release_gate.v1",
        "task": task,
        "task_dir": str(task_path.resolve()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_warnings": strict_warnings,
        "update_status": update_status,
        "summary": {
            "ok": not errors,
            "errors": errors,
            "warnings": sorted(set(warnings)),
        },
        "gates": {
            "review": {
                "ok": review.get("ok"),
                "result_count": review.get("result_count"),
                "ok_count": review.get("ok_count"),
                "failed_count": review.get("failed_count"),
            },
            "doctor": {
                "ok": doctor.get("ok"),
                "hook_ok": doctor.get("hook", {}).get("ok"),
                "index_ok": doctor.get("index", {}).get("ok"),
            },
            "shipping": {
                "ok": shipping.get("summary", {}).get("ok"),
                "path": str(Path(shipping_path).resolve()),
                "installed_manifest_schema": shipping.get("installed_bundle", {}).get("manifest_schema"),
                "installed_manifest_version": shipping.get("installed_bundle", {}).get("manifest_version"),
                "installed_manifest_verify_ok": shipping.get("installed_bundle", {}).get("manifest_verify_ok"),
            },
            "audit": {
                "ok": audit.get("ok"),
                "returncode": audit.get("returncode"),
                "strict_warnings": strict_warnings,
            },
        },
        "doctor": doctor,
        "review": review,
        "shipping": shipping,
        "audit": audit,
    }
    output_path = task_path / "release.json"
    output_path.write_text(json.dumps(release, indent=2, ensure_ascii=False), encoding="utf-8")
    return release, output_path

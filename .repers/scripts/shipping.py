import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_MARKDOWN_ARTIFACTS = ["research.md", "plan.md", "review.md", "shipping.md"]
MACHINE_ARTIFACTS = [
    "research.json",
    "plan.proposed.json",
    "plan.json",
    "dispatch/manifest.json",
    "review.json",
    "release.json",
]


def load_json_if_present(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_record(task_dir, relative_path):
    path = Path(task_dir) / relative_path
    record = {
        "name": relative_path,
        "path": str(path.resolve()),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
    if path.suffix == ".json" and path.exists():
        try:
            data = load_json_if_present(path)
            record["schema"] = data.get("schema") if isinstance(data, dict) else None
        except Exception as exc:
            record["json_error"] = str(exc)
    return record


def package_archive_state(workspace_root):
    root = Path(workspace_root)
    dist_dir = root / "dist"
    archives = sorted(dist_dir.glob("repers-*.zip"), key=lambda path: path.stat().st_mtime, reverse=True) if dist_dir.exists() else []
    if not archives:
        return {"checked": True, "exists": False, "dist_dir": str(dist_dir.resolve())}
    archive = archives[0]
    state = {
        "checked": True,
        "exists": True,
        "path": str(archive.resolve()),
        "size_bytes": archive.stat().st_size,
        "manifest_exists": False,
        "manifest_schema": None,
        "manifest_version": None,
        "manifest_file_count": 0,
        "errors": [],
    }
    try:
        with zipfile.ZipFile(archive) as zf:
            manifest_names = [name for name in zf.namelist() if name.endswith("/repers-package-manifest.json")]
            if not manifest_names:
                state["errors"].append("repers-package-manifest.json not found in archive")
                return state
            manifest = json.loads(zf.read(manifest_names[0]).decode("utf-8"))
            state["manifest_exists"] = True
            state["manifest_schema"] = manifest.get("schema")
            state["manifest_version"] = manifest.get("version")
            state["manifest_file_count"] = manifest.get("file_count", 0)
    except Exception as exc:
        state["errors"].append(str(exc))
    return state


def git_state(workspace_root):
    root = Path(workspace_root)
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        entries = [line for line in status.stdout.splitlines() if line.strip()]
        return {
            "ok": True,
            "root": top.stdout.strip(),
            "dirty": bool(entries),
            "status_count": len(entries),
            "status_entries": entries[:50],
        }
    except Exception as exc:
        return {"ok": False, "root": None, "dirty": None, "status_count": 0, "status_entries": [], "error": str(exc)}


def installed_bundle_state(target_root):
    if not target_root:
        return {"checked": False}
    root = Path(target_root)
    repers = root / ".repers"
    hook = root / ".git" / "hooks" / "pre-commit"
    manifest_path = repers / "manifest.json"
    manifest = load_json_if_present(manifest_path)
    verify = None
    if manifest_path.exists():
        try:
            from install_repers import verify_manifest

            verify = verify_manifest(repers)
        except Exception as exc:
            verify = {
                "schema": "repers.install_verify.v1",
                "ok": False,
                "errors": [str(exc)],
                "missing": [],
                "changed": [],
                "extra": [],
            }
    return {
        "checked": True,
        "target_root": str(root.resolve()),
        "bundle_exists": repers.exists(),
        "cli_exists": (repers / "scripts" / "repers.py").exists(),
        "hook_exists": hook.exists(),
        "manifest_exists": manifest_path.exists(),
        "manifest_path": str(manifest_path.resolve()),
        "manifest_schema": manifest.get("schema") if isinstance(manifest, dict) else None,
        "manifest_version": manifest.get("version") if isinstance(manifest, dict) else None,
        "manifest_file_count": manifest.get("file_count") if isinstance(manifest, dict) else None,
        "manifest_hook_policy": manifest.get("hook_policy") if isinstance(manifest, dict) else None,
        "manifest_verify_schema": verify.get("schema") if isinstance(verify, dict) else None,
        "manifest_verify_ok": verify.get("ok") if isinstance(verify, dict) else None,
        "manifest_verify_checked_count": verify.get("checked_count") if isinstance(verify, dict) else None,
        "manifest_verify_missing_count": len(verify.get("missing", [])) if isinstance(verify, dict) else None,
        "manifest_verify_changed_count": len(verify.get("changed", [])) if isinstance(verify, dict) else None,
        "manifest_verify_extra_count": len(verify.get("extra", [])) if isinstance(verify, dict) else None,
        "manifest_verify_errors": verify.get("errors") if isinstance(verify, dict) else None,
    }


def report_summary(markdown_artifacts, doctor_result, review_json, git, installed):
    errors = []
    warnings = []

    missing = [item["name"] for item in markdown_artifacts if not item["exists"]]
    if missing:
        errors.append(f"missing required markdown artifacts: {', '.join(missing)}")
    if not doctor_result.get("ok"):
        errors.append("doctor check is not ok")
    if review_json and not review_json.get("ok"):
        errors.append("review.json is not ok")
    if git.get("dirty"):
        warnings.append("git working tree is dirty")
    if doctor_result.get("hook") and not doctor_result["hook"].get("ok"):
        warnings.append("RePERS hook is not installed for this workspace")
    optional_backends = [backend["name"] for backend in doctor_result.get("backends", []) if not backend.get("ok")]
    if optional_backends:
        warnings.append(f"optional backends unavailable: {', '.join(optional_backends)}")
    if installed.get("checked") and not installed.get("bundle_exists"):
        errors.append("installed bundle target is missing .repers")
    if installed.get("checked") and installed.get("bundle_exists") and not installed.get("manifest_exists"):
        warnings.append("installed bundle target is missing .repers/manifest.json")
    if installed.get("checked") and installed.get("manifest_verify_ok") is False:
        errors.append("installed bundle manifest verification failed")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def create_shipping_report(task, task_dir, workspace_root, doctor_result, installed_target=None):
    task_path = Path(task_dir)
    markdown_artifacts = [artifact_record(task_path, name) for name in REQUIRED_MARKDOWN_ARTIFACTS]
    machine_artifacts = [artifact_record(task_path, name) for name in MACHINE_ARTIFACTS]
    review_json = load_json_if_present(task_path / "review.json")
    dispatch_json = load_json_if_present(task_path / "dispatch" / "manifest.json")
    git = git_state(workspace_root)
    installed = installed_bundle_state(installed_target)
    package_archive = package_archive_state(workspace_root)
    summary = report_summary(markdown_artifacts, doctor_result, review_json, git, installed)

    report = {
        "schema": "repers.shipping.v1",
        "task": task,
        "task_dir": str(task_path.resolve()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "artifacts": {
            "markdown": markdown_artifacts,
            "machine": machine_artifacts,
        },
        "git": git,
        "doctor": doctor_result,
        "review": review_json,
        "dispatch": dispatch_json,
        "package_archive": package_archive,
        "installed_bundle": installed,
    }
    output_path = task_path / "shipping.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report, output_path

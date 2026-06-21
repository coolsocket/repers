import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


RELEASE_EVIDENCE_SCHEMA = "repers.release_evidence.v1"


def run_git(args, workspace_root):
    proc = subprocess.run(
        ["git", *args],
        cwd=workspace_root,
        capture_output=True,
        text=True,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def git_publish_state(workspace_root):
    root = Path(workspace_root)
    status = run_git(["status", "--porcelain"], root)
    branch = run_git(["branch", "--show-current"], root)
    head = run_git(["rev-parse", "HEAD"], root)
    remote = run_git(["remote", "-v"], root)
    entries = [line for line in status.get("stdout", "").splitlines() if line.strip()]
    return {
        "is_git_repo": status["ok"],
        "branch": branch["stdout"] if branch["ok"] else None,
        "head_sha": head["stdout"] if head["ok"] else None,
        "has_head": head["ok"],
        "dirty": bool(entries),
        "status_count": len(entries),
        "status_entries": entries[:100],
        "remote_count": len({line.split()[1] for line in remote["stdout"].splitlines() if len(line.split()) >= 2}) if remote["ok"] else 0,
        "errors": [item["stderr"] for item in [status, branch, head, remote] if not item["ok"] and item["stderr"]],
    }


def load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def governance_state(workspace_root):
    root = Path(workspace_root)
    required = [
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "SUPPORT.md",
        "ROADMAP.md",
        "CHANGELOG.md",
        "MAINTAINERS.md",
        ".github/workflows/repers-smoke.yml",
        "examples/basic-task/README.md",
        "docs/planning/active-repers-build.md",
    ]
    files = []
    missing = []
    for rel in required:
        path = root / rel
        record = {
            "path": rel,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        files.append(record)
        if not record["exists"]:
            missing.append(rel)
    return {"ok": not missing, "files": files, "missing": missing}


def latest_readiness(output_dir):
    output = Path(output_dir)
    candidates = sorted(output.glob("repers-*-readiness.json"), key=lambda p: p.stat().st_mtime, reverse=True) if output.exists() else []
    if not candidates:
        return None
    return load_json(candidates[0])


def build_release_evidence(workspace_root, install_root, output_dir="dist", include_package=False, verify_roundtrip=False):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()

    package = None
    if include_package:
        from package_repers import create_package

        package = create_package(output, verify_roundtrip=verify_roundtrip)
    readiness = package.get("readiness") if package else latest_readiness(output)

    from capability_registry import search_registry, validate_command

    registry_validation = validate_command(install / "capabilities" / "registry.json")
    registry_search = search_registry("release evidence package publish readiness", limit=5, path=install / "capabilities" / "registry.json")

    git = git_publish_state(workspace)
    governance = governance_state(workspace)
    package_ok = bool(package.get("ok")) if package else bool(readiness and readiness.get("ok"))
    roundtrip_ok = package.get("roundtrip", {}).get("ok") if package else None
    missing_for_publish = []
    if not git["has_head"]:
        missing_for_publish.append("create an initial commit")
    if git["dirty"]:
        missing_for_publish.append("commit or intentionally exclude working tree changes")
    if not git["branch"]:
        missing_for_publish.append("create or name a release branch")
    if git["remote_count"] == 0:
        missing_for_publish.append("configure a Git remote before opening a PR")
    if not package_ok:
        missing_for_publish.append("produce an ok package readiness artifact")
    if include_package and verify_roundtrip and not roundtrip_ok:
        missing_for_publish.append("make package round-trip verification pass")
    if not governance["ok"]:
        missing_for_publish.append("add missing governance files")
    if not registry_validation["ok"]:
        missing_for_publish.append("fix capability registry validation")

    evidence = {
        "schema": RELEASE_EVIDENCE_SCHEMA,
        "ok": package_ok and governance["ok"] and registry_validation["ok"] and (roundtrip_ok is not False),
        "publish_ready": not missing_for_publish,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "missing_for_publish": missing_for_publish,
        "git": git,
        "governance": governance,
        "capability_registry": {
            "validation": registry_validation,
            "release_query": registry_search,
        },
        "package": {
            "included": bool(package),
            "ok": package_ok,
            "archive_path": package.get("archive_path") if package else readiness.get("archive_path") if readiness else None,
            "archive_sha256": package.get("archive_sha256") if package else readiness.get("archive_sha256") if readiness else None,
            "manifest_file_count": package.get("manifest", {}).get("file_count") if package else None,
            "readiness_warnings": package.get("readiness", {}).get("warnings", []) if package else readiness.get("warnings", []) if readiness else [],
            "roundtrip_ok": roundtrip_ok,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    evidence_path = output / "repers-release-evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    return evidence, evidence_path

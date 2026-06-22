import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


PUBLISH_CLONE_FIXTURE_SCHEMA = "repers.publish_clone_fixture.v1"
FIXTURE_BRANCH = "publish-clone-fixture"


def run_plain(command, cwd):
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return {
        "command": [str(part) for part in command],
        "cwd": str(Path(cwd).resolve()),
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def run_json(command, cwd):
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    parsed = None
    errors = []
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            errors.append(f"stdout was not JSON: {exc}")
    return {
        "command": [str(part) for part in command],
        "cwd": str(Path(cwd).resolve()),
        "returncode": proc.returncode,
        "ok": proc.returncode == 0 and not errors,
        "json": parsed,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "errors": errors,
    }


def ignored_workspace_entry(path):
    rel = str(path).replace("\\", "/")
    parts = PurePosixPath(rel).parts
    return (
        rel == ".git"
        or rel.startswith(".git/")
        or rel == ".codegraph"
        or rel.startswith(".codegraph/")
        or rel == "repers_tasks"
        or rel.startswith("repers_tasks/")
        or rel.startswith(".repers-smoke-")
        or ".goal-machine" in parts
        or "__pycache__" in parts
        or rel.endswith(".pyc")
    )


def copy_workspace(workspace, target):
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace)
        if ignored_workspace_entry(relative):
            continue
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def first_error(result, fallback):
    errors = result.get("errors") or []
    if errors:
        return errors[0]
    if result.get("stderr_tail"):
        return result["stderr_tail"].strip().splitlines()[-1]
    return fallback


def prove_publish_clone(workspace_root, install_root, output_dir="dist"):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": PUBLISH_CLONE_FIXTURE_SCHEMA,
        "ok": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "fixture_branch": FIXTURE_BRANCH,
        "steps": [],
        "checks": {},
        "errors": [],
    }

    with tempfile.TemporaryDirectory(prefix="repers-publish-clone-") as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source"
        bare_remote = temp_root / "remote.git"
        clone = temp_root / "clone"
        clone_output = temp_root / "clone-output"
        source.mkdir()
        clone_output.mkdir()
        result["fixture_paths"] = {
            "temp_root": str(temp_root),
            "source": str(source),
            "bare_remote": str(bare_remote),
            "clone": str(clone),
            "clone_output": str(clone_output),
        }

        try:
            copy_workspace(workspace, source)
            result["steps"].append({"name": "copy_workspace", "ok": True, "path": str(source)})
        except Exception as exc:
            result["steps"].append({"name": "copy_workspace", "ok": False, "error": str(exc)})
            result["errors"].append(f"copy_workspace failed: {exc}")
            return write_result(result, output)

        for name, command, cwd in [
            ("git_init_source", ["git", "init"], source),
            ("git_disable_external_hooks", ["git", "config", "core.hooksPath", ".git/hooks"], source),
            ("git_checkout_fixture_branch", ["git", "checkout", "-B", FIXTURE_BRANCH], source),
            ("git_config_name", ["git", "config", "user.name", "RePERS Fixture"], source),
            ("git_config_email", ["git", "config", "user.email", "repers-fixture@example.invalid"], source),
            ("git_add_source", ["git", "add", "."], source),
            ("git_commit_source", ["git", "commit", "-m", "Publish clone fixture source"], source),
            ("git_init_bare_remote", ["git", "init", "--bare", str(bare_remote)], temp_root),
            ("git_remote_head", ["git", "symbolic-ref", "HEAD", f"refs/heads/{FIXTURE_BRANCH}"], bare_remote),
            ("git_add_origin", ["git", "remote", "add", "origin", str(bare_remote)], source),
            ("git_push_source", ["git", "push", "-u", "origin", FIXTURE_BRANCH], source),
            ("git_clone_remote", ["git", "clone", str(bare_remote), str(clone)], temp_root),
        ]:
            step = run_plain(command, cwd)
            result["steps"].append({"name": name, **step})
            if not step["ok"]:
                result["errors"].append(f"{name} failed: {first_error(step, 'command failed')}")
                return write_result(result, output)

        source_head = run_plain(["git", "rev-parse", "HEAD"], source)
        clone_head = run_plain(["git", "rev-parse", "HEAD"], clone)
        bare_refs = run_plain(["git", "show-ref"], bare_remote)
        clone_origin = run_plain(["git", "remote", "get-url", "origin"], clone)
        result["checks"]["source_head"] = source_head
        result["checks"]["clone_head"] = clone_head
        result["checks"]["bare_remote_refs"] = bare_refs
        result["checks"]["clone_origin"] = clone_origin
        source_sha = source_head.get("stdout_tail", "").strip()
        clone_sha = clone_head.get("stdout_tail", "").strip()
        if not source_head["ok"] or not clone_head["ok"] or not source_sha or source_sha != clone_sha:
            result["errors"].append("clone HEAD did not match pushed source HEAD")
        if FIXTURE_BRANCH not in bare_refs.get("stdout_tail", ""):
            result["errors"].append("bare remote did not contain the fixture branch")
        if clone_origin.get("stdout_tail", "").strip() != str(bare_remote):
            result["errors"].append("clone origin did not point at the local bare remote")

        cli = clone / ".repers" / "scripts" / "repers.py"
        commands = {
            "verify_install": [sys.executable, "-B", str(cli), "verify-install", "--json"],
            "capabilities_validate": [
                sys.executable,
                "-B",
                str(cli),
                "capabilities",
                "--action",
                "validate",
                "--json",
            ],
            "state": [sys.executable, "-B", str(cli), "state", "--output", str(clone_output), "--json"],
        }
        for name, command in commands.items():
            check = run_json(command, clone)
            result["checks"][name] = check
            if not check["ok"]:
                result["errors"].append(f"{name} command failed: {first_error(check, 'command failed')}")
                continue
            payload = check.get("json") or {}
            if name == "verify_install" and payload.get("ok") is not True:
                result["errors"].append("clone verify-install returned ok=false")
            if name == "capabilities_validate" and payload.get("ok") is not True:
                result["errors"].append("clone capabilities validate returned ok=false")
            if name == "state":
                state = payload.get("state") or {}
                if state.get("ok") is not True:
                    result["errors"].append("clone state returned ok=false")

    result["ok"] = not result["errors"]
    return write_result(result, output)


def write_result(result, output):
    result["ok"] = not result["errors"]
    path = Path(output) / "repers-publish-clone-fixture.json"
    result["path"] = str(path.resolve())
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result, path

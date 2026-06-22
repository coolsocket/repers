import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


RECEIVER_FIXTURE_SCHEMA = "repers.receiver_fixture.v1"


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


def run_plain(command, cwd):
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return {
        "command": [str(part) for part in command],
        "cwd": str(Path(cwd).resolve()),
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def prove_receiver(workspace_root, install_root, output_dir="dist", verify_package_roundtrip=False):
    from package_repers import PACKAGE_DIR_PREFIX, create_package

    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    package = create_package(output_dir, verify_roundtrip=verify_package_roundtrip)
    result = {
        "schema": RECEIVER_FIXTURE_SCHEMA,
        "ok": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "package": {
            "ok": package.get("ok"),
            "archive_path": package.get("archive_path"),
            "archive_sha256": package.get("archive_sha256"),
            "roundtrip_ok": package.get("roundtrip", {}).get("ok") if package.get("roundtrip") else None,
        },
        "steps": [],
        "checks": {},
        "errors": [],
    }
    if not package.get("ok"):
        result["errors"].append("package creation failed")
        return result

    with tempfile.TemporaryDirectory(prefix="repers-receiver-fixture-") as temp_dir:
        temp_root = Path(temp_dir)
        extract_root = temp_root / "extract"
        target_root = temp_root / "target"
        extract_root.mkdir()
        target_root.mkdir()

        try:
            with zipfile.ZipFile(package["archive_path"]) as zf:
                zf.extractall(extract_root)
            result["steps"].append({"name": "extract", "ok": True, "path": str(extract_root)})
        except Exception as exc:
            result["steps"].append({"name": "extract", "ok": False, "error": str(exc)})
            result["errors"].append(f"extract failed: {exc}")
            return result

        git_init = run_plain(["git", "init"], target_root)
        result["steps"].append({"name": "git_init", **git_init})
        if not git_init["ok"]:
            result["errors"].append("git init failed")
            return result

        installer = extract_root / PACKAGE_DIR_PREFIX / "scripts" / "install_repers.py"
        install_step = run_plain([sys.executable, str(installer), "--target", str(target_root)], extract_root / PACKAGE_DIR_PREFIX)
        result["steps"].append({"name": "install", **install_step})
        if not install_step["ok"]:
            result["errors"].append("install failed")
            return result

        cli = target_root / ".repers" / "scripts" / "repers.py"
        commands = {
            "verify_install": [sys.executable, str(cli), "verify-install", "--json"],
            "doctor": [sys.executable, str(cli), "doctor", "--json"],
            "bundle_status": [sys.executable, str(cli), "bundle-status", "--json"],
            "capabilities_validate": [sys.executable, str(cli), "capabilities", "--action", "validate", "--json"],
            "capabilities_search": [
                sys.executable,
                str(cli),
                "capabilities",
                "--action",
                "search",
                "--query",
                "fixture worker-command parallel dag",
                "--json",
            ],
            "fixture_prove": [sys.executable, str(cli), "fixture", "--action", "prove", "--task", "receiver-fixture", "--json"],
            "remote_bootstrap_fixture": [sys.executable, str(cli), "remote-bootstrap-fixture", "--json"],
            "publish_clone_fixture": [sys.executable, str(cli), "publish-clone-fixture", "--json"],
            "source_install_fixture": [sys.executable, str(cli), "source-install-fixture", "--json"],
        }
        for name, command in commands.items():
            check = run_json(command, target_root)
            result["checks"][name] = check
            if not check["ok"]:
                result["errors"].append(f"{name} command failed")
                continue
            payload = check.get("json") or {}
            if name == "verify_install" and payload.get("ok") is not True:
                result["errors"].append("verify-install returned ok=false")
            if name == "doctor" and payload.get("ok") is not True:
                result["errors"].append("doctor returned ok=false")
            if name == "bundle_status" and payload.get("ok") is not True:
                result["errors"].append("bundle-status returned ok=false")
            if name == "capabilities_validate" and payload.get("ok") is not True:
                result["errors"].append("capabilities validate returned ok=false")
            if name == "capabilities_search" and payload.get("entries", [{}])[0].get("id") != "orchestration-fixture":
                result["errors"].append("capabilities search did not rank orchestration-fixture first")
            if name == "fixture_prove" and payload.get("ok") is not True:
                result["errors"].append("fixture prove returned ok=false")
            if name == "remote_bootstrap_fixture" and payload.get("remote_bootstrap_fixture", {}).get("ok") is not True:
                result["errors"].append("remote-bootstrap fixture returned ok=false")
            if name == "publish_clone_fixture" and payload.get("publish_clone_fixture", {}).get("ok") is not True:
                result["errors"].append("publish-clone fixture returned ok=false")
            if name == "source_install_fixture" and payload.get("source_install_fixture", {}).get("ok") is not True:
                result["errors"].append("source-install fixture returned ok=false")

    result["ok"] = not result["errors"]
    return result

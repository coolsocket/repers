import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from publish_clone_fixture import copy_workspace, first_error, run_json, run_plain


SOURCE_INSTALL_FIXTURE_SCHEMA = "repers.source_install_fixture.v1"


def prove_source_install(workspace_root, install_root, output_dir="dist"):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": SOURCE_INSTALL_FIXTURE_SCHEMA,
        "ok": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "steps": [],
        "checks": {},
        "errors": [],
    }

    with tempfile.TemporaryDirectory(prefix="repers-source-install-") as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source"
        target = temp_root / "target"
        source.mkdir()
        target.mkdir()
        result["fixture_paths"] = {
            "temp_root": str(temp_root),
            "source": str(source),
            "target": str(target),
        }

        try:
            copy_workspace(workspace, source)
            result["steps"].append({"name": "copy_workspace", "ok": True, "path": str(source)})
        except Exception as exc:
            result["steps"].append({"name": "copy_workspace", "ok": False, "error": str(exc)})
            result["errors"].append(f"copy_workspace failed: {exc}")
            return write_result(result, output)

        git_init = run_plain(["git", "init"], target)
        result["steps"].append({"name": "git_init_target", **git_init})
        if not git_init["ok"]:
            result["errors"].append(f"git_init_target failed: {first_error(git_init, 'command failed')}")
            return write_result(result, output)

        source_cli = source / ".repers" / "scripts" / "repers.py"
        install_check = run_json(
            [
                sys.executable,
                "-B",
                str(source_cli),
                "install",
                "--target",
                str(target),
                "--json",
            ],
            source,
        )
        result["checks"]["source_install"] = install_check
        install_payload = install_check.get("json") or {}
        if not install_check["ok"] or install_payload.get("ok") is not True:
            result["errors"].append(f"source install command failed: {first_error(install_check, 'command failed')}")
            return write_result(result, output)
        if install_payload.get("install", {}).get("with_hook") is not True:
            result["errors"].append("source install command did not install the receiver hook")
            return write_result(result, output)

        target_cli = target / ".repers" / "scripts" / "repers.py"
        commands = {
            "verify_install": [sys.executable, "-B", str(target_cli), "verify-install", "--json"],
            "doctor": [sys.executable, "-B", str(target_cli), "doctor", "--json"],
            "capabilities_validate": [
                sys.executable,
                "-B",
                str(target_cli),
                "capabilities",
                "--action",
                "validate",
                "--json",
            ],
        }
        for name, command in commands.items():
            check = run_json(command, target)
            result["checks"][name] = check
            if not check["ok"]:
                result["errors"].append(f"{name} command failed: {first_error(check, 'command failed')}")
                continue
            payload = check.get("json") or {}
            if payload.get("ok") is not True:
                result["errors"].append(f"{name} returned ok=false")
            if name == "doctor" and payload.get("hook", {}).get("ok") is not True:
                result["errors"].append("doctor returned hook.ok=false")

    result["ok"] = not result["errors"]
    return write_result(result, output)


def write_result(result, output):
    result["ok"] = not result["errors"]
    path = Path(output) / "repers-source-install-fixture.json"
    result["path"] = str(path.resolve())
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result, path

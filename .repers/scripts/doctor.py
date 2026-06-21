import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


def check_command(name, args):
    path = shutil.which(name)
    if not path:
        return {"name": name, "ok": False, "path": None, "version": None}
    version = None
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=10)
        version = (proc.stdout or proc.stderr).splitlines()[0] if (proc.stdout or proc.stderr) else ""
    except Exception as exc:
        version = f"version check failed: {exc}"
    return {"name": name, "ok": True, "path": path, "version": version}


def check_git_repo(workspace_root):
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=workspace_root, capture_output=True, text=True, check=True)
        return {"ok": True, "root": proc.stdout.strip()}
    except Exception as exc:
        return {"ok": False, "root": None, "error": str(exc)}


def check_hook(workspace_root):
    hook_path = Path(workspace_root) / ".git" / "hooks" / "pre-commit"
    if not hook_path.exists():
        return {"ok": False, "path": str(hook_path), "installed": False}
    text = hook_path.read_text(encoding="utf-8", errors="ignore")
    return {"ok": "RePERS" in text or "repers.py" in text, "path": str(hook_path), "installed": True}


def check_index(index_db_path):
    path = Path(index_db_path)
    if not path.exists():
        return {"ok": False, "path": str(path), "documents": 0}
    try:
        with sqlite3.connect(path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        return {"ok": True, "path": str(path), "documents": count}
    except Exception as exc:
        return {"ok": False, "path": str(path), "documents": 0, "error": str(exc)}


def check_lsp_guard(path):
    exists = Path(path).exists()
    return {"ok": exists, "path": path, "installed": exists}


def check_backend(name):
    if name == "local":
        return {"name": "local", "ok": True, "mode": "built-in"}
    if name == "worker-command":
        return {"name": "worker-command", "ok": True, "mode": "built-in", "configured": bool(os.environ.get("REPERS_WORKER_COMMAND"))}
    if name == "openai-agents":
        try:
            __import__("agents")
            return {"name": name, "ok": True, "mode": "optional"}
        except Exception as exc:
            return {"name": name, "ok": False, "mode": "optional", "error": str(exc)}
    if name == "langgraph":
        try:
            __import__("langgraph")
            return {"name": name, "ok": True, "mode": "optional"}
        except Exception as exc:
            return {"name": name, "ok": False, "mode": "optional", "error": str(exc)}
    if name == "mcp":
        try:
            __import__("mcp")
            return {"name": name, "ok": True, "mode": "optional"}
        except Exception as exc:
            return {"name": name, "ok": False, "mode": "optional", "error": str(exc)}
    return {"name": name, "ok": False, "mode": "unknown"}


def run_doctor(workspace_root, install_root, index_db_path, lsp_guard_path):
    checks = {
        "python": check_command("python", ["python", "--version"]),
        "git": check_command("git", ["git", "--version"]),
        "git_repo": check_git_repo(workspace_root),
        "hook": check_hook(workspace_root),
        "index": check_index(index_db_path),
        "lsp_guard": check_lsp_guard(lsp_guard_path),
        "backends": [check_backend(name) for name in ["local", "worker-command", "openai-agents", "langgraph", "mcp"]],
        "paths": {
            "workspace_root": str(Path(workspace_root).resolve()),
            "install_root": str(Path(install_root).resolve()),
        },
    }
    required_ok = checks["python"]["ok"] and checks["git"]["ok"] and checks["git_repo"]["ok"]
    checks["ok"] = bool(required_ok)
    return checks


def fix_doctor(workspace_root, install_root, index_db_path, lsp_guard_path, skills_dir, refresh_index=False):
    actions = []
    errors = []
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()

    try:
        from install_repers import ensure_gitignore, write_hook

        gitignore_path = workspace / ".gitignore"
        before = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
        updated_gitignore = ensure_gitignore(workspace)
        after = updated_gitignore.read_text(encoding="utf-8") if updated_gitignore.exists() else ""
        if before != after:
            actions.append({"action": "update_gitignore", "path": str(updated_gitignore)})

        hook = check_hook(workspace)
        if not hook["ok"]:
            hook_path = write_hook(workspace, install)
            actions.append({"action": "install_hook", "path": str(hook_path)})
    except Exception as exc:
        errors.append({"action": "install_hook", "error": str(exc)})

    index = check_index(index_db_path)
    if refresh_index or not index["ok"]:
        try:
            from research_index import refresh

            refreshed = refresh(index_db_path, str(workspace), skills_dir)
            actions.append(
                {
                    "action": "refresh_index",
                    "path": refreshed["db_path"],
                    "documents_indexed": refreshed["documents_indexed"],
                }
            )
        except Exception as exc:
            errors.append({"action": "refresh_index", "error": str(exc)})

    result = run_doctor(str(workspace), str(install), index_db_path, lsp_guard_path)
    result["fix"] = {"actions": actions, "errors": errors, "ok": not errors}
    result["ok"] = bool(result["ok"] and not errors)
    return result


def format_doctor(result):
    lines = ["RePERS Doctor"]
    lines.append(f"Overall: {'OK' if result['ok'] else 'NEEDS ATTENTION'}")
    lines.append(f"Python: {'OK' if result['python']['ok'] else 'MISSING'} {result['python'].get('version') or ''}")
    lines.append(f"Git: {'OK' if result['git']['ok'] else 'MISSING'} {result['git'].get('version') or ''}")
    lines.append(f"Git repo: {'OK' if result['git_repo']['ok'] else 'MISSING'}")
    lines.append(f"Hook: {'OK' if result['hook']['ok'] else 'MISSING'}")
    lines.append(f"Index: {'OK' if result['index']['ok'] else 'MISSING'} documents={result['index'].get('documents', 0)}")
    lines.append(f"LSP Guard: {'OK' if result['lsp_guard']['ok'] else 'OPTIONAL MISSING'}")
    lines.append("Backends:")
    for backend in result["backends"]:
        lines.append(f"  - {backend['name']}: {'OK' if backend['ok'] else 'OPTIONAL MISSING'}")
    return "\n".join(lines)

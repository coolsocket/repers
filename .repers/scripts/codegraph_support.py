import json
import os
import shutil
import subprocess
from pathlib import Path


KNOWN_CODEGRAPH_JS = Path("C:/Users/Administrator/Desktop/coding/codegraph/dist/bin/codegraph.js")


def resolve_codegraph_command(explicit_bin=None):
    candidates = []
    if explicit_bin:
        candidates.append(Path(explicit_bin))
    env_bin = os.environ.get("CODEGRAPH_BIN")
    if env_bin:
        candidates.append(Path(env_bin))
    path_bin = shutil.which("codegraph")
    if path_bin:
        candidates.append(Path(path_bin))
    candidates.append(KNOWN_CODEGRAPH_JS)

    for candidate in candidates:
        if not candidate:
            continue
        if candidate.suffix.lower() == ".js" and candidate.exists():
            node_bin = shutil.which("node")
            if not node_bin:
                return {
                    "available": False,
                    "bin": str(candidate),
                    "command_prefix": [],
                    "error": "CodeGraph JavaScript entrypoint found, but node is not on PATH",
                }
            return {
                "available": True,
                "bin": str(candidate),
                "command_prefix": [node_bin, str(candidate)],
                "error": "",
            }
        if candidate.exists():
            return {
                "available": True,
                "bin": str(candidate),
                "command_prefix": [str(candidate)],
                "error": "",
            }
        if explicit_bin and candidate == Path(explicit_bin):
            return {
                "available": False,
                "bin": str(candidate),
                "command_prefix": [],
                "error": f"CodeGraph CLI not found at explicit path: {candidate}",
            }

    return {
        "available": False,
        "bin": "",
        "command_prefix": [],
        "error": "CodeGraph CLI not found on PATH, CODEGRAPH_BIN, or known local checkout",
    }


def _run_json_or_text(command, cwd, timeout_seconds):
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    parsed = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "command": command,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
        "json": parsed,
    }


def collect_codegraph_evidence(
    repo_root,
    query,
    limit=12,
    init=False,
    sync=True,
    codegraph_bin=None,
    timeout_seconds=30,
):
    repo = Path(repo_root).resolve()
    resolved = resolve_codegraph_command(codegraph_bin)
    evidence = {
        "provider": "codegraph",
        "enabled": True,
        "available": resolved["available"],
        "ok": False,
        "bin": resolved["bin"],
        "repo": str(repo),
        "index_exists": (repo / ".codegraph" / "codegraph.db").exists(),
        "actions": [],
        "status": None,
        "query": None,
        "context": None,
        "uncertainty": [
            "CodeGraph context can over-recall common names.",
            "CodeGraph impact and relationship output should be confirmed against source for high-risk edits.",
        ],
        "errors": [],
    }

    if not resolved["available"]:
        evidence["errors"].append(resolved["error"])
        return evidence

    prefix = resolved["command_prefix"]
    try:
        if not evidence["index_exists"]:
            if not init:
                evidence["errors"].append("CodeGraph index missing; rerun with --codegraph-init to create it")
                return evidence
            init_result = _run_json_or_text(prefix + ["init", "-i", str(repo)], repo, timeout_seconds)
            evidence["actions"].append({"name": "init", **init_result})
            evidence["index_exists"] = (repo / ".codegraph" / "codegraph.db").exists()
            if not init_result["ok"]:
                evidence["errors"].append("CodeGraph init failed")
                return evidence

        if sync:
            sync_result = _run_json_or_text(prefix + ["sync", str(repo)], repo, timeout_seconds)
            evidence["actions"].append({"name": "sync", **sync_result})
            if not sync_result["ok"]:
                evidence["errors"].append("CodeGraph sync failed")

        status_result = _run_json_or_text(prefix + ["status", str(repo)], repo, timeout_seconds)
        evidence["status"] = status_result["json"] if status_result["json"] is not None else {
            "ok": status_result["ok"],
            "stdout_tail": status_result["stdout_tail"],
            "stderr_tail": status_result["stderr_tail"],
            "returncode": status_result["returncode"],
        }
        if not status_result["ok"]:
            evidence["errors"].append("CodeGraph status failed")

        query_result = _run_json_or_text(
            prefix + ["query", "--path", str(repo), "--json", "--limit", str(limit), query],
            repo,
            timeout_seconds,
        )
        evidence["query"] = query_result["json"] if query_result["json"] is not None else {
            "ok": query_result["ok"],
            "stdout_tail": query_result["stdout_tail"],
            "stderr_tail": query_result["stderr_tail"],
            "returncode": query_result["returncode"],
        }
        if not query_result["ok"]:
            evidence["errors"].append("CodeGraph query failed")

        context_result = _run_json_or_text(prefix + ["context", "--path", str(repo), query], repo, timeout_seconds)
        evidence["context"] = context_result["stdout_tail"]
        if not context_result["ok"]:
            evidence["errors"].append("CodeGraph context failed")

        evidence["ok"] = status_result["ok"] and query_result["ok"] and context_result["ok"] and not evidence["errors"]
    except subprocess.TimeoutExpired as exc:
        evidence["errors"].append(f"CodeGraph command timed out after {timeout_seconds}s: {exc.cmd}")
    except OSError as exc:
        evidence["errors"].append(f"CodeGraph command failed to start: {exc}")
    return evidence

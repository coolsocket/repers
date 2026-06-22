#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


SOURCE_ROOT = Path(__file__).resolve().parents[1]
INSTALL_DIR_NAME = ".repers"
REPERS_VERSION = "0.1.0"
MANIFEST_NAME = "manifest.json"


def copy_tree(src, dst, ignore=None):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=ignore)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_excluded(relative):
    rel = relative.replace("\\", "/")
    parts = PurePosixPath(rel).parts
    return (
        rel == MANIFEST_NAME
        or rel.startswith("index/")
        or rel.startswith(".repers/")
        or "__pycache__" in parts
        or rel.endswith(".pyc")
    )


def git_source_state():
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=SOURCE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=SOURCE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        return {"ok": True, "commit": commit, "dirty": bool(status), "status_count": len(status)}
    except Exception as exc:
        return {"ok": False, "commit": None, "dirty": None, "status_count": 0, "error": str(exc)}


def installed_file_records(install_dir):
    records = []
    for path in sorted(install_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(install_dir).as_posix()
        if manifest_excluded(relative):
            continue
        records.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def load_manifest(install_dir):
    manifest_path = Path(install_dir) / MANIFEST_NAME
    if not manifest_path.exists():
        return manifest_path, None, [f"manifest not found: {manifest_path}"]
    try:
        return manifest_path, json.loads(manifest_path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return manifest_path, None, [f"manifest is not valid JSON: {exc}"]


def safe_manifest_path(install_dir, relative):
    rel = str(relative).replace("\\", "/")
    parts = PurePosixPath(rel).parts
    if not rel or rel.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"unsafe manifest path: {relative}")
    return Path(install_dir).joinpath(*parts)


def verify_manifest(install_dir, strict_extra=False):
    install_dir = Path(install_dir).resolve()
    manifest_path, manifest, load_errors = load_manifest(install_dir)
    result = {
        "schema": "repers.install_verify.v1",
        "ok": False,
        "install_root": str(install_dir),
        "manifest_path": str(manifest_path.resolve()),
        "manifest_schema": manifest.get("schema") if isinstance(manifest, dict) else None,
        "manifest_version": manifest.get("version") if isinstance(manifest, dict) else None,
        "strict_extra": bool(strict_extra),
        "file_count": 0,
        "checked_count": 0,
        "missing": [],
        "changed": [],
        "extra": [],
        "errors": load_errors,
    }
    if load_errors:
        return result
    if not isinstance(manifest, dict):
        result["errors"].append("manifest root is not an object")
        return result
    if manifest.get("schema") != "repers.install_manifest.v1":
        result["errors"].append(f"unsupported manifest schema: {manifest.get('schema')}")
        return result

    files = manifest.get("files")
    if not isinstance(files, list):
        result["errors"].append("manifest files field is not a list")
        return result

    manifest_paths = set()
    result["file_count"] = len(files)
    for entry in files:
        if not isinstance(entry, dict):
            result["errors"].append("manifest file entry is not an object")
            continue
        relative = entry.get("path")
        if not isinstance(relative, str):
            result["errors"].append("manifest file entry is missing a string path")
            continue
        try:
            file_path = safe_manifest_path(install_dir, relative)
        except ValueError as exc:
            result["errors"].append(str(exc))
            continue
        manifest_paths.add(relative.replace("\\", "/"))
        if not file_path.exists():
            result["missing"].append(relative)
            continue
        if not file_path.is_file():
            result["changed"].append({"path": relative, "reason": "not a file"})
            continue
        expected_size = entry.get("size_bytes")
        expected_sha = entry.get("sha256")
        actual_size = file_path.stat().st_size
        actual_sha = sha256_file(file_path)
        result["checked_count"] += 1
        reasons = []
        if expected_size != actual_size:
            reasons.append("size")
        if expected_sha != actual_sha:
            reasons.append("sha256")
        if reasons:
            result["changed"].append(
                {
                    "path": relative,
                    "reason": ",".join(reasons),
                    "expected_size_bytes": expected_size,
                    "actual_size_bytes": actual_size,
                    "expected_sha256": expected_sha,
                    "actual_sha256": actual_sha,
                }
            )

    for path in sorted(install_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(install_dir).as_posix()
        if manifest_excluded(relative) or relative in manifest_paths:
            continue
        result["extra"].append(relative)

    result["ok"] = (
        not result["errors"]
        and not result["missing"]
        and not result["changed"]
        and (not strict_extra or not result["extra"])
    )
    return result


def write_manifest(target_root, install_dir, with_hook, hook_policy, hook_path=None, gitignore_path=None):
    manifest = {
        "schema": "repers.install_manifest.v1",
        "version": REPERS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(SOURCE_ROOT.resolve()),
        "target_root": str(target_root.resolve()),
        "install_root": str(install_dir.resolve()),
        "source_git": git_source_state(),
        "with_hook": bool(with_hook),
        "hook_policy": hook_policy,
        "hook_path": str(hook_path.resolve()) if hook_path else None,
        "gitignore_path": str(gitignore_path.resolve()) if gitignore_path else None,
        "files": installed_file_records(install_dir),
    }
    manifest["file_count"] = len(manifest["files"])
    manifest_path = install_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path, manifest


def update_manifest_hook_policy(install_dir, hook_policy, hook_path=None):
    manifest_path = install_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["hook_policy"] = hook_policy
    manifest["with_hook"] = True
    manifest["hook_path"] = str(hook_path.resolve()) if hook_path else manifest.get("hook_path")
    manifest["files"] = installed_file_records(install_dir)
    manifest["file_count"] = len(manifest["files"])
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def write_hook(target_root, install_dir, audit_policy="warn"):
    if audit_policy not in {"warn", "strict"}:
        raise ValueError(f"Unsupported RePERS hook policy: {audit_policy}")
    hooks_dir = target_root / ".git" / "hooks"
    if not hooks_dir.exists():
        raise RuntimeError(f"Git hooks directory not found: {hooks_dir}")

    hook_path = hooks_dir / "pre-commit"
    python_entry = install_dir / "scripts" / "repers.py"
    hook_body = f"""#!/bin/sh
# Installed by RePERS. Set REPERS_SKIP_HOOK=1 to bypass locally.
if [ "$REPERS_SKIP_HOOK" = "1" ]; then
  echo "RePERS hook skipped because REPERS_SKIP_HOOK=1"
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
export REPERS_WORKSPACE_ROOT="$REPO_ROOT"
if [ "$REPERS_AUDIT_STRICT_WARNINGS" = "1" ] || [ "{audit_policy}" = "strict" ]; then
  python -B "{python_entry.as_posix()}" audit --strict-warnings
else
  python -B "{python_entry.as_posix()}" audit
fi
"""
    hook_path.write_text(hook_body, encoding="utf-8", newline="\n")
    current_mode = hook_path.stat().st_mode
    hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    update_manifest_hook_policy(install_dir, audit_policy, hook_path=hook_path)
    return hook_path


def ensure_gitignore(target_root):
    gitignore_path = target_root / ".gitignore"
    existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    lines = [
        "# RePERS",
        ".repers/**/__pycache__/",
        ".repers/**/*.pyc",
        "repers_tasks/**/__pycache__/",
        "repers_tasks/**/*.pyc",
        "tests/**/__pycache__/",
        "tests/**/*.pyc",
        "docs/goal/**/.goal-machine/",
    ]
    missing = [line for line in lines if line not in existing.splitlines()]
    if not missing:
        return gitignore_path
    separator = "" if not existing or existing.endswith("\n") else "\n"
    gitignore_path.write_text(existing + separator + "\n".join(missing) + "\n", encoding="utf-8")
    return gitignore_path


def ensure_gitattributes(target_root):
    gitattributes_path = target_root / ".gitattributes"
    source_path = SOURCE_ROOT / ".gitattributes"
    if source_path.exists():
        lines = source_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = [
            "* text=auto",
            "*.md text eol=lf",
            "*.json text eol=lf",
            "*.py text eol=lf",
            "*.yml text eol=lf",
            "*.yaml text eol=lf",
            ".repers/hooks/* text eol=lf",
        ]
    existing = gitattributes_path.read_text(encoding="utf-8") if gitattributes_path.exists() else ""
    existing_lines = existing.splitlines()
    missing = [line for line in lines if line and line not in existing_lines]
    if not missing:
        return gitattributes_path
    separator = "" if not existing or existing.endswith("\n") else "\n"
    gitattributes_path.write_text(existing + separator + "\n".join(missing) + "\n", encoding="utf-8")
    return gitattributes_path


def refresh_installed_index(target_root, install_dir):
    try:
        from research_index import refresh

        index_path = install_dir / "index" / "repers.db"
        return refresh(index_path, target_root, None)
    except Exception as exc:
        return {"documents_indexed": 0, "db_path": str((install_dir / "index" / "repers.db").resolve()), "error": str(exc)}


def install(target, with_hook, hook_policy="warn"):
    target_root = Path(target).resolve()
    if not target_root.exists():
        raise RuntimeError(f"Target directory does not exist: {target_root}")
    if not (target_root / ".git").exists():
        raise RuntimeError(f"Target is not a Git repository: {target_root}")

    install_dir = target_root / INSTALL_DIR_NAME
    if install_dir.exists():
        shutil.rmtree(install_dir)
    install_dir.mkdir()

    clean_python = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    clean_docs = shutil.ignore_patterns("goal", "__pycache__", "*.pyc", "*.pyo")
    copy_tree(SOURCE_ROOT / "scripts", install_dir / "scripts", ignore=clean_python)
    copy_tree(SOURCE_ROOT / "capabilities", install_dir / "capabilities")
    copy_tree(SOURCE_ROOT / "templates", install_dir / "templates")
    copy_tree(SOURCE_ROOT / "docs", install_dir / "docs", ignore=clean_docs)
    copy_tree(SOURCE_ROOT / "hooks", install_dir / "hooks")
    index_result = refresh_installed_index(target_root, install_dir)
    gitignore_path = ensure_gitignore(target_root)
    gitattributes_path = ensure_gitattributes(target_root)

    hook_path = None
    if with_hook:
        hook_path = write_hook(target_root, install_dir, audit_policy=hook_policy)
    manifest_path, manifest = write_manifest(target_root, install_dir, with_hook, hook_policy, hook_path=hook_path, gitignore_path=gitignore_path)

    print(f"[OK] Installed RePERS into {install_dir}")
    if hook_path:
        print(f"[OK] Installed pre-commit hook at {hook_path} (policy={hook_policy})")
    print(f"[OK] Updated ignore rules at {gitignore_path}")
    print(f"[OK] Updated attributes rules at {gitattributes_path}")
    if index_result.get("error"):
        print(f"[!] RePERS index refresh warning: {index_result['error']}")
    else:
        print(f"[OK] Refreshed RePERS index at {index_result['db_path']} ({index_result['documents_indexed']} documents)")
    print(f"[OK] Wrote install manifest at {manifest_path} ({manifest['file_count']} files)")
    print("[OK] Try: python .repers/scripts/repers.py --help")


def main():
    parser = argparse.ArgumentParser(description="Install RePERS into a target Git repository")
    parser.add_argument("--target", default=".", help="Target Git repository path")
    parser.add_argument("--no-hook", action="store_true", help="Copy files without installing the pre-commit hook")
    parser.add_argument("--hook-policy", choices=["warn", "strict"], default="warn", help="Whether the installed hook allows warnings or treats them as failures")
    args = parser.parse_args()
    install(args.target, with_hook=not args.no_hook, hook_policy=args.hook_policy)


if __name__ == "__main__":
    main()

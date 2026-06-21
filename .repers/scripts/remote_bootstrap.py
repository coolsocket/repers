import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from publish_handoff import create_publish_handoff, default_pr_title, remote_records, run_git


REMOTE_BOOTSTRAP_SCHEMA = "repers.remote_bootstrap.v1"
REMOTE_BOOTSTRAP_APPLY_FIXTURE_SCHEMA = "repers.remote_bootstrap_apply_fixture.v1"


def command_record(step_id, title, command, status, reason):
    return {
        "id": step_id,
        "title": title,
        "command": command,
        "status": status,
        "reason": reason,
    }


def current_git_state(workspace_root):
    branch = run_git(["branch", "--show-current"], workspace_root)
    head = run_git(["rev-parse", "HEAD"], workspace_root)
    status = run_git(["status", "--porcelain"], workspace_root)
    records = remote_records(workspace_root)
    entries = [line for line in status.get("stdout", "").splitlines() if line.strip()] if status["ok"] else []
    return {
        "branch": branch["stdout"] if branch["ok"] else None,
        "head_sha": head["stdout"] if head["ok"] else None,
        "has_head": bool(head["ok"] and head["stdout"]),
        "dirty": bool(entries) if status["ok"] else None,
        "status_count": len(entries),
        "status_entries": entries[:100],
        "remote_count": len({record["name"] for record in records}),
        "remotes": records,
    }


def matching_remote_urls(records, remote_name):
    return sorted({record["url"] for record in records if record.get("name") == remote_name})


def build_remote_actions(git, remote_name, remote_url, base_branch, pr_title, handoff_path):
    branch = git.get("branch") or "<branch>"
    concrete_remote_url = remote_url or "<remote-url>"
    has_named_remote = bool(matching_remote_urls(git.get("remotes", []), remote_name))
    clean_branch = bool(git.get("has_head") and git.get("branch") and not git.get("dirty"))
    remote_available = has_named_remote or bool(remote_url)

    return [
        command_record(
            "inspect_remotes",
            "Inspect current Git remotes",
            "git remote -v",
            "done",
            "Remote state was inspected before generating this bootstrap artifact.",
        ),
        command_record(
            "add_remote",
            "Configure publication remote",
            f"git remote add {remote_name} {concrete_remote_url}",
            "done" if has_named_remote else "ready" if remote_url else "blocked",
            "Named remote already exists." if has_named_remote else "Remote URL was provided." if remote_url else "No remote URL was provided.",
        ),
        command_record(
            "publish_handoff",
            "Regenerate publish handoff evidence",
            f"python .repers/scripts/repers.py publish-handoff --remote-name {remote_name} --remote-url {concrete_remote_url} --base-branch {base_branch} --pr-title \"{pr_title}\" --json",
            "ready" if remote_url or has_named_remote else "blocked",
            f"Handoff path: {handoff_path}",
        ),
        command_record(
            "verify_publish_ready",
            "Verify objective audit after remote setup",
            "python .repers/scripts/repers.py objective-audit --deep --json",
            "ready" if remote_available else "blocked",
            "Run after the remote is configured and publish handoff is refreshed.",
        ),
        command_record(
            "push_branch",
            "Push release branch",
            f"git push -u {remote_name} {branch}",
            "ready" if clean_branch and remote_available else "blocked",
            "Clean committed branch and remote are available." if clean_branch else "Commit or intentionally exclude working tree changes first.",
        ),
        command_record(
            "open_draft_pr",
            "Open draft pull request",
            f"gh pr create --draft --base {base_branch} --head {branch} --title \"{pr_title}\" --body-file {handoff_path}",
            "ready" if clean_branch and remote_available else "blocked",
            "Requires GitHub CLI authentication and a pushed branch.",
        ),
    ]


def apply_remote(workspace, remote_name, remote_url):
    applied = {
        "requested": True,
        "ok": True,
        "changed": False,
        "remote_name": remote_name,
        "remote_url": remote_url,
        "actions": [],
        "errors": [],
    }
    if not remote_url:
        applied["ok"] = False
        applied["errors"].append("--apply requires --remote-url")
        return applied

    before = remote_records(workspace)
    urls = matching_remote_urls(before, remote_name)
    if remote_url in urls:
        applied["actions"].append({"name": "remote_exists", "ok": True, "reason": "matching remote already configured"})
        return applied
    if urls:
        applied["ok"] = False
        applied["errors"].append(
            f"remote '{remote_name}' already exists with different URL(s): {', '.join(urls)}"
        )
        return applied

    proc = subprocess.run(
        ["git", "remote", "add", remote_name, remote_url],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    applied["changed"] = proc.returncode == 0
    applied["ok"] = proc.returncode == 0
    applied["actions"].append(
        {
            "name": "git_remote_add",
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-1000:],
            "stderr_tail": proc.stderr[-1000:],
        }
    )
    if proc.returncode != 0:
        applied["errors"].append("git remote add failed")
    return applied


def write_markdown(bootstrap, markdown_path):
    lines = [
        "# RePERS Remote Bootstrap",
        "",
        f"- Generated: `{bootstrap['generated_at']}`",
        f"- Remote name: `{bootstrap['remote']['name']}`",
        f"- Remote URL provided: `{bootstrap['remote']['provided_url']}`",
        f"- Apply requested: `{bootstrap['applied']['requested']}`",
        f"- Apply changed remote: `{bootstrap['applied']['changed']}`",
        f"- OK: `{bootstrap['ok']}`",
        "",
        "## Safety",
        "",
        "- No branch push is executed by this command.",
        "- No pull request is opened by this command.",
        "- Git remotes are changed only when `--apply --remote-url <url>` is passed.",
        "- Existing remotes with different URLs are not overwritten.",
        "",
        "## Actions",
        "",
    ]
    for action in bootstrap["actions"]:
        lines.extend(
            [
                f"### {action['id']}: {action['title']}",
                "",
                f"- Status: `{action['status']}`",
                f"- Reason: {action['reason']}",
                "",
                "```powershell",
                action["command"],
                "```",
                "",
            ]
        )
    if bootstrap["applied"]["errors"]:
        lines.extend(["## Apply Errors", ""])
        lines.extend(f"- {error}" for error in bootstrap["applied"]["errors"])
        lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def create_remote_bootstrap(
    workspace_root,
    install_root,
    output_dir="dist",
    remote_name="origin",
    remote_url=None,
    base_branch="main",
    pr_title=None,
    include_package=False,
    verify_roundtrip=False,
    apply=False,
):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    applied = {
        "requested": bool(apply),
        "ok": True,
        "changed": False,
        "remote_name": remote_name,
        "remote_url": remote_url,
        "actions": [],
        "errors": [],
    }
    if apply:
        applied = apply_remote(workspace, remote_name, remote_url)

    title = pr_title or default_pr_title(workspace)
    handoff, handoff_json_path, handoff_md_path = create_publish_handoff(
        workspace,
        install,
        output_dir=output,
        remote_name=remote_name,
        remote_url=remote_url,
        base_branch=base_branch,
        pr_title=title,
        include_package=include_package,
        verify_roundtrip=verify_roundtrip,
    )
    git = current_git_state(workspace)
    actions = build_remote_actions(git, remote_name, remote_url, base_branch, title, str(handoff_md_path.resolve()))
    bootstrap = {
        "schema": REMOTE_BOOTSTRAP_SCHEMA,
        "ok": bool(applied["ok"] and handoff.get("ok")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "remote": {
            "name": remote_name,
            "provided_url": remote_url,
            "records": git["remotes"],
            "named_remote_urls": matching_remote_urls(git["remotes"], remote_name),
        },
        "git": git,
        "applied": applied,
        "publish_handoff": {
            "ok": bool(handoff.get("ok")),
            "path": str(Path(handoff_json_path).resolve()),
            "markdown_path": str(Path(handoff_md_path).resolve()),
            "publish_ready": bool(handoff.get("publish_ready")),
            "missing_for_publish": handoff.get("missing_for_publish", []),
        },
        "actions": actions,
        "safety": {
            "executes_push": False,
            "opens_pull_request": False,
            "mutates_git_remote_by_default": False,
            "mutates_git_remote": bool(apply and applied.get("changed")),
            "requires_apply_for_remote_mutation": True,
            "overwrites_existing_remote": False,
        },
    }
    json_path = output / "repers-remote-bootstrap.json"
    md_path = output / "repers-remote-bootstrap.md"
    bootstrap["path"] = str(json_path.resolve())
    bootstrap["markdown_path"] = str(md_path.resolve())
    json_path.write_text(json.dumps(bootstrap, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(bootstrap, md_path)
    return bootstrap, json_path, md_path


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


def prove_remote_bootstrap_apply(workspace_root, install_root, output_dir="dist"):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": REMOTE_BOOTSTRAP_APPLY_FIXTURE_SCHEMA,
        "ok": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "steps": [],
        "checks": {},
        "errors": [],
    }

    with tempfile.TemporaryDirectory(prefix="repers-remote-apply-") as temp_dir:
        temp_root = Path(temp_dir)
        target = temp_root / "target"
        bare_remote = temp_root / "remote.git"
        fixture_output = temp_root / "output"
        target.mkdir()
        fixture_output.mkdir()

        for name, command, cwd in [
            ("git_init", ["git", "init"], target),
            ("git_config_name", ["git", "config", "user.name", "RePERS Fixture"], target),
            ("git_config_email", ["git", "config", "user.email", "repers-fixture@example.invalid"], target),
        ]:
            step = run_plain(command, cwd)
            result["steps"].append({"name": name, **step})
            if not step["ok"]:
                result["errors"].append(f"{name} failed")
                result["path"] = str((output / "repers-remote-bootstrap-fixture.json").resolve())
                Path(result["path"]).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                return result, Path(result["path"])

        (target / "README.md").write_text("# RePERS remote bootstrap fixture\n", encoding="utf-8")
        for name, command in [
            ("git_add_seed", ["git", "add", "README.md"]),
            ("git_commit_seed", ["git", "commit", "-m", "Seed fixture repository"]),
        ]:
            step = run_plain(command, target)
            result["steps"].append({"name": name, **step})
            if not step["ok"]:
                result["errors"].append(f"{name} failed")
                result["path"] = str((output / "repers-remote-bootstrap-fixture.json").resolve())
                Path(result["path"]).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                return result, Path(result["path"])

        installer = install / "scripts" / "install_repers.py"
        install_step = run_plain([sys.executable, str(installer), "--target", str(target), "--no-hook"], workspace)
        result["steps"].append({"name": "install_repers", **install_step})
        if not install_step["ok"]:
            result["errors"].append("install_repers failed")
            result["path"] = str((output / "repers-remote-bootstrap-fixture.json").resolve())
            Path(result["path"]).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            return result, Path(result["path"])

        install_paths = [".repers", ".gitignore"]
        if (target / "docs").exists():
            install_paths.append("docs")
        commit_installed = run_plain(["git", "add", *install_paths], target)
        result["steps"].append({"name": "git_add_repers", **commit_installed})
        if not commit_installed["ok"]:
            result["errors"].append("git_add_repers failed")
        else:
            commit = run_plain(["git", "commit", "-m", "Install RePERS fixture runtime"], target)
            result["steps"].append({"name": "git_commit_repers", **commit})
            if not commit["ok"]:
                result["errors"].append("git_commit_repers failed")

        bare_init = run_plain(["git", "init", "--bare", str(bare_remote)], temp_root)
        result["steps"].append({"name": "git_init_bare_remote", **bare_init})
        if not bare_init["ok"]:
            result["errors"].append("git_init_bare_remote failed")

        cli = target / ".repers" / "scripts" / "repers.py"
        bootstrap_check = run_json(
            [
                sys.executable,
                str(cli),
                "remote-bootstrap",
                "--remote-url",
                str(bare_remote),
                "--output",
                str(fixture_output),
                "--apply",
                "--json",
            ],
            target,
        )
        result["checks"]["remote_bootstrap_apply"] = bootstrap_check
        bootstrap = (bootstrap_check.get("json") or {}).get("remote_bootstrap") or {}
        if not bootstrap_check["ok"] or bootstrap.get("ok") is not True:
            result["errors"].append("remote-bootstrap --apply failed")
        if bootstrap.get("applied", {}).get("changed") is not True:
            result["errors"].append("remote-bootstrap did not report changed remote")
        if str(bare_remote) not in bootstrap.get("remote", {}).get("named_remote_urls", []):
            result["errors"].append("bootstrap artifact did not record the bare remote URL")

        remote_show = run_plain(["git", "remote", "get-url", "origin"], target)
        result["checks"]["remote_url"] = remote_show
        if remote_show.get("stdout_tail", "").strip() != str(bare_remote):
            result["errors"].append("configured origin URL did not match bare remote")

        branch = bootstrap.get("git", {}).get("branch") or "master"
        push = run_plain(["git", "push", "-u", "origin", branch], target)
        result["checks"]["local_push"] = push
        if not push["ok"]:
            result["errors"].append("local push to bare remote failed")

        remote_refs = run_plain(["git", "show-ref"], bare_remote)
        result["checks"]["bare_remote_refs"] = remote_refs
        if branch not in remote_refs.get("stdout_tail", ""):
            result["errors"].append("bare remote did not receive the pushed branch")

    result["ok"] = not result["errors"]
    path = output / "repers-remote-bootstrap-fixture.json"
    result["path"] = str(path.resolve())
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result, path

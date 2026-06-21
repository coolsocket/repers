import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from release_evidence import build_release_evidence


PUBLISH_HANDOFF_SCHEMA = "repers.publish_handoff.v1"


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


def remote_records(workspace_root):
    remote = run_git(["remote", "-v"], workspace_root)
    records = []
    seen = set()
    if remote["ok"]:
        for line in remote["stdout"].splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            name, url, kind = parts[0], parts[1], parts[2].strip("()")
            key = (name, url, kind)
            if key in seen:
                continue
            seen.add(key)
            records.append({"name": name, "url": url, "kind": kind})
    return records


def default_pr_title(workspace_root):
    subject = run_git(["log", "-1", "--pretty=%s"], workspace_root)
    if subject["ok"] and subject["stdout"]:
        return subject["stdout"].replace("-", " ")
    return "Publish RePERS installable workflow bundle"


def command_record(step_id, title, command, status, reason):
    return {
        "id": step_id,
        "title": title,
        "command": command,
        "status": status,
        "reason": reason,
    }


def build_publish_actions(evidence, remote_name, remote_url, base_branch, pr_title):
    git = evidence["git"]
    branch = git.get("branch") or "<branch>"
    has_remote = git.get("remote_count", 0) > 0
    clean = bool(git.get("has_head")) and not git.get("dirty") and bool(git.get("branch"))
    concrete_remote = remote_url or "<remote-url>"
    actions = []

    if has_remote:
        actions.append(
            command_record(
                "remote_present",
                "Confirm Git remote",
                "git remote -v",
                "done",
                "At least one remote is configured.",
            )
        )
    else:
        actions.append(
            command_record(
                "add_remote",
                "Configure Git remote",
                f"git remote add {remote_name} {concrete_remote}",
                "ready" if remote_url else "blocked",
                "Remote URL was provided." if remote_url else "No remote is configured; provide --remote-url or add one manually.",
            )
        )

    actions.append(
        command_record(
            "push_branch",
            "Push release branch",
            f"git push -u {remote_name} {branch}",
            "ready" if clean and (has_remote or remote_url) else "blocked",
            "Clean committed branch is ready to push." if clean else "Commit or intentionally exclude working tree changes first.",
        )
    )

    actions.append(
        command_record(
            "open_draft_pr",
            "Open draft pull request",
            f"gh pr create --draft --base {base_branch} --head {branch} --title \"{pr_title}\" --body-file <handoff-md>",
            "ready" if clean and (has_remote or remote_url) else "blocked",
            "Requires GitHub CLI authentication and pushed branch.",
        )
    )

    return actions


def write_markdown(handoff, markdown_path):
    lines = [
        "# RePERS Publish Handoff",
        "",
        f"- Generated: `{handoff['generated_at']}`",
        f"- Branch: `{handoff['git']['branch']}`",
        f"- Commit: `{handoff['git']['head_sha']}`",
        f"- Clean tree: `{not handoff['git']['dirty']}`",
        f"- Publish ready: `{handoff['publish_ready']}`",
        "",
        "## Remaining Blockers",
        "",
    ]
    if handoff["missing_for_publish"]:
        lines.extend(f"- {item}" for item in handoff["missing_for_publish"])
    else:
        lines.append("- None")
    lines.extend(["", "## Commands", ""])
    for action in handoff["actions"]:
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
    lines.extend(
        [
            "## Package",
            "",
            f"- Archive: `{handoff['package']['archive_path']}`",
            f"- SHA-256: `{handoff['package']['archive_sha256']}`",
            f"- Round trip: `{handoff['package']['roundtrip_ok']}`",
            "",
            "This handoff is intentionally non-destructive. It records the commands",
            "needed by a human or future agent, but it does not add remotes, push,",
            "or open pull requests.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def create_publish_handoff(
    workspace_root,
    install_root,
    output_dir="dist",
    remote_name="origin",
    remote_url=None,
    base_branch="main",
    pr_title=None,
    include_package=False,
    verify_roundtrip=False,
):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    evidence, evidence_path = build_release_evidence(
        workspace,
        install,
        output_dir=output,
        include_package=include_package,
        verify_roundtrip=verify_roundtrip,
    )
    title = pr_title or default_pr_title(workspace)
    actions = build_publish_actions(evidence, remote_name, remote_url, base_branch, title)
    gh_path = shutil.which("gh")
    handoff = {
        "schema": PUBLISH_HANDOFF_SCHEMA,
        "ok": evidence.get("schema") == "repers.release_evidence.v1",
        "release_evidence_ok": bool(evidence.get("ok")),
        "publish_ready": bool(evidence.get("publish_ready")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "release_evidence_path": str(Path(evidence_path).resolve()),
        "missing_for_publish": evidence.get("missing_for_publish", []),
        "remote": {
            "name": remote_name,
            "provided_url": remote_url,
            "records": remote_records(workspace),
        },
        "pull_request": {
            "base_branch": base_branch,
            "head_branch": evidence["git"].get("branch"),
            "title": title,
            "github_cli": {"available": bool(gh_path), "path": gh_path},
        },
        "git": evidence["git"],
        "package": evidence["package"],
        "actions": actions,
        "safety": {
            "executes_publish_commands": False,
            "mutates_git_remote": False,
            "pushes_branch": False,
            "opens_pull_request": False,
        },
    }
    json_path = output / "repers-publish-handoff.json"
    md_path = output / "repers-publish-handoff.md"
    handoff["path"] = str(json_path.resolve())
    handoff["markdown_path"] = str(md_path.resolve())
    json_path.write_text(json.dumps(handoff, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(handoff, md_path)
    return handoff, json_path, md_path

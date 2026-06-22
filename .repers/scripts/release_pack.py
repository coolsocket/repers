import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from open_source_benchmark import verify_open_source_benchmark, write_open_source_benchmark_report
from package_repers import create_package, sha256_file
from publish_handoff import create_publish_handoff
from release_evidence import build_release_evidence
from remote_bootstrap import create_remote_bootstrap
from state_report import build_state_report


RELEASE_PACK_SCHEMA = "repers.release_pack.v1"


def artifact_record(name, path, output_root):
    path = Path(path)
    exists = path.exists()
    record = {
        "name": name,
        "path": str(path.resolve()),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else 0,
        "sha256": sha256_file(path) if exists else None,
        "archive_path": path.name if exists else None,
    }
    try:
        record["relative_to_output"] = path.resolve().relative_to(output_root.resolve()).as_posix()
    except ValueError:
        record["relative_to_output"] = None
    return record


def write_release_pack_markdown(pack, markdown_path):
    lines = [
        "# RePERS Release Pack",
        "",
        f"- Generated: `{pack['generated_at']}`",
        f"- OK: `{pack['ok']}`",
        f"- Status: `{pack['status']}`",
        f"- Archive: `{pack['archive_path']}`",
        f"- Archive SHA-256: `{pack['archive_sha256']}`",
        f"- Artifact count: `{pack['artifact_count']}`",
        "",
        "## Next",
        "",
    ]
    if pack["next"].get("external_command"):
        lines.extend(
            [
                f"- External action: `{pack['next']['external_action_id']}`",
                "",
                "```powershell",
                pack["next"]["external_command"],
                "```",
                "",
            ]
        )
    else:
        lines.append("- None")
        lines.append("")
    lines.extend(["## Artifacts", ""])
    for artifact in pack["artifacts"]:
        lines.append(f"- `{artifact['name']}` -> `{artifact['archive_path']}`")
    lines.extend(
        [
            "",
            "This release pack is non-destructive. It does not add a remote, push a branch,",
            "or open a pull request. Use the publish handoff and remote bootstrap artifacts",
            "inside the archive for hosted publication.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def create_release_pack(
    workspace_root,
    install_root,
    output_dir="dist",
    remote_name="origin",
    remote_url=None,
    base_branch="main",
    pr_title=None,
):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    package = create_package(output, verify_roundtrip=True)
    release_evidence, release_evidence_path = build_release_evidence(
        workspace,
        install,
        output_dir=output,
        include_package=False,
        verify_roundtrip=False,
    )
    handoff, handoff_json_path, handoff_md_path = create_publish_handoff(
        workspace,
        install,
        output_dir=output,
        remote_name=remote_name,
        remote_url=remote_url,
        base_branch=base_branch,
        pr_title=pr_title,
        include_package=False,
        verify_roundtrip=False,
    )
    bootstrap, bootstrap_json_path, bootstrap_md_path = create_remote_bootstrap(
        workspace,
        install,
        output_dir=output,
        remote_name=remote_name,
        remote_url=remote_url,
        base_branch=base_branch,
        pr_title=pr_title,
        include_package=False,
        verify_roundtrip=False,
        apply=False,
    )
    benchmark = verify_open_source_benchmark(workspace, install)
    benchmark_json_path, benchmark_md_path = write_open_source_benchmark_report(benchmark, output)
    state, state_json_path, state_md_path = build_state_report(workspace, install, output_dir=output, deep=False)

    artifact_inputs = [
        ("package_archive", package.get("archive_path")),
        ("package_readiness", package.get("readiness_path")),
        ("release_evidence", release_evidence_path),
        ("publish_handoff_json", handoff_json_path),
        ("publish_handoff_markdown", handoff_md_path),
        ("remote_bootstrap_json", bootstrap_json_path),
        ("remote_bootstrap_markdown", bootstrap_md_path),
        ("open_source_benchmark_json", benchmark_json_path),
        ("open_source_benchmark_markdown", benchmark_md_path),
        ("objective_audit", state.get("artifacts", {}).get("objective_audit")),
        ("continuation_markdown", state.get("artifacts", {}).get("continuation_markdown")),
        ("state_json", state_json_path),
        ("state_markdown", state_md_path),
    ]
    artifacts = [artifact_record(name, path, output) for name, path in artifact_inputs if path]
    errors = []
    for artifact in artifacts:
        if not artifact["exists"]:
            errors.append(f"missing artifact: {artifact['name']}")

    local_ok = bool(
        package.get("ok")
        and release_evidence.get("ok")
        and handoff.get("ok")
        and bootstrap.get("ok")
        and benchmark.get("ok")
        and state.get("ok")
    )
    status = state.get("status") or ("complete" if state.get("objective", {}).get("complete") else "local_work_available")

    pack = {
        "schema": RELEASE_PACK_SCHEMA,
        "ok": bool(local_ok and not errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "status": status,
        "package": {
            "ok": package.get("ok"),
            "archive_path": package.get("archive_path"),
            "archive_sha256": package.get("archive_sha256"),
            "roundtrip_ok": package.get("roundtrip", {}).get("ok"),
        },
        "state": {
            "objective_complete": state.get("objective", {}).get("complete"),
            "blocking_incomplete": state.get("objective", {}).get("blocking_incomplete", []),
            "capability_count": state.get("capabilities", {}).get("entry_count"),
        },
        "next": state.get("next", {}),
        "publish_ready": bool(release_evidence.get("publish_ready")),
        "missing_for_publish": release_evidence.get("missing_for_publish", []),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "safety": {
            "executes_publish_commands": False,
            "mutates_git_remote": False,
            "pushes_branch": False,
            "opens_pull_request": False,
        },
        "errors": errors,
        "archive_path": None,
        "archive_sha256": None,
    }

    manifest_path = output / "repers-release-pack.json"
    markdown_path = output / "repers-release-pack.md"
    archive_path = output / "repers-release-pack.zip"
    pack["archive_path"] = str(archive_path.resolve())
    if archive_path.exists():
        archive_path.unlink()
    manifest_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    write_release_pack_markdown(pack, markdown_path)

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_path, manifest_path.name)
        zf.write(markdown_path, markdown_path.name)
        for artifact in artifacts:
            if artifact["exists"]:
                zf.write(artifact["path"], artifact["archive_path"])

    pack["archive_path"] = str(archive_path.resolve())
    pack["archive_sha256"] = sha256_file(archive_path)
    manifest_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    write_release_pack_markdown(pack, markdown_path)
    return pack, manifest_path, markdown_path, archive_path

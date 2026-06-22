import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from open_source_benchmark import verify_open_source_benchmark
from release_evidence import git_publish_state, missing_publish_requirements


OBJECTIVE_AUDIT_SCHEMA = "repers.objective_audit.v1"


DEFAULT_OBJECTIVE = (
    "Please continuously use all of the things you mentioned and build this one. "
    "Test it until all part is success. And search 10 popular open source code "
    "base to see the structure and how they promote. Build a self-autonomous one "
    "and keep building the solutions. You should build a whole repo that contains "
    "everything of the RePERS"
)


def command_result(name, command, cwd, env=None):
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, env=env)
    parsed = None
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "name": name,
        "command": command,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "json": parsed,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def file_record(root, rel):
    path = root / rel
    return {
        "path": rel,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def audit_requirement(requirement_id, title, passed, evidence, blocks_completion=True):
    status = "passed" if passed else "incomplete"
    return {
        "id": requirement_id,
        "title": title,
        "status": status,
        "passed": bool(passed),
        "blocks_completion": bool(blocks_completion),
        "evidence": evidence,
    }


def continuation_action(action_id, title, command, kind, status, reason):
    return {
        "id": action_id,
        "title": title,
        "command": command,
        "kind": kind,
        "status": status,
        "reason": reason,
    }


def load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_continuation(requirements, blocking_incomplete, handoff, bootstrap, missing_for_publish):
    local_actions = []
    external_actions = []
    blocked = set(blocking_incomplete)
    publish_local_blockers = [
        item
        for item in missing_for_publish
        if (
            "commit" in item
            or "package" in item
            or "round-trip" in item
            or "governance" in item
            or "registry" in item
        )
    ]

    if not blocking_incomplete:
        status = "complete"
    elif blocked == {"publication_ready"} and not publish_local_blockers:
        status = "blocked_external"
    else:
        status = "local_work_available"

    if any(item in blocked for item in ["tests_and_package_gates", "verified_without_chat_history"]):
        local_actions.append(
            continuation_action(
                "refresh_deep_evidence",
                "Regenerate deep objective evidence",
                "python -B .repers/scripts/repers.py objective-audit --deep --output dist --json",
                "local",
                "ready",
                "Deep audit regenerates package, receiver, handoff, remote bootstrap, fixture, and smoke evidence.",
            )
        )

    if "local_remote_bootstrap_apply" in blocked:
        local_actions.append(
            continuation_action(
                "prove_local_remote_apply",
                "Prove remote bootstrap apply path",
                "python -B .repers/scripts/repers.py remote-bootstrap-fixture --output dist --json",
                "local",
                "ready",
                "Runs the offline local bare-remote fixture.",
            )
        )

    if "local_publish_clone_verification" in blocked:
        local_actions.append(
            continuation_action(
                "prove_local_publish_clone",
                "Prove local publish and clone verification",
                "python -B .repers/scripts/repers.py publish-clone-fixture --output dist --json",
                "local",
                "ready",
                "Runs the offline local bare-remote publish, clone, and clone-side verification fixture.",
            )
        )

    if "one_command_source_install" in blocked:
        local_actions.append(
            continuation_action(
                "prove_one_command_source_install",
                "Prove one-command source install",
                "python -B .repers/scripts/repers.py source-install-fixture --output dist --json",
                "local",
                "ready",
                "Runs the fixture proving a source or cloned RePERS repo can install itself into a fresh receiver repository.",
            )
        )

    if "publication_ready" in blocked:
        if any("commit" in item for item in missing_for_publish):
            local_actions.append(
                continuation_action(
                    "commit_or_clean_worktree",
                    "Commit or intentionally exclude working tree changes",
                    "git status --short",
                    "local",
                    "ready",
                    "Publication readiness requires a clean committed branch before configuring or pushing a remote.",
                )
            )
        if any("package" in item or "round-trip" in item for item in missing_for_publish):
            local_actions.append(
                continuation_action(
                    "refresh_package_evidence",
                    "Refresh package and round-trip evidence",
                    "python -B .repers/scripts/repers.py bundle-status --package --verify-roundtrip --output dist --json",
                    "local",
                    "ready",
                    "Publication readiness requires ok package readiness and round-trip evidence.",
                )
            )
        if any("governance" in item or "registry" in item for item in missing_for_publish):
            local_actions.append(
                continuation_action(
                    "repair_release_surface",
                    "Repair governance or capability registry surface",
                    "python -B .repers/scripts/repers.py capabilities --action validate --json",
                    "local",
                    "ready",
                    "Publication readiness requires governance files and a valid capability registry.",
                )
            )
        remote_missing = any("remote" in item for item in missing_for_publish) or not missing_for_publish
        external_actions.append(
            continuation_action(
                "configure_hosted_remote",
                "Configure hosted Git remote",
                "python -B .repers/scripts/repers.py remote-bootstrap --remote-url <hosted-git-url> --apply --json",
                "external",
                "needs_remote_url" if remote_missing else "after_local_cleanup",
                "Requires a real hosted repository URL; local fixture already proves the apply and push mechanics.",
            )
        )
        external_actions.append(
            continuation_action(
                "push_branch",
                "Push committed branch",
                "git push -u origin <branch>",
                "external",
                "after_remote",
                "Requires the hosted remote to exist and be configured.",
            )
        )
        external_actions.append(
            continuation_action(
                "open_draft_pr",
                "Open draft pull request",
                "gh pr create --draft --base main --head <branch> --title \"Publish RePERS\" --body-file dist/repers-publish-handoff.md",
                "external",
                "after_push",
                "Requires GitHub CLI authentication or an equivalent provider API.",
            )
        )
        local_actions.append(
            continuation_action(
                "verify_after_publication_setup",
                "Re-run deep audit after remote setup",
                "python -B .repers/scripts/repers.py objective-audit --deep --output dist --json",
                "local",
                "after_remote",
                "Confirms clean tree, package gates, and publish readiness after the external remote is configured.",
            )
        )

    if not local_actions and not external_actions:
        local_actions.append(
            continuation_action(
                "verify_complete",
                "Verify objective completion",
                "python -B .repers/scripts/repers.py objective-audit --deep --output dist --json",
                "local",
                "ready",
                "No blockers are recorded; this command revalidates completion from current state.",
            )
        )

    requirement_status = {
        item["id"]: {
            "passed": item["passed"],
            "status": item["status"],
            "blocks_completion": item["blocks_completion"],
        }
        for item in requirements
    }
    handoff_actions = handoff.get("actions", []) if isinstance(handoff, dict) else []
    bootstrap_actions = bootstrap.get("actions", []) if isinstance(bootstrap, dict) else []
    return {
        "schema": "repers.objective_continuation.v1",
        "status": status,
        "blocking_incomplete": blocking_incomplete,
        "requirement_status": requirement_status,
        "local_actions": local_actions,
        "external_actions": external_actions,
        "handoff_action_ids": [action.get("id") for action in handoff_actions],
        "bootstrap_action_ids": [action.get("id") for action in bootstrap_actions],
    }


def write_continuation_markdown(audit, markdown_path):
    continuation = audit["continuation"]
    lines = [
        "# RePERS Continuation",
        "",
        f"- Generated: `{audit['generated_at']}`",
        f"- Status: `{continuation['status']}`",
        f"- Objective complete: `{audit['objective_complete']}`",
        "",
        "## Blocking Requirements",
        "",
    ]
    if continuation["blocking_incomplete"]:
        lines.extend(f"- `{item}`" for item in continuation["blocking_incomplete"])
    else:
        lines.append("- None")
    lines.extend(["", "## Local Actions", ""])
    for action in continuation["local_actions"]:
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
    lines.extend(["## External Actions", ""])
    if continuation["external_actions"]:
        for action in continuation["external_actions"]:
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
    else:
        lines.append("- None")
        lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def build_objective_audit(workspace_root, install_root, output_dir="dist", objective=None, deep=False):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    objective_text = objective or DEFAULT_OBJECTIVE

    commands = []
    if deep:
        repers = install / "scripts" / "repers.py"
        commands.append(
            command_result(
                "bundle_status_package_roundtrip",
                ["python", "-B", str(repers), "bundle-status", "--package", "--verify-roundtrip", "--output", str(output), "--json"],
                workspace,
            )
        )
        commands.append(
            command_result(
                "receiver_fixture",
                ["python", "-B", str(repers), "receiver-fixture", "--output", str(output), "--json"],
                workspace,
            )
        )
        commands.append(
            command_result(
                "publish_handoff",
                ["python", "-B", str(repers), "publish-handoff", "--package", "--verify-roundtrip", "--output", str(output), "--json"],
                workspace,
            )
        )
        commands.append(
            command_result(
                "remote_bootstrap",
                [
                    "python",
                    "-B",
                    str(repers),
                    "remote-bootstrap",
                    "--remote-url",
                    "https://example.invalid/repers.git",
                    "--package",
                    "--verify-roundtrip",
                    "--output",
                    str(output),
                    "--json",
                ],
                workspace,
            )
        )
        commands.append(
            command_result(
                "remote_bootstrap_fixture",
                ["python", "-B", str(repers), "remote-bootstrap-fixture", "--output", str(output), "--json"],
                workspace,
            )
        )
        commands.append(
            command_result(
                "publish_clone_fixture",
                ["python", "-B", str(repers), "publish-clone-fixture", "--output", str(output), "--json"],
                workspace,
            )
        )
        commands.append(
            command_result(
                "source_install_fixture",
                ["python", "-B", str(repers), "source-install-fixture", "--output", str(output), "--json"],
                workspace,
            )
        )
        commands.append(
            command_result(
                "smoke_tests",
                ["python", "-B", str(workspace / "tests" / "smoke_repers.py")],
                workspace,
                env={
                    **os.environ,
                    "REPERS_SMOKE_DIST": tempfile.mkdtemp(prefix="repers-objective-smoke-"),
                    "REPERS_INDEX_DB_PATH": str(Path(tempfile.mkdtemp(prefix="repers-objective-index-")) / "repers.db"),
                },
            )
        )

    readiness = load_json(output / "repers-0.1.0-readiness.json")
    release_evidence = load_json(output / "repers-release-evidence.json")
    publish_handoff = load_json(output / "repers-publish-handoff.json")
    remote_bootstrap = load_json(output / "repers-remote-bootstrap.json")
    remote_bootstrap_fixture = load_json(output / "repers-remote-bootstrap-fixture.json")
    publish_clone_fixture = load_json(output / "repers-publish-clone-fixture.json")
    source_install_fixture = load_json(output / "repers-source-install-fixture.json")
    registry = load_json(install / "capabilities" / "registry.json")
    manifest = load_json(install / "manifest.json")
    study_path = install / "docs" / "open-source-structure-study.md"
    benchmark = verify_open_source_benchmark(workspace, install)

    governance_files = [
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "SUPPORT.md",
        "ROADMAP.md",
        "CHANGELOG.md",
        "MAINTAINERS.md",
        ".github/workflows/repers-smoke.yml",
        "examples/basic-task/README.md",
    ]
    governance = [file_record(workspace, rel) for rel in governance_files]
    governance_ok = all(item["exists"] for item in governance)

    registry_entries = registry.get("entries", []) if isinstance(registry, dict) else []
    capability_ids = {entry.get("id") for entry in registry_entries if isinstance(entry, dict)}
    required_capabilities = {
        "preflight",
        "capability-registry",
        "orchestration-fixture",
        "package-readiness",
        "install-hook",
        "install-manifest-refresh",
        "open-source-benchmark",
        "task-dag",
        "review-release",
        "receiver-governance",
        "release-evidence",
        "release-pack",
        "receiver-fixture",
        "publish-handoff",
        "remote-bootstrap",
        "continuation-runner",
        "state-report",
        "snapshot-freshness",
        "verify-all",
        "publish-clone-fixture",
        "source-install-fixture",
    }

    command_map = {item["name"]: item for item in commands}
    bundle_status = command_map.get("bundle_status_package_roundtrip", {}).get("json")
    receiver_fixture = command_map.get("receiver_fixture", {}).get("json")
    publish_handoff_json = command_map.get("publish_handoff", {}).get("json", {})
    remote_bootstrap_json = command_map.get("remote_bootstrap", {}).get("json", {})
    remote_bootstrap_fixture_json = command_map.get("remote_bootstrap_fixture", {}).get("json", {})
    publish_clone_fixture_json = command_map.get("publish_clone_fixture", {}).get("json", {})
    source_install_fixture_json = command_map.get("source_install_fixture", {}).get("json", {})
    smoke = command_map.get("smoke_tests")

    package_ok = bool(readiness and readiness.get("ok") and not readiness.get("warnings"))
    if bundle_status:
        package_ok = package_ok and bool(bundle_status.get("ok") and bundle_status.get("package", {}).get("roundtrip", {}).get("ok"))

    receiver_ok = bool(receiver_fixture and receiver_fixture.get("ok")) if deep else Path(workspace / "dist" / "repers-0.1.0.zip").exists()
    handoff = publish_handoff_json.get("publish_handoff") if publish_handoff_json else publish_handoff
    bootstrap = remote_bootstrap_json.get("remote_bootstrap") if remote_bootstrap_json else remote_bootstrap
    bootstrap_fixture = (
        remote_bootstrap_fixture_json.get("remote_bootstrap_fixture")
        if remote_bootstrap_fixture_json
        else remote_bootstrap_fixture
    )
    clone_fixture = (
        publish_clone_fixture_json.get("publish_clone_fixture")
        if publish_clone_fixture_json
        else publish_clone_fixture
    )
    source_fixture = (
        source_install_fixture_json.get("source_install_fixture")
        if source_install_fixture_json
        else source_install_fixture
    )
    release = release_evidence or {}
    live_git = git_publish_state(workspace)
    git = live_git or (handoff.get("git", {}) if isinstance(handoff, dict) else release.get("git", {}))
    missing_for_publish = missing_publish_requirements(
        git,
        package_ok,
        None,
        False,
        governance_ok,
        required_capabilities <= capability_ids,
    )

    requirements = [
        audit_requirement(
            "self_contained_repository",
            "Repository contains installable RePERS runtime, docs, tests, examples, hooks, and governance.",
            governance_ok and bool(manifest and manifest.get("file_count", 0) >= 30),
            {
                "governance_files": governance,
                "manifest_file_count": manifest.get("file_count") if isinstance(manifest, dict) else None,
            },
        ),
        audit_requirement(
            "installable_by_another_repository",
            "Package can be installed into another Git repository and verified there.",
            receiver_ok,
            {
                "deep_check": bool(deep),
                "receiver_fixture_ok": receiver_fixture.get("ok") if isinstance(receiver_fixture, dict) else None,
                "archive_exists": Path(workspace / "dist" / "repers-0.1.0.zip").exists(),
            },
        ),
        audit_requirement(
            "agent_reusable_capabilities",
            "Reusable workflows are exposed through a machine-readable capability registry and preflight surface.",
            required_capabilities <= capability_ids,
            {
                "entry_count": len(registry_entries),
                "required": sorted(required_capabilities),
                "missing": sorted(required_capabilities - capability_ids),
            },
        ),
        audit_requirement(
            "deterministic_orchestration",
            "Large-task DAG orchestration has deterministic worker dispatch, review, and fixture proof.",
            "orchestration-fixture" in capability_ids and bool(Path(install / "scripts" / "orchestration_fixture.py").exists()),
            {
                "capability_present": "orchestration-fixture" in capability_ids,
                "script": file_record(install, "scripts/orchestration_fixture.py"),
            },
        ),
        audit_requirement(
            "open_source_structure_research",
            "Repository includes and verifies the 10-repository open-source structure and promotion benchmark.",
            benchmark.get("ok") is True,
            {
                "path": str(study_path),
                "benchmark_path": benchmark.get("benchmark_path"),
                "repository_count": benchmark.get("repository_count"),
                "source_urls": benchmark.get("source_url_count"),
                "pattern_count": benchmark.get("pattern_count"),
                "missing_source_paths": benchmark.get("missing_source_paths"),
                "missing_installed_paths": benchmark.get("missing_installed_paths"),
                "errors": benchmark.get("errors"),
            },
        ),
        audit_requirement(
            "tests_and_package_gates",
            "Smoke tests and package round-trip gates pass.",
            package_ok and (not deep or bool(smoke and smoke.get("ok"))),
            {
                "deep_check": bool(deep),
                "tracked_readiness_ok": readiness.get("ok") if isinstance(readiness, dict) else None,
                "tracked_readiness_warnings": readiness.get("warnings") if isinstance(readiness, dict) else None,
                "bundle_status_ok": bundle_status.get("ok") if isinstance(bundle_status, dict) else None,
                "smoke_ok": smoke.get("ok") if isinstance(smoke, dict) else None,
            },
        ),
        audit_requirement(
            "verified_without_chat_history",
            "Repo carries machine-readable release, package, receiver, publish handoff, remote bootstrap, and continuation evidence.",
            bool(readiness and release_evidence and publish_handoff and remote_bootstrap and publish_clone_fixture and source_install_fixture),
            {
                "readiness": file_record(output, "repers-0.1.0-readiness.json"),
                "release_evidence": file_record(output, "repers-release-evidence.json"),
                "publish_handoff": file_record(output, "repers-publish-handoff.json"),
                "publish_handoff_markdown": file_record(output, "repers-publish-handoff.md"),
                "remote_bootstrap": file_record(output, "repers-remote-bootstrap.json"),
                "remote_bootstrap_markdown": file_record(output, "repers-remote-bootstrap.md"),
                "publish_clone_fixture": file_record(output, "repers-publish-clone-fixture.json"),
                "source_install_fixture": file_record(output, "repers-source-install-fixture.json"),
                "continuation_markdown": file_record(output, "repers-continuation.md"),
                "remote_bootstrap_ok": bootstrap.get("ok") if isinstance(bootstrap, dict) else None,
            },
        ),
        audit_requirement(
            "local_remote_bootstrap_apply",
            "Remote bootstrap apply path is proven against a temporary local bare remote.",
            bool(bootstrap_fixture and bootstrap_fixture.get("ok")),
            {
                "deep_check": bool(deep),
                "fixture": file_record(output, "repers-remote-bootstrap-fixture.json"),
                "fixture_ok": bootstrap_fixture.get("ok") if isinstance(bootstrap_fixture, dict) else None,
                "local_push_ok": (
                    bootstrap_fixture.get("checks", {}).get("local_push", {}).get("ok")
                    if isinstance(bootstrap_fixture, dict)
                    else None
                ),
            },
        ),
        audit_requirement(
            "local_publish_clone_verification",
            "Repository publication is proven through a local bare remote, clone, and clone-side RePERS verification.",
            bool(clone_fixture and clone_fixture.get("ok")),
            {
                "deep_check": bool(deep),
                "fixture": file_record(output, "repers-publish-clone-fixture.json"),
                "fixture_ok": clone_fixture.get("ok") if isinstance(clone_fixture, dict) else None,
                "verify_install_ok": (
                    clone_fixture.get("checks", {}).get("verify_install", {}).get("json", {}).get("ok")
                    if isinstance(clone_fixture, dict)
                    else None
                ),
                "state_ok": (
                    clone_fixture.get("checks", {}).get("state", {}).get("json", {}).get("state", {}).get("ok")
                    if isinstance(clone_fixture, dict)
                    else None
                ),
            },
        ),
        audit_requirement(
            "one_command_source_install",
            "A source or cloned RePERS repository can install itself into a fresh receiver with one CLI command.",
            bool(source_fixture and source_fixture.get("ok")),
            {
                "deep_check": bool(deep),
                "fixture": file_record(output, "repers-source-install-fixture.json"),
                "fixture_ok": source_fixture.get("ok") if isinstance(source_fixture, dict) else None,
                "install_command_ok": (
                    source_fixture.get("checks", {}).get("source_install", {}).get("json", {}).get("ok")
                    if isinstance(source_fixture, dict)
                    else None
                ),
                "verify_install_ok": (
                    source_fixture.get("checks", {}).get("verify_install", {}).get("json", {}).get("ok")
                    if isinstance(source_fixture, dict)
                    else None
                ),
            },
        ),
        audit_requirement(
            "publication_ready",
            "Repo can be pushed and opened as a draft PR.",
            bool(git.get("has_head") and not git.get("dirty") and git.get("remote_count", 0) > 0),
            {
                "git": git,
                "missing_for_publish": missing_for_publish,
            },
        ),
    ]

    blocking_incomplete = [item["id"] for item in requirements if item["blocks_completion"] and not item["passed"]]
    continuation = build_continuation(requirements, blocking_incomplete, handoff, bootstrap, missing_for_publish)
    audit = {
        "schema": OBJECTIVE_AUDIT_SCHEMA,
        "ok": True,
        "objective_complete": not blocking_incomplete,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "output_dir": str(output),
        "objective": objective_text,
        "deep": bool(deep),
        "requirements": requirements,
        "blocking_incomplete": blocking_incomplete,
        "continuation": continuation,
        "commands": commands,
    }
    output_path = output / "repers-objective-audit.json"
    continuation_path = output / "repers-continuation.md"
    audit["continuation_markdown_path"] = str(continuation_path.resolve())
    write_continuation_markdown(audit, continuation_path)
    for requirement in audit["requirements"]:
        if requirement["id"] == "verified_without_chat_history":
            continuation_record = file_record(output, "repers-continuation.md")
            requirement["evidence"]["continuation_markdown"] = continuation_record
            requirement["passed"] = bool(requirement["passed"] and continuation_record["exists"])
            requirement["status"] = "passed" if requirement["passed"] else "incomplete"
    audit["blocking_incomplete"] = [
        item["id"] for item in audit["requirements"] if item["blocks_completion"] and not item["passed"]
    ]
    audit["objective_complete"] = not audit["blocking_incomplete"]
    output_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit, output_path

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


OBJECTIVE_AUDIT_SCHEMA = "repers.objective_audit.v1"


DEFAULT_OBJECTIVE = (
    "Please continuously use all of the things you mentioned and build this one. "
    "Test it until all part is success. And search 10 popular open source code "
    "base to see the structure and how they promote. Build a self-autonomous one "
    "and keep building the solutions. You should build a whole repo that contains "
    "everything of the RePERS"
)


def command_result(name, command, cwd):
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
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


def count_open_source_repositories(study_text):
    count = 0
    source_count = 0
    for line in study_text.splitlines():
        if line.startswith("| `") and "` |" in line:
            count += 1
        if line.startswith("- https://api.github.com/repos/"):
            source_count += 1
    return count, source_count


def load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


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
                ["python", "-B", str(repers), "receiver-fixture", "--json"],
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
                "smoke_tests",
                ["python", "-B", str(workspace / "tests" / "smoke_repers.py")],
                workspace,
            )
        )

    readiness = load_json(output / "repers-0.1.0-readiness.json")
    release_evidence = load_json(output / "repers-release-evidence.json")
    publish_handoff = load_json(output / "repers-publish-handoff.json")
    registry = load_json(install / "capabilities" / "registry.json")
    manifest = load_json(install / "manifest.json")
    study_path = install / "docs" / "open-source-structure-study.md"
    study_text = study_path.read_text(encoding="utf-8") if study_path.exists() else ""
    repo_count, source_count = count_open_source_repositories(study_text)

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
        "task-dag",
        "review-release",
        "receiver-governance",
        "release-evidence",
        "receiver-fixture",
        "publish-handoff",
    }

    command_map = {item["name"]: item for item in commands}
    bundle_status = command_map.get("bundle_status_package_roundtrip", {}).get("json")
    receiver_fixture = command_map.get("receiver_fixture", {}).get("json")
    publish_handoff_json = command_map.get("publish_handoff", {}).get("json", {})
    smoke = command_map.get("smoke_tests")

    package_ok = bool(readiness and readiness.get("ok") and not readiness.get("warnings"))
    if bundle_status:
        package_ok = package_ok and bool(bundle_status.get("ok") and bundle_status.get("package", {}).get("roundtrip", {}).get("ok"))

    receiver_ok = bool(receiver_fixture and receiver_fixture.get("ok")) if deep else Path(workspace / "dist" / "repers-0.1.0.zip").exists()
    handoff = publish_handoff_json.get("publish_handoff") if publish_handoff_json else publish_handoff
    release = release_evidence or {}
    git = handoff.get("git", {}) if isinstance(handoff, dict) else release.get("git", {})
    missing_for_publish = handoff.get("missing_for_publish", []) if isinstance(handoff, dict) else release.get("missing_for_publish", [])

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
            "Repository includes the 10-repository open-source structure and promotion study.",
            repo_count >= 10 and source_count >= 10,
            {
                "path": str(study_path),
                "repo_rows": repo_count,
                "source_urls": source_count,
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
            "Repo carries machine-readable release, package, receiver, and publish handoff evidence.",
            bool(readiness and release_evidence and publish_handoff),
            {
                "readiness": file_record(output, "repers-0.1.0-readiness.json"),
                "release_evidence": file_record(output, "repers-release-evidence.json"),
                "publish_handoff": file_record(output, "repers-publish-handoff.json"),
                "publish_handoff_markdown": file_record(output, "repers-publish-handoff.md"),
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
        "commands": commands,
    }
    output_path = output / "repers-objective-audit.json"
    output_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit, output_path

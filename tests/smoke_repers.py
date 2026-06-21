import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPERS = ROOT / ".repers" / "scripts" / "repers.py"
DIST = Path(os.environ.get("REPERS_SMOKE_DIST", ROOT / "dist"))


def run(cmd):
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"command failed: {cmd}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result.stdout


def run_allow_failure(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def test_json_preflight_with_codegraph_fallback():
    stdout = run(
        [
            sys.executable,
            str(REPERS),
            "preflight",
            "--query",
            "DAG preflight",
            "--json",
            "--codegraph",
            "--codegraph-bin",
            str(ROOT / "missing-codegraph"),
        ]
    )
    artifact = json.loads(stdout)
    assert artifact["query"] == "DAG preflight"
    assert artifact["recommendation"]["decision"] in {"reuse", "extend", "create"}
    assert artifact["code_evidence"]["provider"] == "codegraph"
    assert artifact["code_evidence"]["enabled"] is True
    assert artifact["code_evidence"]["available"] is False
    assert artifact["code_evidence"]["ok"] is False
    assert artifact["code_evidence"]["errors"]


def test_preflight_help_exposes_codegraph_flags():
    stdout = run([sys.executable, str(REPERS), "preflight", "--help"])
    assert "--codegraph" in stdout
    assert "--codegraph-init" in stdout
    assert "--no-codegraph-sync" in stdout


def test_audit_warning_policy():
    warn = run_allow_failure([sys.executable, str(REPERS), "audit"])
    assert warn.returncode == 0
    strict = run_allow_failure([sys.executable, str(REPERS), "audit", "--strict-warnings"])
    assert strict.returncode == 1

    hook_repo = ROOT / ".repers-smoke-hook-repo"
    if hook_repo.exists():
        shutil.rmtree(hook_repo)
    try:
        hook_repo.mkdir()
        git_init = subprocess.run(["git", "init"], cwd=hook_repo, capture_output=True, text=True)
        if git_init.returncode != 0:
            raise AssertionError(f"git init failed\nstdout:\n{git_init.stdout}\nstderr:\n{git_init.stderr}")
        shutil.copytree(
            ROOT / ".repers",
            hook_repo / ".repers",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "index"),
        )
        hook_repers = hook_repo / ".repers" / "scripts" / "repers.py"
        install = subprocess.run(
            [sys.executable, str(hook_repers), "install-hook", "--hook-policy", "warn", "--json"],
            cwd=hook_repo,
            capture_output=True,
            text=True,
        )
        if install.returncode != 0:
            raise AssertionError(f"install-hook failed\nstdout:\n{install.stdout}\nstderr:\n{install.stderr}")
        installed = json.loads(install.stdout)
        assert installed["hook_policy"] == "warn"
        assert (hook_repo / ".git" / "hooks" / "pre-commit").exists()
    finally:
        if hook_repo.exists():
            shutil.rmtree(hook_repo)


def test_install_manifest_verification():
    stdout = run([sys.executable, str(REPERS), "verify-install", "--json"])
    verify = json.loads(stdout)
    assert verify["schema"] == "repers.install_verify.v1"
    assert verify["ok"] is True
    assert verify["checked_count"] == verify["file_count"]


def test_package_archive_manifest():
    stdout = run([sys.executable, str(REPERS), "package", "--output", str(DIST), "--json"])
    package = json.loads(stdout)
    assert package["schema"] == "repers.package.v1"
    assert package["ok"] is True
    archive_path = Path(package["archive_path"])
    assert archive_path.exists()
    assert package["archive_size_bytes"] == archive_path.stat().st_size
    assert len(package["archive_sha256"]) == 64
    readiness_path = Path(package["readiness_path"])
    assert readiness_path.exists()
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    assert readiness["schema"] == "repers.package_readiness.v1"
    assert readiness["ok"] is True
    assert readiness["archive_sha256"] == package["archive_sha256"]
    assert readiness["surface"]["has_cli"] is True
    assert readiness["surface"]["has_install_script"] is True
    assert readiness["surface"]["has_templates"] is True
    assert readiness["surface"]["has_top_level_readme"] is True
    assert readiness["surface"]["has_changelog"] is True
    assert readiness["surface"]["has_contributing"] is True
    assert readiness["surface"]["has_maintainers"] is True
    assert readiness["surface"]["has_roadmap"] is True
    assert readiness["surface"]["has_security"] is True
    assert readiness["surface"]["has_support"] is True
    assert readiness["surface"]["has_ci"] is True
    assert readiness["surface"]["has_capability_registry"] is True
    assert readiness["surface"]["has_examples"] is True
    assert readiness["surface"]["has_tests"] is True
    assert readiness["warnings"] == []
    assert "install" in readiness["receiver_commands"]
    assert "verify" in readiness["receiver_commands"]
    assert "capabilities" in readiness["receiver_commands"]
    assert "fixture_prove" in readiness["receiver_commands"]
    assert "receiver_fixture" in readiness["receiver_commands"]
    assert "publish_handoff" in readiness["receiver_commands"]
    assert "remote_bootstrap" in readiness["receiver_commands"]
    assert "remote_bootstrap_fixture" in readiness["receiver_commands"]
    assert "objective_audit" in readiness["receiver_commands"]
    assert "continue" in readiness["receiver_commands"]

    archive_root = package["manifest"]["archive_root"]
    manifest_path = f"{archive_root}/repers-package-manifest.json"
    readiness_archive_path = f"{archive_root}/repers-package-readiness.json"
    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
        assert manifest_path in names
        assert readiness_archive_path in names
        manifest = json.loads(zf.read(manifest_path).decode("utf-8"))
        assert manifest["schema"] == "repers.package_manifest.v1"
        assert manifest["file_count"] == len(manifest["files"])
        embedded_readiness = json.loads(zf.read(readiness_archive_path).decode("utf-8"))
        assert embedded_readiness["schema"] == "repers.package_readiness.v1"
        assert embedded_readiness["archive_sha256"] is None
        assert embedded_readiness["archive_sha256_scope"] == "external_package_output"
        assert f"{archive_root}/scripts/repers.py" in names
        assert f"{archive_root}/scripts/install_repers.py" in names
        assert f"{archive_root}/scripts/capability_registry.py" in names
        assert f"{archive_root}/scripts/orchestration_fixture.py" in names
        assert f"{archive_root}/scripts/receiver_fixture.py" in names
        assert f"{archive_root}/scripts/release_evidence.py" in names
        assert f"{archive_root}/scripts/publish_handoff.py" in names
        assert f"{archive_root}/scripts/remote_bootstrap.py" in names
        assert f"{archive_root}/scripts/objective_audit.py" in names
        assert f"{archive_root}/scripts/continuation_runner.py" in names
        assert f"{archive_root}/capabilities/registry.json" in names
        assert f"{archive_root}/templates/plan.md" in names
        assert f"{archive_root}/hooks/pre-commit" in names
        assert f"{archive_root}/README.md" in names
        assert f"{archive_root}/docs/planning/active-repers-build.md" in names
        assert f"{archive_root}/CHANGELOG.md" in names
        assert f"{archive_root}/CONTRIBUTING.md" in names
        assert f"{archive_root}/MAINTAINERS.md" in names
        assert f"{archive_root}/ROADMAP.md" in names
        assert f"{archive_root}/SECURITY.md" in names
        assert f"{archive_root}/SUPPORT.md" in names
        assert f"{archive_root}/.github/workflows/repers-smoke.yml" in names
        assert f"{archive_root}/examples/basic-task/README.md" in names
        assert f"{archive_root}/tests/smoke_repers.py" in names
        assert not any(".repers/" in name for name in names)
        assert not any("repers_tasks/" in name for name in names)


def test_package_roundtrip_install_from_archive():
    stdout = run([sys.executable, str(REPERS), "package", "--output", str(DIST), "--json"])
    package = json.loads(stdout)
    archive_path = Path(package["archive_path"])
    archive_root = package["manifest"]["archive_root"]
    roundtrip_root = ROOT / ".repers-smoke-roundtrip"
    if roundtrip_root.exists():
        shutil.rmtree(roundtrip_root)
    try:
        extract_root = roundtrip_root / "extract"
        target_repo = roundtrip_root / "target"
        extract_root.mkdir(parents=True)
        target_repo.mkdir(parents=True)
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(extract_root)
        git_init = subprocess.run(["git", "init"], cwd=target_repo, capture_output=True, text=True)
        if git_init.returncode != 0:
            raise AssertionError(f"git init failed\nstdout:\n{git_init.stdout}\nstderr:\n{git_init.stderr}")

        installer = extract_root / archive_root / "scripts" / "install_repers.py"
        install = subprocess.run(
            [sys.executable, str(installer), "--target", str(target_repo), "--no-hook"],
            cwd=extract_root / archive_root,
            capture_output=True,
            text=True,
        )
        if install.returncode != 0:
            raise AssertionError(f"archive install failed\nstdout:\n{install.stdout}\nstderr:\n{install.stderr}")

        verify = subprocess.run(
            [sys.executable, str(target_repo / ".repers" / "scripts" / "repers.py"), "verify-install", "--json"],
            cwd=target_repo,
            capture_output=True,
            text=True,
        )
        if verify.returncode != 0:
            raise AssertionError(f"roundtrip verify failed\nstdout:\n{verify.stdout}\nstderr:\n{verify.stderr}")
        verify_json = json.loads(verify.stdout)
        assert verify_json["schema"] == "repers.install_verify.v1"
        assert verify_json["ok"] is True
        assert verify_json["checked_count"] == verify_json["file_count"]
    finally:
        if roundtrip_root.exists():
            shutil.rmtree(roundtrip_root)


def test_package_verify_roundtrip_flag():
    stdout = run([sys.executable, str(REPERS), "package", "--output", str(DIST), "--verify-roundtrip", "--json"])
    package = json.loads(stdout)
    assert package["schema"] == "repers.package.v1"
    assert package["ok"] is True
    assert package["roundtrip"]["schema"] == "repers.package_roundtrip.v1"
    assert package["roundtrip"]["ok"] is True
    assert package["roundtrip"]["errors"] == []
    assert package["roundtrip"]["verify"]["schema"] == "repers.install_verify.v1"
    assert package["roundtrip"]["verify"]["ok"] is True
    step_names = {step["name"] for step in package["roundtrip"]["steps"]}
    assert {"extract", "git_init", "install", "verify_install"} <= step_names


def test_bundle_status_json():
    stdout = run([sys.executable, str(REPERS), "bundle-status", "--json"])
    status = json.loads(stdout)
    assert status["schema"] == "repers.bundle_status.v1"
    assert status["ok"] is True
    assert status["verify_install"]["schema"] == "repers.install_verify.v1"
    assert status["verify_install"]["ok"] is True
    assert status["doctor"]["ok"] is True
    assert status["package"] is None
    assert status["errors"] == []


def test_bundle_status_with_package_roundtrip():
    stdout = run(
        [
            sys.executable,
            str(REPERS),
            "bundle-status",
            "--package",
            "--verify-roundtrip",
            "--output",
            str(DIST),
            "--json",
        ]
    )
    status = json.loads(stdout)
    assert status["schema"] == "repers.bundle_status.v1"
    assert status["ok"] is True
    assert status["verify_install"]["ok"] is True
    assert status["doctor"]["ok"] is True
    assert status["package"]["ok"] is True
    assert status["package"]["roundtrip"]["ok"] is True
    assert status["package"]["readiness"]["warnings"] == []
    assert status["errors"] == []


def test_orchestration_fixture_proves_worker_command_dag():
    task_dir = ROOT / "repers_tasks" / "smoke_large_task"
    if task_dir.exists():
        shutil.rmtree(task_dir)
    try:
        stdout = run(
            [
                sys.executable,
                str(REPERS),
                "fixture",
                "--action",
                "prove",
                "--task",
                "smoke-large-task",
                "--max-workers",
                "3",
                "--json",
            ]
        )
        fixture = json.loads(stdout)
        assert fixture["schema"] == "repers.orchestration_fixture.v1"
        assert fixture["ok"] is True
        assert fixture["initial_dry_run"]["ready_count"] == 3
        assert fixture["dispatch"]["schema"] == "repers.dispatch.v1"
        assert fixture["dispatch"]["ready_count"] == 3
        assert fixture["dispatch"]["batch_count"] == 2
        assert len(fixture["dispatch"]["workers"]) == 3
        for batch in fixture["dispatch"]["batches"]:
            step_ids = {
                str(worker["step_id"])
                for worker in fixture["dispatch"]["workers"]
                if worker["worker_id"] in set(batch["workers"])
            }
            assert not {"1", "2"} <= step_ids
        assert sorted(fixture["worker_run"]["completed"]) == ["1", "2", "3"]
        assert fixture["worker_run"]["failed"] == []
        assert fixture["join_dry_run"]["ready_count"] == 1
        assert fixture["local_run"]["completed"] == ["4"]
        assert fixture["local_run"]["failed"] == []
        assert fixture["join"]["fixture_ok"] is True
        assert fixture["review"]["ok"] is True
    finally:
        if task_dir.exists():
            shutil.rmtree(task_dir)


def test_capability_registry_and_preflight_surface():
    validate_stdout = run([sys.executable, str(REPERS), "capabilities", "--action", "validate", "--json"])
    validation = json.loads(validate_stdout)
    assert validation["schema"] == "repers.capability_registry_validation.v1"
    assert validation["ok"] is True
    assert validation["entry_count"] >= 8

    search_stdout = run(
        [
            sys.executable,
            str(REPERS),
            "capabilities",
            "--action",
            "search",
            "--query",
            "fixture worker-command parallel dag",
            "--json",
        ]
    )
    search = json.loads(search_stdout)
    assert search["schema"] == "repers.capability_query.v1"
    assert search["ok"] is True
    assert search["entries"]
    assert search["entries"][0]["id"] == "orchestration-fixture"

    continuation_stdout = run(
        [
            sys.executable,
            str(REPERS),
            "capabilities",
            "--action",
            "search",
            "--query",
            "autonomous continuation resume local actions",
            "--json",
        ]
    )
    continuation_search = json.loads(continuation_stdout)
    assert continuation_search["ok"] is True
    assert continuation_search["entries"][0]["id"] == "continuation-runner"

    preflight_stdout = run(
        [
            sys.executable,
            str(REPERS),
            "preflight",
            "--query",
            "fixture worker-command parallel dag",
            "--refresh",
            "--json",
        ]
    )
    preflight = json.loads(preflight_stdout)
    assert preflight["counts"]["capability_hits"] >= 1
    assert any(result["source"] == "local_capability" for result in preflight["results"])


def test_release_evidence_publish_readiness_artifact():
    stdout = run(
        [
            sys.executable,
            str(REPERS),
            "release-evidence",
            "--output",
            str(DIST),
            "--package",
            "--verify-roundtrip",
            "--json",
        ]
    )
    result = json.loads(stdout)
    evidence = result["release_evidence"]
    evidence_path = Path(result["path"])
    assert evidence_path.exists()
    assert evidence["schema"] == "repers.release_evidence.v1"
    assert evidence["ok"] is True
    assert isinstance(evidence["publish_ready"], bool)
    assert evidence["package"]["ok"] is True
    assert evidence["package"]["roundtrip_ok"] is True
    assert evidence["governance"]["ok"] is True
    assert evidence["capability_registry"]["validation"]["ok"] is True
    assert "git" in evidence
    if not evidence["publish_ready"]:
        assert evidence["missing_for_publish"]
    written = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert written["schema"] == "repers.release_evidence.v1"


def test_publish_handoff_artifact_is_non_destructive():
    output_dir = ROOT / ".repers-smoke-publish-handoff"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        stdout = run(
            [
                sys.executable,
                str(REPERS),
                "publish-handoff",
                "--output",
                str(output_dir),
                "--remote-url",
                "https://example.invalid/repo.git",
                "--base-branch",
                "main",
                "--pr-title",
                "RePERS smoke handoff",
                "--json",
            ]
        )
        result = json.loads(stdout)
        handoff = result["publish_handoff"]
        handoff_path = Path(result["path"])
        markdown_path = Path(result["markdown_path"])
        assert handoff_path.exists()
        assert markdown_path.exists()
        assert handoff["schema"] == "repers.publish_handoff.v1"
        assert handoff["ok"] is True
        assert handoff["remote"]["provided_url"] == "https://example.invalid/repo.git"
        assert handoff["pull_request"]["base_branch"] == "main"
        assert handoff["safety"]["executes_publish_commands"] is False
        assert handoff["safety"]["mutates_git_remote"] is False
        assert handoff["safety"]["pushes_branch"] is False
        assert handoff["safety"]["opens_pull_request"] is False
        action_ids = {action["id"] for action in handoff["actions"]}
        assert {"push_branch", "open_draft_pr"} <= action_ids
        written = json.loads(handoff_path.read_text(encoding="utf-8"))
        assert written["schema"] == "repers.publish_handoff.v1"
        assert "gh pr create --draft" in markdown_path.read_text(encoding="utf-8")
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_remote_bootstrap_artifact_is_non_destructive():
    output_dir = ROOT / ".repers-smoke-remote-bootstrap"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    before = subprocess.run(["git", "remote", "-v"], cwd=ROOT, capture_output=True, text=True)
    try:
        stdout = run(
            [
                sys.executable,
                str(REPERS),
                "remote-bootstrap",
                "--output",
                str(output_dir),
                "--remote-url",
                "https://example.invalid/repo.git",
                "--base-branch",
                "main",
                "--pr-title",
                "RePERS smoke bootstrap",
                "--json",
            ]
        )
        after = subprocess.run(["git", "remote", "-v"], cwd=ROOT, capture_output=True, text=True)
        assert before.stdout == after.stdout
        result = json.loads(stdout)
        bootstrap = result["remote_bootstrap"]
        bootstrap_path = Path(result["path"])
        markdown_path = Path(result["markdown_path"])
        assert bootstrap_path.exists()
        assert markdown_path.exists()
        assert bootstrap["schema"] == "repers.remote_bootstrap.v1"
        assert bootstrap["ok"] is True
        assert bootstrap["remote"]["provided_url"] == "https://example.invalid/repo.git"
        assert bootstrap["applied"]["requested"] is False
        assert bootstrap["applied"]["changed"] is False
        assert bootstrap["safety"]["mutates_git_remote_by_default"] is False
        assert bootstrap["safety"]["mutates_git_remote"] is False
        assert bootstrap["safety"]["executes_push"] is False
        assert bootstrap["safety"]["opens_pull_request"] is False
        assert bootstrap["publish_handoff"]["ok"] is True
        action_ids = {action["id"] for action in bootstrap["actions"]}
        assert {"add_remote", "publish_handoff", "push_branch", "open_draft_pr"} <= action_ids
        written = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert written["schema"] == "repers.remote_bootstrap.v1"
        markdown = markdown_path.read_text(encoding="utf-8")
        assert "git remote add origin https://example.invalid/repo.git" in markdown
        assert "gh pr create --draft" in markdown
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_remote_bootstrap_fixture_proves_apply_path():
    output_dir = ROOT / ".repers-smoke-remote-bootstrap-fixture"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        stdout = run(
            [
                sys.executable,
                str(REPERS),
                "remote-bootstrap-fixture",
                "--output",
                str(output_dir),
                "--json",
            ]
        )
        result = json.loads(stdout)
        fixture = result["remote_bootstrap_fixture"]
        fixture_path = Path(result["path"])
        assert fixture_path.exists()
        assert fixture["schema"] == "repers.remote_bootstrap_apply_fixture.v1"
        assert fixture["ok"] is True
        assert fixture["errors"] == []
        assert fixture["checks"]["remote_bootstrap_apply"]["json"]["remote_bootstrap"]["applied"]["changed"] is True
        assert fixture["checks"]["remote_bootstrap_apply"]["json"]["remote_bootstrap"]["safety"]["mutates_git_remote"] is True
        assert fixture["checks"]["remote_bootstrap_apply"]["json"]["remote_bootstrap"]["git"]["dirty"] is False
        action_by_id = {
            action["id"]: action
            for action in fixture["checks"]["remote_bootstrap_apply"]["json"]["remote_bootstrap"]["actions"]
        }
        assert action_by_id["push_branch"]["status"] == "ready"
        assert fixture["checks"]["remote_url"]["ok"] is True
        assert fixture["checks"]["local_push"]["ok"] is True
        assert fixture["checks"]["bare_remote_refs"]["ok"] is True
        written = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert written["schema"] == "repers.remote_bootstrap_apply_fixture.v1"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_objective_audit_reports_requirements_and_blockers():
    output_dir = ROOT / ".repers-smoke-objective-audit"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        stdout = run(
            [
                sys.executable,
                str(REPERS),
                "objective-audit",
                "--output",
                str(output_dir),
                "--json",
            ]
        )
        result = json.loads(stdout)
        audit = result["objective_audit"]
        audit_path = Path(result["path"])
        assert audit_path.exists()
        assert audit["schema"] == "repers.objective_audit.v1"
        assert audit["ok"] is True
        assert isinstance(audit["objective_complete"], bool)
        requirement_ids = {item["id"] for item in audit["requirements"]}
        assert {
            "self_contained_repository",
            "installable_by_another_repository",
            "agent_reusable_capabilities",
            "deterministic_orchestration",
            "open_source_structure_research",
            "tests_and_package_gates",
            "verified_without_chat_history",
            "local_remote_bootstrap_apply",
            "publication_ready",
        } <= requirement_ids
        assert any(item["id"] == "publication_ready" for item in audit["requirements"])
        assert audit["continuation"]["schema"] == "repers.objective_continuation.v1"
        assert audit["continuation"]["status"] in {"blocked_external", "local_work_available", "complete"}
        assert audit["continuation"]["local_actions"]
        assert "publication_ready" in audit["continuation"]["requirement_status"]
        continuation_path = Path(audit["continuation_markdown_path"])
        assert continuation_path.exists()
        assert "RePERS Continuation" in continuation_path.read_text(encoding="utf-8")
        written = json.loads(audit_path.read_text(encoding="utf-8"))
        assert written["schema"] == "repers.objective_audit.v1"
        assert written["continuation"]["schema"] == "repers.objective_continuation.v1"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_continue_reports_resume_actions_without_applying_by_default():
    output_dir = ROOT / ".repers-smoke-continue"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        stdout = run(
            [
                sys.executable,
                str(REPERS),
                "continue",
                "--output",
                str(output_dir),
                "--json",
            ]
        )
        result = json.loads(stdout)
        assert result["schema"] == "repers.continuation_run.v1"
        assert result["ok"] is True
        assert result["mode"] == "dry-run"
        assert Path(result["audit_path"]).exists()
        assert isinstance(result["objective_complete"], bool)
        assert isinstance(result["blocking_incomplete"], list)
        assert result["local_actions"]
        assert "verify_after_publication_setup" in result["selected_action_ids"]
        assert result["external_actions"]
        assert "configure_hosted_remote" in result["external_action_ids"]
        assert result["executions"] == []
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_receiver_fixture_proves_installed_package_commands():
    stdout = run([sys.executable, str(REPERS), "receiver-fixture", "--output", str(DIST), "--json"])
    fixture = json.loads(stdout)
    assert fixture["schema"] == "repers.receiver_fixture.v1"
    assert fixture["ok"] is True
    assert fixture["package"]["ok"] is True
    assert fixture["checks"]["verify_install"]["json"]["ok"] is True
    assert fixture["checks"]["doctor"]["json"]["ok"] is True
    assert fixture["checks"]["bundle_status"]["json"]["ok"] is True
    assert fixture["checks"]["capabilities_validate"]["json"]["ok"] is True
    assert fixture["checks"]["capabilities_search"]["json"]["entries"][0]["id"] == "orchestration-fixture"
    assert fixture["checks"]["fixture_prove"]["json"]["ok"] is True
    assert fixture["checks"]["remote_bootstrap_fixture"]["json"]["remote_bootstrap_fixture"]["ok"] is True


def main():
    test_json_preflight_with_codegraph_fallback()
    test_preflight_help_exposes_codegraph_flags()
    test_audit_warning_policy()
    test_install_manifest_verification()
    test_package_archive_manifest()
    test_package_roundtrip_install_from_archive()
    test_package_verify_roundtrip_flag()
    test_bundle_status_json()
    test_bundle_status_with_package_roundtrip()
    test_orchestration_fixture_proves_worker_command_dag()
    test_capability_registry_and_preflight_surface()
    test_release_evidence_publish_readiness_artifact()
    test_publish_handoff_artifact_is_non_destructive()
    test_remote_bootstrap_artifact_is_non_destructive()
    test_remote_bootstrap_fixture_proves_apply_path()
    test_objective_audit_reports_requirements_and_blockers()
    test_continue_reports_resume_actions_without_applying_by_default()
    test_receiver_fixture_proves_installed_package_commands()
    print("installed repers smoke tests ok")


if __name__ == "__main__":
    main()

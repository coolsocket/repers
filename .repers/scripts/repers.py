#!/usr/bin/env python3
import os
import sys
import argparse
import shutil
import subprocess
import glob
import json
from pathlib import Path

# Define base paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALL_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_REPO_ROOT = os.path.dirname(INSTALL_ROOT) if os.path.basename(INSTALL_ROOT) == ".repers" else INSTALL_ROOT
REPO_ROOT = os.path.abspath(os.environ.get("REPERS_WORKSPACE_ROOT", DEFAULT_REPO_ROOT))
TEMPLATES_DIR = os.path.join(INSTALL_ROOT, "templates")

# Integration defaults
DEFAULT_CODEX_SKILLS_DIR = "C:/Users/Administrator/.codex/skills"
LSP_GUARD_CMD = "C:/Users/Administrator/AppData/Local/CodexAgentTools/lsp-guard/agent-lsp-guard.cmd"
PREFLIGHT_EXCLUDED_DIRS = {".git", ".repers", "repers_tasks", "templates", "__pycache__"}
AUDIT_EXCLUDED_DIRS = {".git", ".repers", "__pycache__"}
INDEX_DB_PATH = os.path.abspath(os.environ.get("REPERS_INDEX_DB_PATH", os.path.join(REPO_ROOT, ".repers", "index", "repers.db")))


def emit_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=True))


def has_excluded_part(path, excluded_dirs):
    parts = {part.lower() for part in os.path.normpath(path).split(os.sep)}
    return any(part.lower() in parts for part in excluded_dirs)

def init_task(task_name):
    """Initializes a new RePERS task workspace folder and copies standard templates."""
    task_dir_name = task_name.lower().replace(" ", "_").replace("-", "_")
    task_dir = os.path.join(REPO_ROOT, "repers_tasks", task_dir_name)
    
    if os.path.exists(task_dir):
        print(f"[-] Task directory already exists: {task_dir}")
        return False
        
    os.makedirs(task_dir, exist_ok=True)
    print(f"[+] Created task directory: {task_dir}")
    
    # List of templates to copy
    templates = ["research.md", "plan.md", "review.md", "shipping.md"]
    for temp in templates:
        src = os.path.join(TEMPLATES_DIR, temp)
        dst = os.path.join(task_dir, temp)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  -> Copied standard template: {temp}")
        else:
            print(f"  [!] Template not found: {src}")
            
    print(f"\n[OK] RePERS task '{task_name}' initialized successfully!")
    print(f"    Get started by researching in: repers_tasks/{task_dir_name}/research.md")
    return True

def run_preflight(
    query,
    as_json=False,
    refresh_index=False,
    codegraph=False,
    codegraph_init=False,
    codegraph_sync=True,
    codegraph_bin=None,
    codegraph_limit=12,
):
    """Performs a lightweight preflight token scan to prevent duplicate capability implementation."""
    if as_json or refresh_index:
        sys.path.append(SCRIPT_DIR)
        from research_index import build_research_artifact, refresh

        if refresh_index:
            refresh(INDEX_DB_PATH, REPO_ROOT, DEFAULT_CODEX_SKILLS_DIR)
        artifact = build_research_artifact(INDEX_DB_PATH, query, REPO_ROOT, DEFAULT_CODEX_SKILLS_DIR)
        if codegraph:
            from codegraph_support import collect_codegraph_evidence

            artifact["code_evidence"] = collect_codegraph_evidence(
                REPO_ROOT,
                query,
                limit=codegraph_limit,
                init=codegraph_init,
                sync=codegraph_sync,
                codegraph_bin=codegraph_bin,
            )
        if as_json:
            emit_json(artifact)
            return artifact["counts"]["results"] == 0

    print("====================================================")
    print(f"       RePERS Preflight Scan: '{query}'             ")
    print("====================================================")
    
    query_lower = query.lower()
    matches = []
    
    # 1. Scan Local Workspace Files
    print("[1] Scanning active workspace files...")
    extensions = ["*.py", "*.mjs", "*.js", "*.md"]
    for ext in extensions:
        search_path = os.path.join(REPO_ROOT, "**", ext)
        for filepath in glob.glob(search_path, recursive=True):
            if has_excluded_part(filepath, PREFLIGHT_EXCLUDED_DIRS):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if query_lower in line.lower():
                            matches.append({
                                "source": "workspace",
                                "path": os.path.relpath(filepath, REPO_ROOT),
                                "line": line_num,
                                "text": line.strip()
                            })
            except Exception:
                pass

    # 2. Scan Global Codex Skills (if directory exists)
    if os.path.exists(DEFAULT_CODEX_SKILLS_DIR):
        print("[2] Scanning global Codex skills...")
        for root, dirs, files in os.walk(DEFAULT_CODEX_SKILLS_DIR):
            for file in files:
                if file.endswith(".md"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                if query_lower in line.lower():
                                    matches.append({
                                        "source": f"global_skill ({os.path.basename(root)})",
                                        "path": os.path.relpath(filepath, DEFAULT_CODEX_SKILLS_DIR),
                                        "line": line_num,
                                        "text": line.strip()
                                    })
                    except Exception:
                        pass
    else:
        print("[2] Global Codex skills directory not found. Skipping.")

    if codegraph:
        sys.path.append(SCRIPT_DIR)
        from codegraph_support import collect_codegraph_evidence

        print("[3] Collecting optional CodeGraph code evidence...")
        code_evidence = collect_codegraph_evidence(
            REPO_ROOT,
            query,
            limit=codegraph_limit,
            init=codegraph_init,
            sync=codegraph_sync,
            codegraph_bin=codegraph_bin,
        )
        if code_evidence["ok"]:
            print(f"  [OK] CodeGraph evidence collected from {code_evidence['bin']}")
        else:
            reason = "; ".join(code_evidence["errors"]) or "unknown CodeGraph error"
            print(f"  [!] CodeGraph evidence unavailable: {reason}")

    print("\n=================== Results ========================")
    if not matches:
        print("  [OK] No matching capability found. Safe to implement!")
    else:
        print(f"  [!] Found {len(matches)} matching occurrences of '{query}':")
        # Group and deduplicate by file path
        by_file = {}
        for m in matches:
            by_file.setdefault(m["path"], []).append(m)
            
        for path, occurrences in list(by_file.items())[:10]: # Limit to top 10 files
            print(f"  - File: {path} ({occurrences[0]['source']})")
            for occ in occurrences[:3]: # Limit to top 3 lines per file
                print(f"    Line {occ['line']}: {occ['text'][:80]}")
            if len(occurrences) > 3:
                print(f"    ... and {len(occurrences)-3} more occurrences in this file")
        if len(by_file) > 10:
            print(f"  ... and {len(by_file)-10} more files matched.")
            
    print("====================================================")
    return len(matches) == 0


def run_index(args):
    sys.path.append(SCRIPT_DIR)
    from research_index import refresh, search

    if args.action == "refresh":
        result = refresh(INDEX_DB_PATH, REPO_ROOT, DEFAULT_CODEX_SKILLS_DIR)
        if args.json:
            emit_json(result)
        else:
            print(f"[OK] Indexed {result['documents_indexed']} documents into {result['db_path']}")
    elif args.action == "search":
        results = search(INDEX_DB_PATH, args.query, limit=args.limit)
        if args.json:
            emit_json(results)
        else:
            for result in results:
                print(f"- {result['source']}:{result['kind']}:{result['path']} :: {result['summary'][:120]}")


def run_capabilities(args):
    sys.path.append(SCRIPT_DIR)
    from capability_registry import load_registry, search_registry, validate_command

    registry_path = Path(INSTALL_ROOT) / "capabilities" / "registry.json"
    if args.action == "validate":
        result = validate_command(registry_path)
    elif args.action == "search":
        result = search_registry(args.query, limit=args.limit, path=registry_path)
    elif args.action == "list":
        registry = load_registry(registry_path)
        result = {
            "schema": "repers.capability_list.v1",
            "ok": True,
            "registry_path": registry.get("_path"),
            "count": len(registry.get("entries", [])),
            "entries": registry.get("entries", []),
        }
    else:
        raise ValueError(f"Unknown capabilities action: {args.action}")
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if result.get("ok") is False:
        sys.exit(1)


def task_dir_name(task_name):
    return task_name.lower().replace(" ", "_").replace("-", "_")


def write_research_artifacts(task, query, artifact):
    task_dir = os.path.join(REPO_ROOT, "repers_tasks", task_dir_name(task))
    os.makedirs(task_dir, exist_ok=True)
    json_path = os.path.join(task_dir, "research.json")
    md_path = os.path.join(task_dir, "research.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)
    lines = [
        f"# RePERS Research: {task}",
        "",
        f"## Query",
        f"`{query}`",
        "",
        "## Recommendation",
        f"* **Decision**: {artifact['recommendation']['decision']}",
        f"* **Reason**: {artifact['recommendation']['reason']}",
        "",
        "## Top Evidence",
    ]
    for result in artifact["results"][:10]:
        lines.append(f"* `{result['source']}:{result['kind']}:{result['path']}` - {result['summary']}")
    lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return {"research_json": json_path, "research_md": md_path}


def run_research(args):
    sys.path.append(SCRIPT_DIR)
    from research_index import build_research_artifact, refresh

    if args.refresh:
        refresh(INDEX_DB_PATH, REPO_ROOT, DEFAULT_CODEX_SKILLS_DIR)
    artifact = build_research_artifact(INDEX_DB_PATH, args.query, REPO_ROOT, DEFAULT_CODEX_SKILLS_DIR, limit=args.limit)
    paths = write_research_artifacts(args.task, args.query, artifact)
    if args.json:
        emit_json({"artifact": artifact, "paths": paths})
    else:
        print(f"[OK] Wrote research artifacts:")
        print(f"  - {paths['research_md']}")
        print(f"  - {paths['research_json']}")


def resolve_task_paths(task):
    task_dir = os.path.join(REPO_ROOT, "repers_tasks", task_dir_name(task))
    plan_path = os.path.join(task_dir, "plan.md")
    return task_dir, plan_path


def run_plan(args):
    sys.path.append(SCRIPT_DIR)
    from plan_runner import build_plan_json, build_plan_proposal

    task_dir, plan_path = resolve_task_paths(args.task)
    if args.from_research:
        proposal, json_path, md_path = build_plan_proposal(
            args.task,
            task_dir,
            objective=args.objective,
            max_steps=args.max_steps,
        )
        result = {"proposal": proposal, "path": str(json_path), "markdown_path": str(md_path)}
        if args.json:
            emit_json(result)
        else:
            print(f"[OK] Wrote proposed machine plan: {json_path}")
            print(f"[OK] Wrote proposed Markdown plan: {md_path}")
        return

    plan, output_path = build_plan_json(args.task, task_dir, plan_path)
    if args.json:
        emit_json({"plan": plan, "path": str(output_path)})
    else:
        print(f"[OK] Wrote machine plan: {output_path}")


def run_execution(args):
    sys.path.append(SCRIPT_DIR)
    from plan_runner import build_plan_json, dry_run, load_plan_json
    from backends import BackendUnavailable, get_backend

    task_dir, plan_path = resolve_task_paths(args.task)
    plan_json_path = os.path.join(task_dir, "plan.json")
    if args.use_existing_plan and os.path.exists(plan_json_path):
        plan = load_plan_json(task_dir)
    else:
        plan, _ = build_plan_json(args.task, task_dir, plan_path)

    if args.action == "dry-run":
        result = dry_run(plan)
    elif args.action == "local":
        if args.backend == "worker-command":
            command_template = args.worker_command or os.environ.get("REPERS_WORKER_COMMAND", "")
            from plan_runner import run_worker_command_ready

            result = run_worker_command_ready(
                plan,
                REPO_ROOT,
                task_dir,
                command_template,
                max_workers=args.max_workers,
                update_markdown=not args.no_update,
            )
            if args.json:
                emit_json(result)
            else:
                emit_json(result)
            return
        try:
            backend = get_backend(args.backend)
        except BackendUnavailable as exc:
            result = {
                "schema": "repers.run_result.v1",
                "task": args.task,
                "backend": args.backend,
                "ok": False,
                "error": str(exc),
                "results": [],
                "completed": [],
                "failed": [],
            }
            emit_json(result)
            sys.exit(1)
        result = backend.run_ready(plan, REPO_ROOT, task_dir, max_workers=args.max_workers, update_markdown=not args.no_update)
    else:
        raise ValueError(f"Unknown run action: {args.action}")

    if args.json:
        emit_json(result)
    else:
        emit_json(result)


def run_dispatch_command(args):
    sys.path.append(SCRIPT_DIR)
    from plan_runner import build_plan_json, dispatch_ready, load_plan_json

    task_dir, plan_path = resolve_task_paths(args.task)
    plan_json_path = os.path.join(task_dir, "plan.json")
    if args.use_existing_plan and os.path.exists(plan_json_path):
        plan = load_plan_json(task_dir)
    else:
        plan, _ = build_plan_json(args.task, task_dir, plan_path)

    manifest, manifest_path = dispatch_ready(
        plan,
        task_dir,
        backend=args.backend,
        max_workers=args.max_workers,
    )
    result = {"manifest": manifest, "path": str(manifest_path)}
    if args.json:
        emit_json(result)
    else:
        print(f"[OK] Wrote dispatch manifest: {manifest_path}")


def run_doctor_command(args):
    sys.path.append(SCRIPT_DIR)
    from doctor import fix_doctor, format_doctor, run_doctor

    if args.fix:
        result = fix_doctor(
            REPO_ROOT,
            INSTALL_ROOT,
            INDEX_DB_PATH,
            LSP_GUARD_CMD,
            DEFAULT_CODEX_SKILLS_DIR,
            refresh_index=args.refresh_index,
        )
    else:
        result = run_doctor(REPO_ROOT, INSTALL_ROOT, INDEX_DB_PATH, LSP_GUARD_CMD)
    if args.json:
        emit_json(result)
    else:
        print(format_doctor(result))


def run_review_command(args):
    sys.path.append(SCRIPT_DIR)
    from reviewer import review_task

    task_dir, _ = resolve_task_paths(args.task)
    result = review_task(task_dir, update_status=args.update_status)
    if args.json:
        emit_json(result)
    else:
        emit_json(result)


def run_shipping_command(args):
    sys.path.append(SCRIPT_DIR)
    from doctor import run_doctor
    from shipping import create_shipping_report

    task_dir, _ = resolve_task_paths(args.task)
    doctor_result = run_doctor(REPO_ROOT, INSTALL_ROOT, INDEX_DB_PATH, LSP_GUARD_CMD)
    report, output_path = create_shipping_report(
        args.task,
        task_dir,
        REPO_ROOT,
        doctor_result,
        installed_target=args.installed_target,
    )
    result = {"shipping": report, "path": str(output_path)}
    if args.json:
        emit_json(result)
    else:
        print(f"[OK] Wrote shipping report: {output_path}")


def run_release_command(args):
    sys.path.append(SCRIPT_DIR)
    from release_gate import create_release_gate

    task_dir, _ = resolve_task_paths(args.task)
    release, output_path = create_release_gate(
        args.task,
        task_dir,
        REPO_ROOT,
        INSTALL_ROOT,
        INDEX_DB_PATH,
        LSP_GUARD_CMD,
        installed_target=args.installed_target,
        strict_warnings=args.strict_warnings,
        update_status=args.update_status,
    )
    result = {"release": release, "path": str(output_path)}
    if args.json:
        emit_json(result)
    else:
        summary = release["summary"]
        status = "OK" if summary["ok"] else "FAILED"
        print(f"[{status}] Release gate wrote {output_path}")
        if summary["errors"]:
            print("Errors:")
            for error in summary["errors"]:
                print(f"  - {error}")
        if summary["warnings"]:
            print("Warnings:")
            for warning in summary["warnings"]:
                print(f"  - {warning}")
    if not release["summary"]["ok"]:
        sys.exit(1)


def run_release_evidence_command(args):
    sys.path.append(SCRIPT_DIR)
    from release_evidence import build_release_evidence

    evidence, path = build_release_evidence(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
        include_package=args.package,
        verify_roundtrip=args.verify_roundtrip,
    )
    result = {"release_evidence": evidence, "path": str(Path(path).resolve())}
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not evidence.get("ok"):
        sys.exit(1)


def run_publish_handoff_command(args):
    sys.path.append(SCRIPT_DIR)
    from publish_handoff import create_publish_handoff

    handoff, json_path, md_path = create_publish_handoff(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
        remote_name=args.remote_name,
        remote_url=args.remote_url,
        base_branch=args.base_branch,
        pr_title=args.pr_title,
        include_package=args.package,
        verify_roundtrip=args.verify_roundtrip,
    )
    result = {
        "publish_handoff": handoff,
        "path": str(Path(json_path).resolve()),
        "markdown_path": str(Path(md_path).resolve()),
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not handoff.get("ok"):
        sys.exit(1)


def run_remote_bootstrap_command(args):
    sys.path.append(SCRIPT_DIR)
    from remote_bootstrap import create_remote_bootstrap

    bootstrap, json_path, md_path = create_remote_bootstrap(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
        remote_name=args.remote_name,
        remote_url=args.remote_url,
        base_branch=args.base_branch,
        pr_title=args.pr_title,
        include_package=args.package,
        verify_roundtrip=args.verify_roundtrip,
        apply=args.apply,
    )
    result = {
        "remote_bootstrap": bootstrap,
        "path": str(Path(json_path).resolve()),
        "markdown_path": str(Path(md_path).resolve()),
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not bootstrap.get("ok"):
        sys.exit(1)


def run_remote_bootstrap_fixture_command(args):
    sys.path.append(SCRIPT_DIR)
    from remote_bootstrap import prove_remote_bootstrap_apply

    fixture, path = prove_remote_bootstrap_apply(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
    )
    result = {"remote_bootstrap_fixture": fixture, "path": str(Path(path).resolve())}
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not fixture.get("ok"):
        sys.exit(1)


def run_publish_clone_fixture_command(args):
    sys.path.append(SCRIPT_DIR)
    from publish_clone_fixture import prove_publish_clone

    fixture, path = prove_publish_clone(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
    )
    result = {"publish_clone_fixture": fixture, "path": str(Path(path).resolve())}
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not fixture.get("ok"):
        sys.exit(1)


def run_source_install_fixture_command(args):
    sys.path.append(SCRIPT_DIR)
    from source_install_fixture import prove_source_install

    fixture, path = prove_source_install(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
    )
    result = {"source_install_fixture": fixture, "path": str(Path(path).resolve())}
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not fixture.get("ok"):
        sys.exit(1)


def run_objective_audit_command(args):
    sys.path.append(SCRIPT_DIR)
    from objective_audit import DEFAULT_OBJECTIVE, build_objective_audit

    audit, path = build_objective_audit(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
        objective=args.objective or DEFAULT_OBJECTIVE,
        deep=args.deep,
    )
    result = {"objective_audit": audit, "path": str(Path(path).resolve())}
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not audit.get("ok"):
        sys.exit(1)


def run_continue_command(args):
    sys.path.append(SCRIPT_DIR)
    from continuation_runner import build_continuation_run

    result = build_continuation_run(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
        objective=args.objective,
        deep=args.deep,
        apply=args.apply,
        action_ids=args.action_id,
    )
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not result.get("ok"):
        sys.exit(1)


def run_state_command(args):
    sys.path.append(SCRIPT_DIR)
    from state_report import build_state_report

    state, json_path, markdown_path = build_state_report(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
        objective=args.objective,
        deep=args.deep,
    )
    result = {
        "state": state,
        "path": str(Path(json_path).resolve()),
        "markdown_path": str(Path(markdown_path).resolve()),
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not state.get("ok"):
        sys.exit(1)


def run_snapshot_freshness_command(args):
    sys.path.append(SCRIPT_DIR)
    from snapshot_freshness import build_snapshot_freshness

    freshness, json_path, markdown_path = build_snapshot_freshness(
        REPO_ROOT,
        output_dir=args.output,
        strict=args.strict,
    )
    result = {
        "snapshot_freshness": freshness,
        "path": str(Path(json_path).resolve()),
        "markdown_path": str(Path(markdown_path).resolve()),
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not freshness.get("ok"):
        sys.exit(1)


def run_open_source_benchmark_command(args):
    sys.path.append(SCRIPT_DIR)
    from open_source_benchmark import verify_open_source_benchmark, write_open_source_benchmark_report

    benchmark = verify_open_source_benchmark(REPO_ROOT, INSTALL_ROOT)
    json_path, markdown_path = write_open_source_benchmark_report(benchmark, args.output)
    result = {
        "open_source_benchmark": benchmark,
        "path": str(Path(json_path).resolve()),
        "markdown_path": str(Path(markdown_path).resolve()),
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not benchmark.get("ok"):
        sys.exit(1)


def run_release_pack_command(args):
    sys.path.append(SCRIPT_DIR)
    from release_pack import create_release_pack

    pack, json_path, markdown_path, archive_path = create_release_pack(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
        remote_name=args.remote_name,
        remote_url=args.remote_url,
        base_branch=args.base_branch,
        pr_title=args.pr_title,
    )
    result = {
        "release_pack": pack,
        "path": str(Path(json_path).resolve()),
        "markdown_path": str(Path(markdown_path).resolve()),
        "archive_path": str(Path(archive_path).resolve()),
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not pack.get("ok"):
        sys.exit(1)


def run_verify_all_command(args):
    sys.path.append(SCRIPT_DIR)
    from verify_all import build_verify_all

    report, json_path, markdown_path = build_verify_all(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
    )
    result = {
        "verify_all": report,
        "path": str(Path(json_path).resolve()),
        "markdown_path": str(Path(markdown_path).resolve()),
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not report.get("ok"):
        sys.exit(1)


def run_receiver_fixture_command(args):
    sys.path.append(SCRIPT_DIR)
    from receiver_fixture import prove_receiver

    result = prove_receiver(
        REPO_ROOT,
        INSTALL_ROOT,
        output_dir=args.output,
        verify_package_roundtrip=args.verify_package_roundtrip,
    )
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not result.get("ok"):
        sys.exit(1)


def run_install_command(args):
    sys.path.append(SCRIPT_DIR)
    from install_repers import install, verify_manifest

    install_result = install(
        args.target,
        with_hook=not args.no_hook,
        hook_policy=args.hook_policy,
        quiet=args.json,
    )
    verify_result = verify_manifest(Path(args.target).resolve() / ".repers")
    result = {
        "schema": "repers.install_command.v1",
        "ok": bool(install_result.get("ok") and verify_result.get("ok")),
        "install": install_result,
        "verify_install": verify_result,
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not result.get("ok"):
        sys.exit(1)


def run_install_hook_command(args):
    sys.path.append(SCRIPT_DIR)
    from install_repers import ensure_gitignore, write_hook

    target_root = os.path.abspath(REPO_ROOT)
    hook_path = write_hook(Path(target_root), Path(INSTALL_ROOT), audit_policy=args.hook_policy)
    gitignore_path = ensure_gitignore(Path(target_root))
    result = {
        "schema": "repers.install_hook.v1",
        "ok": True,
        "workspace_root": target_root,
        "install_root": os.path.abspath(INSTALL_ROOT),
        "hook_path": str(hook_path),
        "gitignore_path": str(gitignore_path),
        "hook_policy": args.hook_policy,
    }
    if args.json:
        emit_json(result)
    else:
        print(f"[OK] Installed RePERS pre-commit hook at {hook_path}")


def run_refresh_manifest_command(args):
    sys.path.append(SCRIPT_DIR)
    from install_repers import verify_manifest, write_manifest

    target_root = Path(REPO_ROOT).resolve()
    install_root = Path(INSTALL_ROOT).resolve()
    hook_path = target_root / ".git" / "hooks" / "pre-commit"
    gitignore_path = target_root / ".gitignore"
    manifest_path, manifest = write_manifest(
        target_root,
        install_root,
        with_hook=hook_path.exists(),
        hook_policy=args.hook_policy,
        hook_path=hook_path if hook_path.exists() else None,
        gitignore_path=gitignore_path if gitignore_path.exists() else None,
    )
    verify = verify_manifest(install_root, strict_extra=args.strict_extra)
    result = {
        "schema": "repers.refresh_manifest.v1",
        "ok": bool(verify.get("ok")),
        "manifest_path": str(manifest_path.resolve()),
        "manifest_file_count": manifest.get("file_count"),
        "verify_install": verify,
    }
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if not result["ok"]:
        sys.exit(1)


def run_verify_install_command(args):
    sys.path.append(SCRIPT_DIR)
    from install_repers import verify_manifest

    install_root = Path(args.install_root).resolve() if args.install_root else Path(INSTALL_ROOT).resolve()
    result = verify_manifest(install_root, strict_extra=args.strict_extra)
    if args.json:
        emit_json(result)
    else:
        status = "OK" if result["ok"] else "FAILED"
        print(f"[{status}] Verified RePERS install manifest at {result['manifest_path']}")
        print(f"Checked {result['checked_count']} of {result['file_count']} manifest files")
        if result["missing"]:
            print("Missing files:")
            for path in result["missing"]:
                print(f"  - {path}")
        if result["changed"]:
            print("Changed files:")
            for item in result["changed"]:
                print(f"  - {item['path']} ({item['reason']})")
        if result["extra"]:
            label = "Extra files" if args.strict_extra else "Extra files (allowed without --strict-extra)"
            print(f"{label}:")
            for path in result["extra"]:
                print(f"  - {path}")
        if result["errors"]:
            print("Errors:")
            for error in result["errors"]:
                print(f"  - {error}")
    if not result["ok"]:
        sys.exit(1)


def run_package_command(args):
    sys.path.append(SCRIPT_DIR)
    from package_repers import create_package

    result = create_package(args.output, verify_roundtrip=args.verify_roundtrip)
    if args.json:
        emit_json(result)
    else:
        print(f"[OK] Wrote RePERS package archive: {result['archive_path']}")
        print(f"Files: {result['manifest']['file_count']}")
        print(f"SHA-256: {result['archive_sha256']}")
        if args.verify_roundtrip:
            if result.get("roundtrip", {}).get("ok"):
                print("Round-trip verification: OK")
            else:
                print("Round-trip verification: FAILED")
    if not result["ok"]:
        sys.exit(1)


def run_bundle_status_command(args):
    sys.path.append(SCRIPT_DIR)
    from doctor import run_doctor
    from install_repers import verify_manifest

    verify = verify_manifest(Path(INSTALL_ROOT).resolve(), strict_extra=args.strict_extra)
    doctor = run_doctor(REPO_ROOT, INSTALL_ROOT, INDEX_DB_PATH, LSP_GUARD_CMD)
    result = {
        "schema": "repers.bundle_status.v1",
        "ok": bool(verify.get("ok") and doctor.get("ok")),
        "workspace_root": REPO_ROOT,
        "install_root": INSTALL_ROOT,
        "verify_install": verify,
        "doctor": doctor,
        "package": None,
        "errors": [],
    }
    if not verify.get("ok"):
        result["errors"].append("verify-install failed")
    if not doctor.get("ok"):
        result["errors"].append("doctor failed")

    if args.package:
        from package_repers import create_package

        package = create_package(args.output, verify_roundtrip=args.verify_roundtrip)
        result["package"] = package
        if not package.get("ok"):
            result["ok"] = False
            result["errors"].append("package failed")

    if args.json:
        emit_json(result)
    else:
        status = "OK" if result["ok"] else "FAILED"
        print(f"[{status}] RePERS bundle status")
        print(f"Install verify: {'OK' if verify.get('ok') else 'FAILED'}")
        print(f"Doctor: {'OK' if doctor.get('ok') else 'FAILED'}")
        if result["package"]:
            package_status = "OK" if result["package"].get("ok") else "FAILED"
            print(f"Package: {package_status} ({result['package']['archive_path']})")
            if result["package"].get("roundtrip") is not None:
                roundtrip_status = "OK" if result["package"]["roundtrip"].get("ok") else "FAILED"
                print(f"Package round-trip: {roundtrip_status}")
        if result["errors"]:
            print("Errors:")
            for error in result["errors"]:
                print(f"  - {error}")
    if not result["ok"]:
        sys.exit(1)


def run_fixture_command(args):
    sys.path.append(SCRIPT_DIR)
    from orchestration_fixture import (
        assert_fixture,
        create_fixture_plan,
        prove_fixture,
        worker_record_from_env,
    )

    if args.action == "create":
        result = create_fixture_plan(REPO_ROOT, task=args.task, reset=args.reset)
    elif args.action == "worker":
        result = worker_record_from_env()
    elif args.action == "assert":
        result = assert_fixture(REPO_ROOT, task=args.task)
    elif args.action == "prove":
        result = prove_fixture(
            REPO_ROOT,
            INSTALL_ROOT,
            task=args.task,
            max_workers=args.max_workers,
            reset=not args.no_reset,
        )
    else:
        raise ValueError(f"Unknown fixture action: {args.action}")
    if args.json:
        emit_json(result)
    else:
        emit_json(result)
    if result.get("ok") is False:
        sys.exit(1)


def run_audit(task_name=None, strict_warnings=False):
    """Performs pre-shipping audit checks to ensure clean delivery."""
    print("====================================================")
    print("            RePERS Pre-Shipping Audit               ")
    print("====================================================")
    
    warnings = 0
    errors = 0
    
    # Check 1: Git Status Check
    print("[1] Checking Git Working Tree Status...")
    try:
        git_status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        changes = git_status_proc.stdout.strip()
        if changes:
            print("  [!] Warning: You have uncommitted or untracked changes in your workspace:")
            for line in changes.split("\n"):
                print(f"      {line}")
            warnings += 1
        else:
            print("  [OK] Working tree is completely clean.")
    except Exception as e:
        print(f"  [!] Error running git: {e}")
        errors += 1
        
    # Check 2: Temporary Files Scan
    print("\n[2] Scanning for Stray Temporary Files...")
    temp_files = [".codex_session", "codex_prompt_docs.txt"]
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d.lower() not in AUDIT_EXCLUDED_DIRS]
        for file in files:
            if file in temp_files or "codex_prompt" in file:
                print(f"  [!] Warning: Found temporary/session file: {os.path.join(root, file)}")
                warnings += 1
                
    if warnings == 0:
        print("  [OK] No stray temporary files found.")
        
    # Check 3: Check task artifacts if task name specified
    if task_name:
        task_dir_name = task_name.lower().replace(" ", "_").replace("-", "_")
        task_dir = os.path.join(REPO_ROOT, "repers_tasks", task_dir_name)
        print(f"\n[3] Auditing Artifacts for Task: {task_name}...")
        
        if not os.path.exists(task_dir):
            print(f"  [ERR] Task directory not found at: {task_dir}")
            errors += 1
            return False
            
        required_files = ["research.md", "plan.md", "review.md", "shipping.md"]
        for f in required_files:
            file_path = os.path.join(task_dir, f)
            if not os.path.exists(file_path):
                print(f"  [ERR] Missing required stage artifact: {f}")
                errors += 1
            else:
                # Basic check if it has been modified from template
                stat = os.stat(file_path)
                tmpl_path = os.path.join(TEMPLATES_DIR, f)
                tmpl_stat = os.stat(tmpl_path)
                if stat.st_size == tmpl_stat.st_size:
                    print(f"  [!] Warning: Stage artifact '{f}' seems unmodified from template.")
                    warnings += 1
                else:
                    print(f"  [OK] Stage artifact '{f}' verified.")
    else:
         print("\n[3] No specific task name provided for artifact-level audit.")
         
    # Check 4: LSP Guard integration
    print("\n[4] Integrating LSP Guard status check...")
    if os.path.exists(LSP_GUARD_CMD):
        print(f"  -> LSP Guard tool detected. Running on workspace...")
        try:
            # Run LSP Guard as a dry run / diagnostic
            proc = subprocess.run([LSP_GUARD_CMD, REPO_ROOT], cwd=REPO_ROOT, capture_output=True, text=True)
            if proc.returncode != 0:
                print("  [!] Warning: LSP Guard returned diagnostics or errors:")
                print(proc.stdout[:400]) # Print first 400 chars of diagnostics
                warnings += 1
            else:
                print("  [OK] LSP Guard syntax check passed successfully.")
        except Exception as e:
            print(f"  [!] Could not run LSP Guard: {e}")
    else:
        print("  [OK] LSP Guard local tool not registered at path (skipped).")

    print("\n====================================================")
    print(f"Audit Summary: {errors} Errors, {warnings} Warnings")
    print("====================================================")
    if errors > 0:
        print("  [ERR] Audit FAILED. Resolve errors before shipping.")
        return False
    elif warnings > 0:
        if strict_warnings:
            print("  [ERR] Audit FAILED because --strict-warnings is enabled.")
            return False
        print("  [WARN] Audit passed with warnings. Consider cleaning up warnings before shipping.")
        return True
    else:
        print("  [OK] Audit PASSED 100%! Ready to ship.")
        return True

def handle_dag(args):
    """Handles parsing, scheduling, and updating DAG tasks in the plan."""
    import json
    # Resolve plan path
    plan_path = args.plan
    if not plan_path:
        if args.task:
            task_dir_name = args.task.lower().replace(" ", "_").replace("-", "_")
            plan_path = os.path.join(REPO_ROOT, "repers_tasks", task_dir_name, "plan.md")
        else:
            # Try some common locations
            common_locations = [
                os.path.join(REPO_ROOT, "plan.md"),
                os.path.join(REPO_ROOT, ".hermes", "plan.md"),
                "plan.md"
            ]
            for loc in common_locations:
                if os.path.exists(loc):
                    plan_path = loc
                    break
            if not plan_path:
                print("[-] Error: No task, plan path specified or common plan.md found.", file=sys.stderr)
                sys.exit(1)

    print(f"[+] Loading DAG from plan: {plan_path}", file=sys.stderr)
    try:
        sys.path.append(SCRIPT_DIR)
        from dag_engine import DAGEngine
        engine = DAGEngine(plan_path)
    except Exception as e:
        print(f"[-] Error loading/validating DAG: {e}", file=sys.stderr)
        sys.exit(1)

    if args.action == "list":
        print("\n====================================================")
        print("                RePERS DAG Task List                ")
        print("====================================================")
        steps = engine.get_all_steps()
        for sid, step in sorted(steps.items(), key=lambda x: int(x[0])):
            deps_str = ", ".join(step["depends_on"]) if step["depends_on"] else "None"
            status_icon = "[ ]" if step["status"] == "Pending" else "[~]" if step["status"] == "In Progress" else "[x]" if step["status"] == "Completed" else "[!]"
            print(f"  {status_icon} Step {sid}: {step['title']}")
            print(f"     Action: {step['action']}")
            print(f"     Target File: {step['target_file']}")
            print(f"     Verification: {step['verification_command']}")
            print(f"     Depends On: {deps_str}")
            print(f"     Status: {step['status']}")
            print("----------------------------------------------------")
            
    elif args.action == "next":
        # Print next ready tasks as JSON
        ready = engine.get_ready_steps()
        output_list = []
        for step in ready:
            output_list.append({
                "id": step["id"],
                "title": step["title"],
                "action": step["action"],
                "target_file": step["target_file"],
                "verification_command": step["verification_command"],
                "expected_outcome": step["expected_outcome"],
                "depends_on": step["depends_on"],
                "status": step["status"]
            })
        print(json.dumps(output_list, indent=2))
        
    elif args.action == "update":
        if not args.step:
            print("[-] Error: --step is required for update action.", file=sys.stderr)
            sys.exit(1)
        if not args.status:
            print("[-] Error: --status is required for update action.", file=sys.stderr)
            sys.exit(1)
            
        try:
            engine.update_status(args.step, args.status)
            print(f"[OK] Successfully updated Step {args.step} to '{args.status}'.")
        except Exception as e:
            print(f"[-] Error updating step status: {e}", file=sys.stderr)
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="RePERS Framework CLI Helper")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Init Subparser
    init_parser = subparsers.add_parser("init", help="Initialize a new RePERS task workspace")
    init_parser.add_argument("--task", required=True, help="Name of the task")
    
    # Preflight Subparser
    preflight_parser = subparsers.add_parser("preflight", help="Query local & global paths to prevent duplicates")
    preflight_parser.add_argument("--query", required=True, help="Keyword query for capability search")
    preflight_parser.add_argument("--json", action="store_true", help="Emit structured JSON preflight results")
    preflight_parser.add_argument("--refresh", action="store_true", help="Refresh the local capability index first")
    preflight_parser.add_argument("--codegraph", action="store_true", help="Attach optional CodeGraph code evidence")
    preflight_parser.add_argument("--codegraph-init", action="store_true", help="Initialize CodeGraph when .codegraph is missing")
    preflight_parser.add_argument("--no-codegraph-sync", action="store_true", help="Skip CodeGraph sync before querying")
    preflight_parser.add_argument("--codegraph-bin", help="Explicit CodeGraph CLI or JavaScript entrypoint")
    preflight_parser.add_argument("--codegraph-limit", type=int, default=12, help="Maximum CodeGraph query results")

    index_parser = subparsers.add_parser("index", help="Refresh or query the local RePERS capability index")
    index_parser.add_argument("--action", choices=["refresh", "search"], default="refresh")
    index_parser.add_argument("--query", default="", help="Query for index search")
    index_parser.add_argument("--limit", type=int, default=20)
    index_parser.add_argument("--json", action="store_true")

    capabilities_parser = subparsers.add_parser("capabilities", help="List, search, or validate the local RePERS capability registry")
    capabilities_parser.add_argument("--action", choices=["list", "search", "validate"], default="list")
    capabilities_parser.add_argument("--query", default="", help="Query for capability search")
    capabilities_parser.add_argument("--limit", type=int, default=20)
    capabilities_parser.add_argument("--json", action="store_true")

    research_parser = subparsers.add_parser("research", help="Create structured research artifacts from preflight/index evidence")
    research_parser.add_argument("--task", required=True)
    research_parser.add_argument("--query", required=True)
    research_parser.add_argument("--limit", type=int, default=20)
    research_parser.add_argument("--refresh", action="store_true")
    research_parser.add_argument("--json", action="store_true")

    plan_parser = subparsers.add_parser("plan", help="Generate plan artifacts from a RePERS plan.md or research.json")
    plan_parser.add_argument("--task", required=True)
    plan_parser.add_argument("--from-research", action="store_true", help="Generate plan.proposed artifacts from research.json")
    plan_parser.add_argument("--objective", default="", help="Objective text to include in a plan proposal")
    plan_parser.add_argument("--max-steps", type=int, default=6, help="Maximum proposed steps when using --from-research")
    plan_parser.add_argument("--json", action="store_true")

    run_parser = subparsers.add_parser("run", help="Dry-run or execute ready local DAG steps")
    run_parser.add_argument("--task", required=True)
    run_parser.add_argument("--action", choices=["dry-run", "local"], default="dry-run")
    run_parser.add_argument("--backend", choices=["local", "worker-command", "openai-agents", "langgraph", "mcp"], default="local")
    run_parser.add_argument("--use-existing-plan", action="store_true", help="Use existing plan.json instead of refreshing from plan.md")
    run_parser.add_argument("--max-workers", type=int, default=4)
    run_parser.add_argument("--no-update", action="store_true", help="Do not update plan.md statuses after execution")
    run_parser.add_argument("--worker-command", help="Command template for worker-command backend; also accepts REPERS_WORKER_COMMAND")
    run_parser.add_argument("--json", action="store_true")

    dispatch_parser = subparsers.add_parser("dispatch", help="Create parallel worker dispatch packets for ready non-local DAG steps")
    dispatch_parser.add_argument("--task", required=True)
    dispatch_parser.add_argument("--backend", choices=["codex", "openai-agents", "langgraph", "mcp"], default="codex")
    dispatch_parser.add_argument("--use-existing-plan", action="store_true", help="Use existing plan.json instead of refreshing from plan.md")
    dispatch_parser.add_argument("--max-workers", type=int, default=4)
    dispatch_parser.add_argument("--json", action="store_true")

    doctor_parser = subparsers.add_parser("doctor", help="Check RePERS runtime, install, index, hook, and optional adapters")
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.add_argument("--fix", action="store_true", help="Repair missing local install pieces such as hook, ignore rules, and index")
    doctor_parser.add_argument("--refresh-index", action="store_true", help="Refresh the local capability index while fixing")

    review_parser = subparsers.add_parser("review", help="Validate step result contracts for a task")
    review_parser.add_argument("--task", required=True)
    review_parser.add_argument("--json", action="store_true")
    review_parser.add_argument("--update-status", action="store_true", help="Update plan.md statuses from validated result JSON files")

    shipping_parser = subparsers.add_parser("shipping", help="Write machine-readable delivery evidence for a task")
    shipping_parser.add_argument("--task", required=True)
    shipping_parser.add_argument("--installed-target", help="Optional installed repository target to include in shipping evidence")
    shipping_parser.add_argument("--json", action="store_true")

    release_parser = subparsers.add_parser("release", help="Run review, doctor, shipping, and audit gates for a task")
    release_parser.add_argument("--task", required=True)
    release_parser.add_argument("--installed-target", help="Optional installed repository target to include in release evidence")
    release_parser.add_argument("--strict-warnings", action="store_true", help="Fail the release gate when audit warnings are present")
    release_parser.add_argument("--update-status", action="store_true", help="Update plan.md statuses from validated result JSON files before release")
    release_parser.add_argument("--json", action="store_true")

    release_evidence_parser = subparsers.add_parser("release-evidence", help="Write publish-readiness evidence for the RePERS repository")
    release_evidence_parser.add_argument("--output", default="dist", help="Output directory for release evidence")
    release_evidence_parser.add_argument("--package", action="store_true", help="Create package evidence as part of the release evidence")
    release_evidence_parser.add_argument("--verify-roundtrip", action="store_true", help="When --package is used, verify package round-trip install")
    release_evidence_parser.add_argument("--json", action="store_true")

    publish_handoff_parser = subparsers.add_parser("publish-handoff", help="Write non-destructive push and PR handoff artifacts")
    publish_handoff_parser.add_argument("--output", default="dist", help="Output directory for publish handoff artifacts")
    publish_handoff_parser.add_argument("--remote-name", default="origin", help="Remote name to use in generated commands")
    publish_handoff_parser.add_argument("--remote-url", help="Optional remote URL to include in the generated add-remote command")
    publish_handoff_parser.add_argument("--base-branch", default="main", help="Base branch for generated draft PR command")
    publish_handoff_parser.add_argument("--pr-title", help="Optional draft PR title; defaults to the latest commit subject")
    publish_handoff_parser.add_argument("--package", action="store_true", help="Create package evidence before writing the handoff")
    publish_handoff_parser.add_argument("--verify-roundtrip", action="store_true", help="When --package is used, verify package round-trip install")
    publish_handoff_parser.add_argument("--json", action="store_true")

    remote_bootstrap_parser = subparsers.add_parser("remote-bootstrap", help="Write or optionally apply remote setup and publish handoff artifacts")
    remote_bootstrap_parser.add_argument("--output", default="dist", help="Output directory for remote bootstrap artifacts")
    remote_bootstrap_parser.add_argument("--remote-name", default="origin", help="Remote name to configure or describe")
    remote_bootstrap_parser.add_argument("--remote-url", help="Remote URL to include in generated commands or apply with --apply")
    remote_bootstrap_parser.add_argument("--base-branch", default="main", help="Base branch for generated draft PR command")
    remote_bootstrap_parser.add_argument("--pr-title", help="Optional draft PR title; defaults to the latest commit subject")
    remote_bootstrap_parser.add_argument("--package", action="store_true", help="Create package evidence before writing the handoff")
    remote_bootstrap_parser.add_argument("--verify-roundtrip", action="store_true", help="When --package is used, verify package round-trip install")
    remote_bootstrap_parser.add_argument("--apply", action="store_true", help="Actually run git remote add when --remote-url is provided")
    remote_bootstrap_parser.add_argument("--json", action="store_true")

    remote_bootstrap_fixture_parser = subparsers.add_parser("remote-bootstrap-fixture", help="Prove remote-bootstrap --apply against a temporary local bare remote")
    remote_bootstrap_fixture_parser.add_argument("--output", default="dist", help="Output directory for remote bootstrap fixture evidence")
    remote_bootstrap_fixture_parser.add_argument("--json", action="store_true")

    publish_clone_fixture_parser = subparsers.add_parser("publish-clone-fixture", help="Prove a local bare-remote publish and clone can verify RePERS from the clone")
    publish_clone_fixture_parser.add_argument("--output", default="dist", help="Output directory for publish clone fixture evidence")
    publish_clone_fixture_parser.add_argument("--json", action="store_true")

    source_install_fixture_parser = subparsers.add_parser("source-install-fixture", help="Prove source/clone one-command install into a fresh Git repository")
    source_install_fixture_parser.add_argument("--output", default="dist", help="Output directory for source install fixture evidence")
    source_install_fixture_parser.add_argument("--json", action="store_true")

    objective_audit_parser = subparsers.add_parser("objective-audit", help="Audit RePERS against the full repository objective")
    objective_audit_parser.add_argument("--output", default="dist", help="Output directory for objective audit artifacts")
    objective_audit_parser.add_argument("--objective", help="Objective text to audit; defaults to the current RePERS build objective")
    objective_audit_parser.add_argument("--deep", action="store_true", help="Run package, receiver, handoff, and smoke checks before auditing")
    objective_audit_parser.add_argument("--json", action="store_true")

    continue_parser = subparsers.add_parser("continue", help="Read objective continuation actions and optionally run ready local actions")
    continue_parser.add_argument("--output", default="dist", help="Output directory for objective audit and continuation artifacts")
    continue_parser.add_argument("--objective", help="Objective text to audit; defaults to the current RePERS build objective")
    continue_parser.add_argument("--deep", action="store_true", help="Run deep objective audit before selecting continuation actions")
    continue_parser.add_argument("--apply", action="store_true", help="Execute ready local continuation actions")
    continue_parser.add_argument("--action-id", action="append", help="Limit execution/reporting to one local continuation action id; repeatable")
    continue_parser.add_argument("--json", action="store_true")

    state_parser = subparsers.add_parser("state", help="Write compact RePERS repository state artifacts")
    state_parser.add_argument("--output", default="dist", help="Output directory for state, objective audit, and continuation artifacts")
    state_parser.add_argument("--objective", help="Objective text to audit; defaults to the current RePERS build objective")
    state_parser.add_argument("--deep", action="store_true", help="Run deep objective audit before writing state")
    state_parser.add_argument("--json", action="store_true")

    snapshot_freshness_parser = subparsers.add_parser("snapshot-freshness", help="Compare generated state evidence with live Git state")
    snapshot_freshness_parser.add_argument("--output", default="dist", help="Output directory containing generated RePERS evidence artifacts")
    snapshot_freshness_parser.add_argument("--strict", action="store_true", help="Exit non-zero when comparable snapshots are stale")
    snapshot_freshness_parser.add_argument("--json", action="store_true")

    open_source_benchmark_parser = subparsers.add_parser("open-source-benchmark", help="Verify the stored 10-repository open-source structure benchmark")
    open_source_benchmark_parser.add_argument("--output", default="dist", help="Output directory for benchmark verification artifacts")
    open_source_benchmark_parser.add_argument("--json", action="store_true")

    release_pack_parser = subparsers.add_parser("release-pack", help="Build one transferable package plus evidence handoff archive")
    release_pack_parser.add_argument("--output", default="dist", help="Output directory for release-pack artifacts")
    release_pack_parser.add_argument("--remote-name", default="origin", help="Remote name to use in generated handoff commands")
    release_pack_parser.add_argument("--remote-url", help="Optional remote URL to include in generated handoff commands")
    release_pack_parser.add_argument("--base-branch", default="main", help="Base branch for generated draft PR command")
    release_pack_parser.add_argument("--pr-title", help="Optional draft PR title; defaults to the latest commit subject")
    release_pack_parser.add_argument("--json", action="store_true")

    verify_all_parser = subparsers.add_parser("verify-all", help="Run all local RePERS gates sequentially with isolated outputs")
    verify_all_parser.add_argument("--output", default="dist", help="Output directory for verify-all artifacts")
    verify_all_parser.add_argument("--json", action="store_true")

    receiver_fixture_parser = subparsers.add_parser("receiver-fixture", help="Install the package into a fresh Git repo and prove receiver commands")
    receiver_fixture_parser.add_argument("--output", default="dist", help="Output directory for the package archive")
    receiver_fixture_parser.add_argument("--verify-package-roundtrip", action="store_true", help="Also run package-level round-trip verification before receiver checks")
    receiver_fixture_parser.add_argument("--json", action="store_true")

    install_parser = subparsers.add_parser("install", help="Install this RePERS bundle into a target Git repository")
    install_parser.add_argument("--target", required=True, help="Target Git repository path")
    install_parser.add_argument("--no-hook", action="store_true", help="Copy files without installing the pre-commit hook")
    install_parser.add_argument("--hook-policy", choices=["warn", "strict"], default="warn", help="Whether the installed hook allows warnings or treats them as failures")
    install_parser.add_argument("--json", action="store_true")

    install_hook_parser = subparsers.add_parser("install-hook", help="Install or refresh the RePERS pre-commit hook in this repo")
    install_hook_parser.add_argument("--json", action="store_true")
    install_hook_parser.add_argument("--hook-policy", choices=["warn", "strict"], default="warn", help="Whether the hook allows warnings or treats them as failures")

    refresh_manifest_parser = subparsers.add_parser("refresh-manifest", help="Refresh .repers/manifest.json for the installed RePERS runtime")
    refresh_manifest_parser.add_argument("--hook-policy", choices=["warn", "strict"], default="warn", help="Manifest hook policy to record")
    refresh_manifest_parser.add_argument("--strict-extra", action="store_true", help="Fail when non-runtime files exist in the install root but are not in the manifest")
    refresh_manifest_parser.add_argument("--json", action="store_true")

    verify_install_parser = subparsers.add_parser("verify-install", help="Verify .repers/manifest.json against the installed bundle")
    verify_install_parser.add_argument("--install-root", help="Path to the .repers install root; defaults to this CLI's install root")
    verify_install_parser.add_argument("--strict-extra", action="store_true", help="Fail when non-runtime files exist in the install root but are not in the manifest")
    verify_install_parser.add_argument("--json", action="store_true")

    package_parser = subparsers.add_parser("package", help="Create a distributable RePERS source archive")
    package_parser.add_argument("--output", default="dist", help="Output directory for the package archive")
    package_parser.add_argument("--verify-roundtrip", action="store_true", help="Extract the archive, install into a temporary Git repo, and run verify-install")
    package_parser.add_argument("--json", action="store_true")

    bundle_status_parser = subparsers.add_parser("bundle-status", help="Summarize installed bundle, doctor, and optional package readiness")
    bundle_status_parser.add_argument("--json", action="store_true")
    bundle_status_parser.add_argument("--strict-extra", action="store_true", help="Fail when non-runtime files exist in the install root but are not in the manifest")
    bundle_status_parser.add_argument("--package", action="store_true", help="Create a package archive and include package readiness in the status")
    bundle_status_parser.add_argument("--output", default="dist", help="Output directory when --package is used")
    bundle_status_parser.add_argument("--verify-roundtrip", action="store_true", help="When --package is used, verify archive extraction, install, and verify-install")

    fixture_parser = subparsers.add_parser("fixture", help="Create or prove deterministic RePERS orchestration fixtures")
    fixture_parser.add_argument("--action", choices=["create", "worker", "assert", "prove"], default="prove")
    fixture_parser.add_argument("--task", default="large-task-fixture")
    fixture_parser.add_argument("--max-workers", type=int, default=3)
    fixture_parser.add_argument("--reset", action="store_true", help="Reset fixture artifacts when --action=create is used")
    fixture_parser.add_argument("--no-reset", action="store_true", help="Keep existing fixture artifacts when --action=prove is used")
    fixture_parser.add_argument("--json", action="store_true")
    
    # Audit Subparser
    audit_parser = subparsers.add_parser("audit", help="Run pre-shipping checks")
    audit_parser.add_argument("--task", help="Name of the task to verify specific artifacts")
    audit_parser.add_argument("--strict-warnings", action="store_true", help="Return failure when audit warnings are present")
    
    # DAG Subparser
    dag_parser = subparsers.add_parser("dag", help="Manage and execute a plan's task DAG")
    dag_parser.add_argument("--task", help="Name of the task (will derive plan path)")
    dag_parser.add_argument("--plan", help="Direct path to plan.md file")
    dag_parser.add_argument("--action", choices=["list", "next", "update"], default="list", help="DAG action to perform")
    dag_parser.add_argument("--step", help="Step number (required for update)")
    dag_parser.add_argument("--status", help="New status value (required for update)")
    
    args = parser.parse_args()
    
    if args.command == "init":
        sys.exit(0 if init_task(args.task) else 1)
    elif args.command == "preflight":
        run_preflight(
            args.query,
            as_json=args.json,
            refresh_index=args.refresh,
            codegraph=args.codegraph,
            codegraph_init=args.codegraph_init,
            codegraph_sync=not args.no_codegraph_sync,
            codegraph_bin=args.codegraph_bin,
            codegraph_limit=args.codegraph_limit,
        )
    elif args.command == "index":
        run_index(args)
    elif args.command == "capabilities":
        run_capabilities(args)
    elif args.command == "research":
        run_research(args)
    elif args.command == "plan":
        run_plan(args)
    elif args.command == "run":
        run_execution(args)
    elif args.command == "dispatch":
        run_dispatch_command(args)
    elif args.command == "doctor":
        run_doctor_command(args)
    elif args.command == "review":
        run_review_command(args)
    elif args.command == "shipping":
        run_shipping_command(args)
    elif args.command == "release":
        run_release_command(args)
    elif args.command == "release-evidence":
        run_release_evidence_command(args)
    elif args.command == "publish-handoff":
        run_publish_handoff_command(args)
    elif args.command == "remote-bootstrap":
        run_remote_bootstrap_command(args)
    elif args.command == "remote-bootstrap-fixture":
        run_remote_bootstrap_fixture_command(args)
    elif args.command == "publish-clone-fixture":
        run_publish_clone_fixture_command(args)
    elif args.command == "source-install-fixture":
        run_source_install_fixture_command(args)
    elif args.command == "objective-audit":
        run_objective_audit_command(args)
    elif args.command == "continue":
        run_continue_command(args)
    elif args.command == "state":
        run_state_command(args)
    elif args.command == "snapshot-freshness":
        run_snapshot_freshness_command(args)
    elif args.command == "open-source-benchmark":
        run_open_source_benchmark_command(args)
    elif args.command == "release-pack":
        run_release_pack_command(args)
    elif args.command == "verify-all":
        run_verify_all_command(args)
    elif args.command == "receiver-fixture":
        run_receiver_fixture_command(args)
    elif args.command == "install":
        run_install_command(args)
    elif args.command == "install-hook":
        run_install_hook_command(args)
    elif args.command == "refresh-manifest":
        run_refresh_manifest_command(args)
    elif args.command == "verify-install":
        run_verify_install_command(args)
    elif args.command == "package":
        run_package_command(args)
    elif args.command == "bundle-status":
        run_bundle_status_command(args)
    elif args.command == "fixture":
        run_fixture_command(args)
    elif args.command == "audit":
        sys.exit(0 if run_audit(args.task, strict_warnings=args.strict_warnings) else 1)
    elif args.command == "dag":
        handle_dag(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

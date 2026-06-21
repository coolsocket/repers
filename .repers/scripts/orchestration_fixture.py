import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


FIXTURE_SCHEMA = "repers.orchestration_fixture.v1"
DEFAULT_TASK = "large-task-fixture"


def task_dir_name(task_name):
    return task_name.lower().replace(" ", "_").replace("-", "_")


def fixture_task_dir(workspace_root, task):
    return Path(workspace_root) / "repers_tasks" / task_dir_name(task)


def create_fixture_plan(workspace_root, task=DEFAULT_TASK, reset=False):
    task_dir = fixture_task_dir(workspace_root, task)
    if reset and task_dir.exists():
        shutil.rmtree(task_dir)
    task_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir = task_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    shared = (task_dir / "outputs" / "shared-log.jsonl").as_posix()
    hook = (task_dir / "outputs" / "hook.json").as_posix()
    join = (task_dir / "outputs" / "join.json").as_posix()
    plan = f"""# RePERS Plan: {task}

## Metadata
* **Task ID**: {task}
* **Priority**: High
* **Target Files**: {shared}, {hook}, {join}
* **Dependencies**: None

## Research Summary
* Deterministic fixture for proving conflict-safe parallel worker dispatch,
  worker-command execution, and a local join verification step.

## Step-by-Step Execution Roadmap
1. **Step 1: Research lane writes shared artifact**
   * **Action**: Worker writes a research lane record to the shared fixture log.
   * **Target File**: {shared}
   * **Verification Command**:
   * **Expected Outcome**: Worker result and shared log record exist for step 1.
   * **Depends On**: None
   * **Status**: Pending

2. **Step 2: Package lane writes shared artifact**
   * **Action**: Worker writes a package lane record to the shared fixture log.
   * **Target File**: {shared}
   * **Verification Command**:
   * **Expected Outcome**: Worker result and shared log record exist for step 2.
   * **Depends On**: None
   * **Status**: Pending

3. **Step 3: Hook lane writes independent artifact**
   * **Action**: Worker writes a hook lane record to an independent fixture file.
   * **Target File**: {hook}
   * **Verification Command**:
   * **Expected Outcome**: Worker result and hook artifact exist for step 3.
   * **Depends On**: None
   * **Status**: Pending

4. **Step 4: Join and verify worker evidence**
   * **Action**: Verify dispatch batches, worker outputs, result contracts, and join evidence.
   * **Target File**: {join}
   * **Verification Command**: {sys.executable} {Path(__file__).resolve()} assert --task {task} --workspace {Path(workspace_root).resolve()}
   * **Expected Outcome**: Join artifact records fixture_ok=true.
   * **Depends On**: Step 1, Step 2, Step 3
   * **Status**: Pending

## Risk & Pitfalls Mitigation
* **Risk**: A future dispatcher may place conflicting target files in one batch.
* **Mitigation**: The join assertion fails if steps 1 and 2 share a batch.

## Definition of Done
* [ ] Worker-command steps complete.
* [ ] Join step completes.
* [ ] Review passes.
"""
    plan_path = task_dir / "plan.md"
    plan_path.write_text(plan, encoding="utf-8")
    return {
        "task": task,
        "task_dir": str(task_dir.resolve()),
        "plan_md": str(plan_path.resolve()),
    }


def worker_record_from_env():
    task_dir = Path(os.environ["REPERS_TASK_DIR"]).resolve()
    step_id = os.environ["REPERS_STEP_ID"]
    worker_id = os.environ["REPERS_WORKER_ID"]
    prompt_path = os.environ["REPERS_PROMPT_PATH"]
    outputs = task_dir / "outputs"
    outputs.mkdir(exist_ok=True)
    record = {
        "schema": "repers.fixture_worker_record.v1",
        "step_id": step_id,
        "worker_id": worker_id,
        "prompt_path": prompt_path,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if step_id in {"1", "2"}:
        with (outputs / "shared-log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    elif step_id == "3":
        (outputs / "hook.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        raise ValueError(f"unexpected fixture worker step: {step_id}")
    return record


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assert_fixture(workspace_root, task=DEFAULT_TASK):
    task_dir = fixture_task_dir(workspace_root, task)
    dispatch_path = task_dir / "dispatch" / "manifest.json"
    results_dir = task_dir / "results"
    outputs = task_dir / "outputs"
    errors = []
    manifest = load_json(dispatch_path) if dispatch_path.exists() else None
    if not manifest:
        errors.append("missing dispatch manifest")
    else:
        if manifest.get("schema") != "repers.dispatch.v1":
            errors.append("dispatch manifest schema mismatch")
        if manifest.get("ready_count") != 3:
            errors.append(f"expected three ready workers, got {manifest.get('ready_count')}")
        for batch in manifest.get("batches", []):
            batch_workers = set(batch.get("workers", []))
            step_ids = {
                str(worker.get("step_id"))
                for worker in manifest.get("workers", [])
                if worker.get("worker_id") in batch_workers
            }
            if {"1", "2"} <= step_ids:
                errors.append("conflicting shared-target steps 1 and 2 were dispatched in the same batch")

    result_status = {}
    for step_id in ["1", "2", "3"]:
        path = results_dir / f"{step_id}.json"
        if not path.exists():
            errors.append(f"missing worker result for step {step_id}")
            continue
        result = load_json(path)
        result_status[step_id] = result.get("status")
        if result.get("schema") != "repers.step_result.v1":
            errors.append(f"step {step_id} result schema mismatch")
        if result.get("status") != "completed":
            errors.append(f"step {step_id} did not complete")
        if not result.get("worker_id") or not result.get("prompt_path"):
            errors.append(f"step {step_id} result lacks worker metadata")

    shared_records = []
    shared_path = outputs / "shared-log.jsonl"
    if shared_path.exists():
        shared_records = [json.loads(line) for line in shared_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        errors.append("missing shared log output")
    shared_steps = {record.get("step_id") for record in shared_records}
    if not {"1", "2"} <= shared_steps:
        errors.append("shared log does not contain records for steps 1 and 2")
    hook_path = outputs / "hook.json"
    if not hook_path.exists():
        errors.append("missing hook output")
    else:
        hook = load_json(hook_path)
        if hook.get("step_id") != "3":
            errors.append("hook output does not belong to step 3")

    report = {
        "schema": "repers.fixture_join.v1",
        "fixture_ok": not errors,
        "task": task,
        "task_dir": str(task_dir.resolve()),
        "dispatch_manifest": str(dispatch_path.resolve()),
        "batch_count": manifest.get("batch_count") if manifest else 0,
        "worker_count": len(manifest.get("workers", [])) if manifest else 0,
        "result_status": result_status,
        "shared_record_count": len(shared_records),
        "errors": errors,
    }
    join_path = outputs / "join.json"
    join_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if errors:
        raise AssertionError("; ".join(errors))
    return report


def prove_fixture(workspace_root, install_root, task=DEFAULT_TASK, max_workers=3, reset=True):
    sys.path.append(str(Path(install_root) / "scripts"))
    from plan_runner import build_plan_json, dry_run, run_local_ready, run_worker_command_ready
    from reviewer import review_task

    created = create_fixture_plan(workspace_root, task=task, reset=reset)
    task_dir = Path(created["task_dir"])
    plan, _ = build_plan_json(task, task_dir, task_dir / "plan.md")
    initial_dry_run = dry_run(plan)
    command_template = f'"{sys.executable}" "{Path(__file__).resolve()}" worker --json'
    worker_run = run_worker_command_ready(
        plan,
        workspace_root,
        task_dir,
        command_template,
        max_workers=max_workers,
        update_markdown=True,
    )
    plan_after_workers, _ = build_plan_json(task, task_dir, task_dir / "plan.md")
    join_dry_run = dry_run(plan_after_workers)
    local_run = run_local_ready(
        plan_after_workers,
        workspace_root,
        task_dir,
        max_workers=1,
        update_markdown=True,
    )
    review = review_task(task_dir, update_status=True)
    join = load_json(task_dir / "outputs" / "join.json")
    manifest = load_json(task_dir / "dispatch" / "manifest.json")
    ok = (
        initial_dry_run.get("ready_count") == 3
        and manifest.get("ready_count") == 3
        and manifest.get("batch_count") == 2
        and sorted(worker_run.get("completed", [])) == ["1", "2", "3"]
        and worker_run.get("failed", []) == []
        and local_run.get("completed") == ["4"]
        and local_run.get("failed") == []
        and join.get("fixture_ok") is True
        and review.get("ok") is True
    )
    return {
        "schema": FIXTURE_SCHEMA,
        "ok": ok,
        "task": task,
        "created": created,
        "initial_dry_run": initial_dry_run,
        "dispatch": manifest,
        "worker_run": worker_run,
        "join_dry_run": join_dry_run,
        "local_run": local_run,
        "join": join,
        "review": review,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="RePERS deterministic orchestration fixture")
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--task", default=DEFAULT_TASK)
    create.add_argument("--workspace", default=os.getcwd())
    create.add_argument("--reset", action="store_true")
    create.add_argument("--json", action="store_true")
    worker = subparsers.add_parser("worker")
    worker.add_argument("--json", action="store_true")
    assert_cmd = subparsers.add_parser("assert")
    assert_cmd.add_argument("--task", default=DEFAULT_TASK)
    assert_cmd.add_argument("--workspace", default=os.getcwd())
    assert_cmd.add_argument("--json", action="store_true")
    prove = subparsers.add_parser("prove")
    prove.add_argument("--task", default=DEFAULT_TASK)
    prove.add_argument("--workspace", default=os.getcwd())
    prove.add_argument("--install-root", default=str(Path(__file__).resolve().parents[1]))
    prove.add_argument("--max-workers", type=int, default=3)
    prove.add_argument("--no-reset", action="store_true")
    prove.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.action == "create":
        result = create_fixture_plan(args.workspace, task=args.task, reset=args.reset)
    elif args.action == "worker":
        result = worker_record_from_env()
    elif args.action == "assert":
        result = assert_fixture(args.workspace, task=args.task)
    elif args.action == "prove":
        result = prove_fixture(
            args.workspace,
            args.install_root,
            task=args.task,
            max_workers=args.max_workers,
            reset=not args.no_reset,
        )
    else:
        raise ValueError(args.action)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())

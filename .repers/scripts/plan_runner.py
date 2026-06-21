import concurrent.futures
import contextlib
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import TypedDict

from dag_engine import DAGEngine


def clean_field(value):
    value = (value or "").strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        return value[1:-1]
    return value


def load_research(task_dir):
    research_path = Path(task_dir) / "research.json"
    if not research_path.exists():
        return None
    return json.loads(research_path.read_text(encoding="utf-8"))


def shell_quote(value):
    if os.name == "nt":
        return json.dumps(value)
    return shlex.quote(value)


def workspace_evidence_paths(research, limit=6):
    paths = []
    for result in (research or {}).get("results", []):
        if result.get("source") != "workspace":
            continue
        path = result.get("path")
        if not path or path in paths:
            continue
        paths.append(path)
        if len(paths) >= limit:
            break
    return paths


def proposal_steps(task, research, objective="", max_steps=6):
    query = research.get("query", objective or task)
    evidence_paths = workspace_evidence_paths(research)
    target_files = [path for path in evidence_paths if path.startswith("scripts/") or path.startswith("docs/") or path.startswith("tests/")]
    if not target_files:
        target_files = ["scripts/repers.py", "tests/smoke_repers.py"]

    steps = [
        {
            "id": "1",
            "title": "Review Preflight Evidence",
            "action": "Use the structured research artifact to decide whether to reuse, extend, promote, or create.",
            "target_files": ["repers_tasks/{}/research.json".format(task.lower().replace(" ", "_").replace("-", "_"))],
            "verification_command": f"python scripts/repers.py preflight --query {shell_quote(query)} --json",
            "expected_outcome": "Preflight returns structured evidence and a recommendation.",
            "depends_on": [],
            "status": "Pending",
            "mode": "local",
        },
        {
            "id": "2",
            "title": "Update Relevant Capability",
            "action": "Apply the smallest implementation change that follows the research recommendation.",
            "target_files": target_files[:4],
            "verification_command": "",
            "expected_outcome": "The targeted capability is updated without duplicating an existing workflow.",
            "depends_on": ["1"],
            "status": "Pending",
            "mode": "subagent",
        },
        {
            "id": "3",
            "title": "Add Focused Smoke Coverage",
            "action": "Cover the new behavior with the repository smoke harness.",
            "target_files": ["tests/smoke_repers.py"],
            "verification_command": "python tests/smoke_repers.py",
            "expected_outcome": "Smoke tests pass and exercise the new behavior.",
            "depends_on": ["2"],
            "status": "Pending",
            "mode": "local",
        },
        {
            "id": "4",
            "title": "Refresh Machine Artifacts",
            "action": "Regenerate machine-readable RePERS artifacts after the implementation changes.",
            "target_files": [f"repers_tasks/{task.lower().replace(' ', '_').replace('-', '_')}/plan.json"],
            "verification_command": f"python scripts/repers.py plan --task {shell_quote(task)} --json",
            "expected_outcome": "plan.json reflects the current human-readable plan.",
            "depends_on": ["3"],
            "status": "Pending",
            "mode": "local",
        },
        {
            "id": "5",
            "title": "Run Readiness Gates",
            "action": "Run runtime and shipping checks before publishing the updated bundle.",
            "target_files": ["repers_tasks/{}/review.md".format(task.lower().replace(" ", "_").replace("-", "_"))],
            "verification_command": f"python scripts/repers.py audit --task {shell_quote(task)}",
            "expected_outcome": "Audit reports no errors; any warnings are recorded.",
            "depends_on": ["4"],
            "status": "Pending",
            "mode": "local",
        },
    ]
    return steps[:max(1, max_steps)]


def build_plan_proposal(task, task_dir, objective="", max_steps=6):
    research = load_research(task_dir)
    if not research:
        raise FileNotFoundError(f"research.json not found in {task_dir}")

    steps = proposal_steps(task, research, objective=objective, max_steps=max_steps)
    proposal = {
        "schema": "repers.plan_proposal.v1",
        "task": task,
        "task_dir": str(Path(task_dir).resolve()),
        "objective": objective,
        "research_json": str((Path(task_dir) / "research.json").resolve()),
        "research_query": research.get("query"),
        "recommendation": research.get("recommendation"),
        "evidence_refs": [
            f"{result.get('source')}:{result.get('kind')}:{result.get('path')}"
            for result in research.get("results", [])[:10]
        ],
        "steps": steps,
    }
    task_path = Path(task_dir)
    json_path = task_path / "plan.proposed.json"
    md_path = task_path / "plan.proposed.md"
    json_path.write_text(json.dumps(proposal, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_plan_proposal_md(proposal), encoding="utf-8")
    return proposal, json_path, md_path


def render_plan_proposal_md(proposal):
    lines = [
        f"# RePERS Proposed Plan: {proposal['task']}",
        "",
        "## Source",
        f"* **Research JSON**: `{proposal['research_json']}`",
        f"* **Research Query**: `{proposal.get('research_query') or ''}`",
        f"* **Decision**: {proposal.get('recommendation', {}).get('decision', '')}",
        f"* **Reason**: {proposal.get('recommendation', {}).get('reason', '')}",
        "",
        "## Evidence",
    ]
    for ref in proposal.get("evidence_refs", [])[:10]:
        lines.append(f"* `{ref}`")
    lines.extend(["", "## Step-by-Step Execution Roadmap"])
    for step in proposal["steps"]:
        depends_on = ", ".join(f"Step {dep}" for dep in step["depends_on"]) if step["depends_on"] else "None"
        target_files = ", ".join(f"`{path}`" for path in step["target_files"]) if step["target_files"] else ""
        lines.extend(
            [
                f"{step['id']}. **Step {step['id']}: {step['title']}**",
                f"   * **Action**: {step['action']}",
                f"   * **Target File**: {target_files}",
                f"   * **Verification Command**: `{step['verification_command']}`" if step["verification_command"] else "   * **Verification Command**: Manual review",
                f"   * **Expected Outcome**: {step['expected_outcome']}",
                f"   * **Depends On**: {depends_on}",
                f"   * **Status**: {step['status']}",
                "",
            ]
        )
    return "\n".join(lines)


def build_plan_json(task, task_dir, plan_path):
    engine = DAGEngine(plan_path)
    research = load_research(task_dir)
    steps = []
    for step in engine.get_all_steps().values():
        steps.append(
            {
                "id": step["id"],
                "title": step["title"],
                "action": clean_field(step["action"]),
                "target_files": parse_target_files(step["target_file"]),
                "verification_command": clean_field(step["verification_command"]),
                "expected_outcome": clean_field(step["expected_outcome"]),
                "depends_on": step["depends_on"],
                "status": step["status"],
                "mode": infer_mode(step),
                "artifact_contract": "step_result_v1",
            }
        )
    plan = {
        "schema": "repers.plan.v1",
        "task": task,
        "task_dir": str(Path(task_dir).resolve()),
        "plan_md": str(Path(plan_path).resolve()),
        "research_json": str((Path(task_dir) / "research.json").resolve()) if research else None,
        "research_recommendation": research.get("recommendation") if research else None,
        "steps": steps,
    }
    output_path = Path(task_dir) / "plan.json"
    output_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return plan, output_path


def parse_target_files(value):
    value = clean_field(value)
    if not value:
        return []
    return [part.strip().strip("`") for part in value.split(",") if part.strip()]


def infer_mode(step):
    command = clean_field(step.get("verification_command", ""))
    action = (step.get("action") or "").lower()
    if command:
        return "local"
    if "manual" in action:
        return "manual"
    return "subagent"


def load_plan_json(task_dir):
    path = Path(task_dir) / "plan.json"
    if not path.exists():
        raise FileNotFoundError(f"plan.json not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def ready_steps(plan):
    by_id = {step["id"]: step for step in plan["steps"]}
    ready = []
    for step in plan["steps"]:
        if step["status"] != "Pending":
            continue
        if all(by_id[dep]["status"] == "Completed" for dep in step["depends_on"]):
            ready.append(step)
    return ready


def partition_conflict_batches(steps):
    batches = []
    for step in steps:
        targets = set(step.get("target_files") or [])
        placed = False
        for batch in batches:
            batch_targets = set()
            for existing in batch:
                batch_targets.update(existing.get("target_files") or [])
            if not targets or not batch_targets.intersection(targets):
                batch.append(step)
                placed = True
                break
        if not placed:
            batches.append([step])
    return batches


def split_batches_by_limit(batches, max_workers):
    limited = []
    worker_limit = max(1, max_workers)
    for batch in batches:
        for start in range(0, len(batch), worker_limit):
            limited.append(batch[start : start + worker_limit])
    return limited


def dry_run(plan):
    ready = ready_steps(plan)
    batches = partition_conflict_batches(ready)
    return {
        "schema": "repers.run_plan.v1",
        "task": plan["task"],
        "ready_count": len(ready),
        "batches": [
            {
                "batch": index + 1,
                "steps": [
                    {
                        "id": step["id"],
                        "title": step["title"],
                        "mode": step["mode"],
                        "target_files": step["target_files"],
                        "verification_command": step["verification_command"],
                    }
                    for step in batch
                ],
            }
            for index, batch in enumerate(batches)
        ],
    }


def dispatch_ready(plan, task_dir, backend="codex", max_workers=4):
    ready = [
        step
        for step in ready_steps(plan)
        if step.get("mode") in {"subagent", "manual"} or not step.get("verification_command")
    ]
    batches = split_batches_by_limit(partition_conflict_batches(ready), max_workers)
    dispatch_dir = Path(task_dir) / "dispatch"
    prompts_dir = dispatch_dir / "workers"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    workers = []
    for batch_index, batch in enumerate(batches, 1):
        for worker_index, step in enumerate(batch, 1):
            worker_id = f"batch{batch_index}-step{step['id']}"
            prompt = render_worker_prompt(plan, step, worker_id)
            prompt_path = prompts_dir / f"{worker_id}.md"
            prompt_path.write_text(prompt, encoding="utf-8")
            workers.append(
                {
                    "worker_id": worker_id,
                    "batch": batch_index,
                    "slot": worker_index,
                    "backend": backend,
                    "step_id": step["id"],
                    "title": step["title"],
                    "mode": step.get("mode", "subagent"),
                    "target_files": step.get("target_files", []),
                    "depends_on": step.get("depends_on", []),
                    "verification_command": step.get("verification_command", ""),
                    "prompt_path": str(prompt_path.resolve()),
                }
            )

    manifest = {
        "schema": "repers.dispatch.v1",
        "task": plan["task"],
        "task_dir": plan["task_dir"],
        "plan_json": str((Path(task_dir) / "plan.json").resolve()),
        "plan_md": plan.get("plan_md"),
        "backend": backend,
        "max_workers": max_workers,
        "ready_count": len(ready),
        "batch_count": len(batches),
        "workers": workers,
        "batches": [
            {
                "batch": index + 1,
                "workers": [worker["worker_id"] for worker in workers if worker["batch"] == index + 1],
            }
            for index in range(len(batches))
        ],
    }
    manifest_path = dispatch_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest, manifest_path


def render_worker_prompt(plan, step, worker_id):
    allowed = step.get("target_files") or []
    allowed_text = "\n".join(f"- {path}" for path in allowed) if allowed else "- No file edits until the supervisor narrows ownership."
    forbidden_text = "\n".join(
        [
            "- Do not edit files outside the allowed ownership list.",
            "- Do not revert unrelated changes.",
            "- Do not spawn additional subagents.",
            "- Do not perform destructive git operations.",
        ]
    )
    verification = step.get("verification_command") or "Return implementation evidence; supervisor will run integration gates."
    return "\n".join(
        [
            f"# RePERS Worker Prompt: {worker_id}",
            "",
            f"You are working in workspace: {plan.get('task_dir')}",
            "",
            "## Task",
            f"{step['title']}",
            "",
            "## Goal",
            step.get("action") or "Complete the assigned RePERS plan step.",
            "",
            "## Ownership",
            "You may edit:",
            allowed_text,
            "",
            "Do not edit:",
            forbidden_text,
            "",
            "## Dependencies",
            ", ".join(f"Step {dep}" for dep in step.get("depends_on", [])) or "None",
            "",
            "## Acceptance Criteria",
            step.get("expected_outcome") or "Return a narrow, reviewable result.",
            "",
            "## Verification",
            verification,
            "",
            "## Return Format",
            "- status",
            "- files changed",
            "- tests run",
            "- failures",
            "- risks",
            "- follow-up",
            "",
        ]
    )


def run_local_ready(plan, workspace_root, task_dir, max_workers=4, update_markdown=True):
    ready = [step for step in ready_steps(plan) if step["mode"] == "local" and step["verification_command"]]
    batches = partition_conflict_batches(ready)
    results = []
    for batch in batches:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(run_step_command, step, workspace_root, task_dir) for step in batch]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
    if update_markdown and results:
        update_completed_steps(plan["plan_md"], results)
    return {
        "schema": "repers.run_result.v1",
        "task": plan["task"],
        "results": results,
        "completed": [r["step_id"] for r in results if r["status"] == "completed"],
        "failed": [r["step_id"] for r in results if r["status"] == "failed"],
    }


def run_worker_command_ready(plan, workspace_root, task_dir, command_template, max_workers=4, update_markdown=True):
    if not command_template:
        raise ValueError("worker-command backend requires a command template")
    manifest, _ = dispatch_ready(plan, task_dir, backend="worker-command", max_workers=max_workers)
    results = []
    workers_by_id = {worker["worker_id"]: worker for worker in manifest["workers"]}
    for batch in manifest["batches"]:
        batch_workers = [workers_by_id[worker_id] for worker_id in batch["workers"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(run_worker_command, worker, workspace_root, task_dir, command_template)
                for worker in batch_workers
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    if update_markdown and results:
        update_completed_steps(plan["plan_md"], results)
    return {
        "schema": "repers.run_result.v1",
        "task": plan["task"],
        "backend": "worker-command",
        "dispatch_manifest": str((Path(task_dir) / "dispatch" / "manifest.json").resolve()),
        "results": results,
        "completed": [r["step_id"] for r in results if r["status"] == "completed"],
        "failed": [r["step_id"] for r in results if r["status"] == "failed"],
    }


def run_openai_agents_ready(plan, workspace_root, task_dir, max_workers=4, update_markdown=True):
    manifest, _ = dispatch_ready(plan, task_dir, backend="openai-agents", max_workers=max_workers)
    results = []
    workers_by_id = {worker["worker_id"]: worker for worker in manifest["workers"]}
    for batch in manifest["batches"]:
        batch_workers = [workers_by_id[worker_id] for worker_id in batch["workers"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(run_openai_agents_worker, worker, workspace_root, task_dir)
                for worker in batch_workers
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    if update_markdown and results:
        update_completed_steps(plan["plan_md"], results)
    return {
        "schema": "repers.run_result.v1",
        "task": plan["task"],
        "backend": "openai-agents",
        "dispatch_manifest": str((Path(task_dir) / "dispatch" / "manifest.json").resolve()),
        "results": results,
        "completed": [r["step_id"] for r in results if r["status"] == "completed"],
        "failed": [r["step_id"] for r in results if r["status"] == "failed"],
    }


class LangGraphBatchState(TypedDict):
    workers: list
    results: list


def run_langgraph_ready(plan, workspace_root, task_dir, max_workers=4, update_markdown=True):
    command_template = os.environ.get("REPERS_LANGGRAPH_WORKER_COMMAND") or os.environ.get("REPERS_WORKER_COMMAND", "")
    if not command_template:
        raise ValueError("langgraph backend requires REPERS_LANGGRAPH_WORKER_COMMAND or REPERS_WORKER_COMMAND")

    from langgraph.graph import END, START, StateGraph

    checkpoint_mode = os.environ.get("REPERS_LANGGRAPH_CHECKPOINT", "none").strip().lower() or "none"
    thread_id = os.environ.get("REPERS_LANGGRAPH_THREAD_ID", "").strip()
    checkpoint_path = None
    checkpointer = None
    if checkpoint_mode not in {"none", "memory", "sqlite"}:
        raise ValueError("REPERS_LANGGRAPH_CHECKPOINT must be one of: none, memory, sqlite")

    manifest, _ = dispatch_ready(plan, task_dir, backend="langgraph", max_workers=max_workers)
    all_results = []

    def run_batch(state):
        workers = state["workers"]
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(run_langgraph_worker_command, worker, workspace_root, task_dir, command_template)
                for worker in workers
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        return {"workers": workers, "results": results}

    with contextlib.ExitStack() as checkpoint_stack:
        if checkpoint_mode == "memory":
            try:
                from langgraph.checkpoint.memory import InMemorySaver
            except ImportError:
                from langgraph.checkpoint.memory import MemorySaver as InMemorySaver

            checkpointer = InMemorySaver()
        elif checkpoint_mode == "sqlite":
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver
            except ImportError as exc:
                raise ValueError(
                    "REPERS_LANGGRAPH_CHECKPOINT=sqlite requires the optional "
                    "langgraph-checkpoint-sqlite package"
                ) from exc

            checkpoint_path = os.environ.get("REPERS_LANGGRAPH_CHECKPOINT_PATH", "").strip()
            if not checkpoint_path:
                checkpoint_path = str(Path(task_dir) / "langgraph-checkpoints.sqlite")
            checkpoint_path = str(Path(checkpoint_path).expanduser().resolve())
            Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
            if hasattr(SqliteSaver, "from_conn_string"):
                saver = SqliteSaver.from_conn_string(checkpoint_path)
                if hasattr(saver, "__enter__"):
                    checkpointer = checkpoint_stack.enter_context(saver)
                else:
                    checkpointer = saver
            else:
                import sqlite3

                connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
                checkpoint_stack.callback(connection.close)
                checkpointer = SqliteSaver(connection)
            if hasattr(checkpointer, "setup"):
                checkpointer.setup()

        if checkpointer and not thread_id:
            thread_id = f"repers-{plan['task']}"

        graph_builder = StateGraph(LangGraphBatchState)
        graph_builder.add_node("run_batch", run_batch)
        graph_builder.add_edge(START, "run_batch")
        graph_builder.add_edge("run_batch", END)
        if checkpointer:
            graph = graph_builder.compile(checkpointer=checkpointer)
        else:
            graph = graph_builder.compile()

        workers_by_id = {worker["worker_id"]: worker for worker in manifest["workers"]}
        for batch in manifest["batches"]:
            batch_workers = [workers_by_id[worker_id] for worker_id in batch["workers"]]
            state_input = {"workers": batch_workers, "results": []}
            if checkpointer:
                state = graph.invoke(state_input, {"configurable": {"thread_id": thread_id}})
            else:
                state = graph.invoke(state_input)
            all_results.extend(state.get("results", []))

    if update_markdown and all_results:
        update_completed_steps(plan["plan_md"], all_results)
    return {
        "schema": "repers.run_result.v1",
        "task": plan["task"],
        "backend": "langgraph",
        "dispatch_manifest": str((Path(task_dir) / "dispatch" / "manifest.json").resolve()),
        "checkpoint_mode": checkpoint_mode,
        "thread_id": thread_id if checkpointer else None,
        "checkpoint_path": checkpoint_path,
        "results": all_results,
        "completed": [r["step_id"] for r in all_results if r["status"] == "completed"],
        "failed": [r["step_id"] for r in all_results if r["status"] == "failed"],
    }


def run_langgraph_worker_command(worker, workspace_root, task_dir, command_template):
    result = run_worker_command(worker, workspace_root, task_dir, command_template)
    result["backend"] = "langgraph"
    result["command"] = f"langgraph:{result['command']}"
    result_path = Path(result["result_path"])
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def run_openai_agents_worker(worker, workspace_root, task_dir):
    start = time.time()
    prompt = Path(worker["prompt_path"]).read_text(encoding="utf-8")
    model = os.environ.get("REPERS_OPENAI_AGENT_MODEL")
    max_turns = int(os.environ.get("REPERS_OPENAI_AGENT_MAX_TURNS", "8"))
    command = f"openai-agents:Runner.run_sync({worker['worker_id']})"
    tool_mode = os.environ.get("REPERS_OPENAI_AGENT_TOOLS", "readonly").strip().lower() or "readonly"
    try:
        from agents import Agent, Runner, function_tool

        agent_kwargs = {
            "name": f"RePERS {worker['worker_id']}",
            "instructions": (
                "You are a RePERS worker. Follow the prompt exactly, preserve the stated "
                "ownership boundaries, and return concise implementation evidence. Use tools "
                "only when they are necessary and respect each tool's safety boundary."
            ),
        }
        if model:
            agent_kwargs["model"] = model
        tools = build_openai_agent_tools(function_tool, workspace_root, worker, tool_mode)
        if tools:
            agent_kwargs["tools"] = tools
        agent = Agent(**agent_kwargs)
        output = Runner.run_sync(agent, prompt, max_turns=max_turns)
        final_output = getattr(output, "final_output", str(output))
        returncode = 0
        stderr_tail = ""
    except Exception as exc:
        final_output = ""
        returncode = 1
        stderr_tail = str(exc)

    status = "completed" if returncode == 0 else "failed"
    result = {
        "schema": "repers.step_result.v1",
        "step_id": worker["step_id"],
        "title": worker["title"],
        "status": status,
        "command": command,
        "returncode": returncode,
        "duration_seconds": round(time.time() - start, 3),
        "stdout_tail": str(final_output)[-4000:],
        "stderr_tail": stderr_tail[-4000:],
        "target_files": worker.get("target_files", []),
        "worker_id": worker["worker_id"],
        "prompt_path": worker["prompt_path"],
        "backend": "openai-agents",
        "tools_mode": tool_mode,
    }
    results_dir = Path(task_dir) / "results"
    results_dir.mkdir(exist_ok=True)
    result_path = results_dir / f"{worker['step_id']}.json"
    result["result_path"] = str(result_path.resolve())
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def path_is_relative_to(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def safe_workspace_path(workspace_root, worker, path_value, write=False):
    workspace = Path(workspace_root).resolve()
    path = Path(path_value)
    candidate = path.resolve() if path.is_absolute() else (workspace / path).resolve()
    if not path_is_relative_to(candidate, workspace):
        raise ValueError(f"path escapes workspace: {path_value}")
    relative = candidate.relative_to(workspace).as_posix()
    parts = set(relative.split("/"))
    if ".git" in parts or "__pycache__" in parts:
        raise ValueError(f"path is not allowed: {relative}")
    if write:
        targets = {str(item).replace("\\", "/").strip("/") for item in worker.get("target_files", []) if item}
        if not targets:
            raise ValueError("worker has no writable target files")
        if relative not in targets:
            raise ValueError(f"write path is outside worker target files: {relative}")
    return candidate, relative


def build_openai_agent_tools(function_tool, workspace_root, worker, mode):
    if mode not in {"none", "readonly", "workspace"}:
        raise ValueError("REPERS_OPENAI_AGENT_TOOLS must be one of: none, readonly, workspace")
    if mode == "none":
        return []
    workspace = Path(workspace_root).resolve()

    @function_tool
    def repers_list_files(prefix: str = "", limit: int = 50) -> str:
        """List workspace files under prefix, excluding .git and Python cache folders."""
        base, _ = safe_workspace_path(workspace, worker, prefix or ".")
        if base.is_file():
            return base.relative_to(workspace).as_posix()
        if not base.exists():
            return ""
        files = []
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(workspace).as_posix()
            if ".git/" in rel or "__pycache__/" in rel:
                continue
            files.append(rel)
            if len(files) >= max(1, min(int(limit), 200)):
                break
        return "\n".join(files)

    @function_tool
    def repers_read_file(path: str, max_chars: int = 12000) -> str:
        """Read a UTF-8 workspace file within the RePERS worker safety boundary."""
        file_path, _ = safe_workspace_path(workspace, worker, path)
        if not file_path.is_file():
            raise ValueError(f"not a file: {path}")
        return file_path.read_text(encoding="utf-8", errors="replace")[: max(1, min(int(max_chars), 50000))]

    tools = [repers_list_files, repers_read_file]
    if mode != "workspace":
        return tools

    @function_tool
    def repers_write_file(path: str, content: str) -> str:
        """Write a UTF-8 file only when the path is in the worker target file list."""
        file_path, relative = safe_workspace_path(workspace, worker, path, write=True)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"wrote {relative}"

    @function_tool
    def repers_run_command(command: str, timeout_seconds: int = 60) -> str:
        """Run a non-interactive shell command in the workspace and return stdout/stderr tails."""
        blocked = ["git reset", "git checkout --", "rm -rf", "Remove-Item", "del /s"]
        if any(token.lower() in command.lower() for token in blocked):
            raise ValueError("command is blocked by RePERS safety policy")
        proc = subprocess.run(
            command,
            cwd=workspace,
            shell=True,
            capture_output=True,
            text=True,
            timeout=max(1, min(int(timeout_seconds), 300)),
        )
        return json.dumps(
            {
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-4000:],
                "stderr_tail": proc.stderr[-4000:],
            },
            ensure_ascii=False,
        )

    tools.extend([repers_write_file, repers_run_command])
    return tools


def run_worker_command(worker, workspace_root, task_dir, command_template):
    start = time.time()
    command = command_template.format(
        prompt_path=shell_quote(worker["prompt_path"]),
        worker_id=shell_quote(worker["worker_id"]),
        step_id=shell_quote(worker["step_id"]),
        task_dir=shell_quote(str(Path(task_dir).resolve())),
        workspace_root=shell_quote(str(Path(workspace_root).resolve())),
    )
    env = os.environ.copy()
    env.update(
        {
            "REPERS_WORKER_ID": worker["worker_id"],
            "REPERS_STEP_ID": worker["step_id"],
            "REPERS_PROMPT_PATH": worker["prompt_path"],
            "REPERS_TASK_DIR": str(Path(task_dir).resolve()),
            "REPERS_WORKSPACE_ROOT": str(Path(workspace_root).resolve()),
        }
    )
    proc = subprocess.run(command, cwd=workspace_root, shell=True, capture_output=True, text=True, env=env)
    status = "completed" if proc.returncode == 0 else "failed"
    result = {
        "schema": "repers.step_result.v1",
        "step_id": worker["step_id"],
        "title": worker["title"],
        "status": status,
        "command": command,
        "returncode": proc.returncode,
        "duration_seconds": round(time.time() - start, 3),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "target_files": worker.get("target_files", []),
        "worker_id": worker["worker_id"],
        "prompt_path": worker["prompt_path"],
    }
    results_dir = Path(task_dir) / "results"
    results_dir.mkdir(exist_ok=True)
    result_path = results_dir / f"{worker['step_id']}.json"
    result["result_path"] = str(result_path.resolve())
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def run_step_command(step, workspace_root, task_dir):
    start = time.time()
    command = step["verification_command"]
    proc = subprocess.run(command, cwd=workspace_root, shell=True, capture_output=True, text=True)
    status = "completed" if proc.returncode == 0 else "failed"
    result = {
        "schema": "repers.step_result.v1",
        "step_id": step["id"],
        "title": step["title"],
        "status": status,
        "command": command,
        "returncode": proc.returncode,
        "duration_seconds": round(time.time() - start, 3),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "target_files": step.get("target_files", []),
    }
    results_dir = Path(task_dir) / "results"
    results_dir.mkdir(exist_ok=True)
    result_path = results_dir / f"{step['id']}.json"
    result["result_path"] = str(result_path.resolve())
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def update_completed_steps(plan_md, results):
    engine = DAGEngine(plan_md)
    for result in results:
        if result["status"] == "completed":
            engine.update_status(result["step_id"], "Completed", verbose=False)
        elif result["status"] == "failed":
            engine.update_status(result["step_id"], "Failed", verbose=False)

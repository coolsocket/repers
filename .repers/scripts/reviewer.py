import json
from pathlib import Path

from dag_engine import DAGEngine


REQUIRED_RESULT_KEYS = {
    "schema",
    "step_id",
    "title",
    "status",
    "command",
    "returncode",
    "duration_seconds",
    "stdout_tail",
    "stderr_tail",
    "target_files",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def review_result_file(path):
    errors = []
    result = load_json(path)
    missing = sorted(REQUIRED_RESULT_KEYS - set(result))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if result.get("schema") != "repers.step_result.v1":
        errors.append("invalid schema")
    if result.get("status") not in {"completed", "failed"}:
        errors.append("invalid status")
    if result.get("status") == "completed" and result.get("returncode") != 0:
        errors.append("completed result has non-zero returncode")
    if result.get("status") == "failed" and result.get("returncode") == 0:
        errors.append("failed result has zero returncode")
    return {
        "path": str(Path(path).resolve()),
        "step_id": result.get("step_id"),
        "status": result.get("status"),
        "ok": not errors,
        "errors": errors,
    }


def update_plan_statuses(task_path, reviews):
    plan_path = task_path / "plan.md"
    if not plan_path.exists():
        return {"updated": [], "skipped": [], "error": f"plan.md not found: {plan_path}"}

    engine = DAGEngine(plan_path)
    updated = []
    skipped = []
    for review in reviews:
        if not review["ok"]:
            skipped.append({"step_id": review.get("step_id"), "reason": "review_failed"})
            continue
        if review["status"] == "completed":
            engine.update_status(review["step_id"], "Completed", verbose=False)
            updated.append({"step_id": review["step_id"], "status": "Completed"})
        elif review["status"] == "failed":
            engine.update_status(review["step_id"], "Failed", verbose=False)
            updated.append({"step_id": review["step_id"], "status": "Failed"})

    # Keep plan.json in sync with the freshly-updated plan.md so that the
    # next `run`/`dispatch --use-existing-plan` reads the updated statuses
    # instead of stale Pending values.
    plan_json_refresh = {"refreshed": False, "error": None}
    plan_json_path = task_path / "plan.json"
    if updated and plan_json_path.exists():
        try:
            existing = json.loads(plan_json_path.read_text(encoding="utf-8"))
            task_name = existing.get("task") or task_path.name
        except Exception as exc:  # pragma: no cover — defensive
            task_name = task_path.name
            plan_json_refresh["error"] = f"could not read existing plan.json: {exc}"
        try:
            from plan_runner import build_plan_json
            build_plan_json(task_name, str(task_path), str(plan_path))
            plan_json_refresh["refreshed"] = True
        except Exception as exc:  # pragma: no cover — defensive
            plan_json_refresh["error"] = f"build_plan_json failed: {exc}"

    return {
        "updated": updated,
        "skipped": skipped,
        "error": None,
        "plan_json_refresh": plan_json_refresh,
    }


def review_task(task_dir, update_status=False):
    task_path = Path(task_dir)
    results_dir = task_path / "results"
    result_files = sorted(results_dir.glob("*.json")) if results_dir.exists() else []
    reviews = [review_result_file(path) for path in result_files]
    summary = {
        "schema": "repers.review.v1",
        "task_dir": str(task_path.resolve()),
        "results_dir": str(results_dir.resolve()),
        "result_count": len(reviews),
        "ok_count": sum(1 for review in reviews if review["ok"]),
        "failed_count": sum(1 for review in reviews if not review["ok"]),
        "ok": bool(reviews) and all(review["ok"] for review in reviews),
        "results": reviews,
    }
    if update_status:
        summary["status_update"] = update_plan_statuses(task_path, reviews)
    output_path = task_path / "review.json"
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary

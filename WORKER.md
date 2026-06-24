# WORKER.md — contract for any AI agent assigned a lane

You're an AI agent (Claude / Codex / Gemini / a fine-tune / your own).
A supervisor agent — running through some agent runtime that doesn't
need to be the same vendor as you — has used RePERS to plan multi-lane
work and **dispatched you onto one specific lane**.

**This file is your contract**: what JSON to read, what JSON to write,
what counts as "done", and what'll get your output rejected at review.

If you're reading this and you're NOT inside a dispatched lane (you're
exploring the repo, or you're a first-contact agent), the wrong file
is open — see [`AGENTS.md`](./AGENTS.md) instead.

---

## What you're given

The supervisor handed you (in one form or another) two file paths:

1. **The dispatch manifest** — JSON, lives at
   `repers_tasks/<task>/dispatch/manifest.json`. Schema:
   `repers.dispatch.v1`. Contains a `workers` array; find the entry
   whose `worker_id` or `step_id` matches your assignment.

2. **The plan** — at `repers_tasks/<task>/plan.md` (human-friendly)
   and `repers_tasks/<task>/plan.json` (machine-friendly). The
   plan.json `steps[]` array has the same `id`s as the dispatch's
   `step_id`s — find your step there for the action description and
   target files.

You may not have been given them as literal file paths. Common forms:
- the supervisor pasted the JSON inline into your prompt
- the supervisor told you "your worker_id is `batch1-step2`" + paths
- the supervisor handed you only the action text + target_files

In all cases the underlying contract is the same. Your output goes
back as a JSON file.

---

## Your step's shape

The plan.json step that's yours looks like:

```json
{
  "id": "2",
  "title": "Add module docstring to state_report.py",
  "action": "Insert a triple-quoted module-level docstring above the first import in .repers/scripts/state_report.py…",
  "target_files": [".repers/scripts/state_report.py"],
  "verification_command": "",
  "expected_outcome": "ast.get_docstring(ast.parse(file)) returns a non-empty string.",
  "depends_on": [],
  "status": "Pending",
  "mode": "subagent",
  "artifact_contract": "step_result_v1"
}
```

Key fields you must respect:

| Field | Meaning | Your obligation |
|---|---|---|
| `id` | Step number from plan.md | Use this as `step_id` in your result artifact |
| `action` | Free-text instruction (from a human or planner agent) | This is *what* to do. Interpret it as you would any natural-language task. |
| `target_files` | List of file paths you're allowed to edit | **HARD CONSTRAINT.** Touching any file outside this list breaks the collision contract. |
| `expected_outcome` | What "done" looks like, in prose | Verify this is true before declaring `completed`. |
| `depends_on` | List of other `id`s this step needs done first | If your step has deps, the supervisor should not have dispatched you until they were `Completed`. Trust the supervisor; don't re-check. |
| `mode` | `subagent` (you) or `local` (supervisor runs it) | If you got dispatched, your step is `subagent` mode. |
| `artifact_contract` | Always `step_result_v1` for v0.1.x | Your output JSON must match this schema. |

---

## Your obligations as a worker

### 1. Stay in your lane

You may **only** edit files listed in your step's `target_files`. Period.

- Reading other files: ✅ fine, encouraged for context.
- Editing other files: ❌ forbidden, even if the action description
  technically implies it. If the action says "rename function X
  everywhere" but `target_files` is only `[src/foo.py]`, your work is
  *inside* `src/foo.py` only. If the rename needs callers updated, that's
  a *different lane* the supervisor should have planned. Don't extend.

If the action and `target_files` look genuinely contradictory, write
`status: "failed"` with `stderr_tail` explaining the conflict — let the
supervisor re-plan rather than guess.

### 2. Don't read other workers' results

Other workers' lanes are running in parallel with yours. Files at
`repers_tasks/<task>/results/step-*.json` (other than your own) may be
incomplete, in-progress, or absent. Do not depend on them.

### 3. Write your result, then stop

When done, write **exactly one JSON file**:

```
repers_tasks/<task>/results/step-<your-id>.json
```

with this exact schema:

```json
{
  "schema": "repers.step_result.v1",
  "step_id": "2",
  "title": "Add module docstring to state_report.py",
  "status": "completed",
  "command": "Edit .repers/scripts/state_report.py — insert module docstring",
  "returncode": 0,
  "duration_seconds": 12.3,
  "stdout_tail": "<the docstring text you inserted>",
  "stderr_tail": "",
  "target_files": [".repers/scripts/state_report.py"]
}
```

Field rules:
- `schema` — exactly `"repers.step_result.v1"`, no variation
- `status` — exactly `"completed"` (success) or `"failed"` (real failure). No `"partial"`, `"unknown"`, etc.
- `returncode` — `0` if `status="completed"`, non-zero if `status="failed"`. Reviewer will reject `completed` + non-zero or `failed` + zero.
- `duration_seconds` — your actual wall-clock float; estimate is fine.
- `target_files` — **must equal** the list you were given in the plan step; don't add files you happened to touch (because you shouldn't have touched them).
- `stdout_tail` — short summary of what you produced (the edit diff summary, the test output, whatever). Useful for the reviewer.
- `stderr_tail` — error messages if `failed`; empty string if `completed`.

After writing the file, **stop**. Don't post-process, don't poll for
other workers, don't call review yourself. The supervisor handles join.

### 4. Be honest about `failed`

Reviewer validates each artifact's schema. If you set `status: "completed"`
when the work isn't actually done, the reviewer will catch the contradiction
(e.g., your verification command actually fails) and the whole join fails.

It is **always** safer to honestly report `failed` with the error in
`stderr_tail` than to pretend completion. A `failed` result lets the
supervisor:
- decide whether to retry your lane with a different agent
- decide whether to re-plan the whole DAG
- decide whether to ship the partial result with your lane skipped

A dishonest `completed` blocks all of that.

---

## What gets your result rejected at review

The `review --task <name> --json` step runs `review_result_file` on each
result. These checks will reject your output:

| Rejection reason | Cause |
|---|---|
| `missing keys: …` | You forgot a required schema field |
| `invalid schema` | `schema` field isn't `"repers.step_result.v1"` |
| `invalid status` | `status` is anything other than `"completed"` / `"failed"` |
| `completed result has non-zero returncode` | Contradiction: success + error code |
| `failed result has zero returncode` | Contradiction: failure + success code |

Other failure modes that aren't auto-caught but will show up later:
- You edited a file outside `target_files` — caught when a sibling
  worker's edit clobbers yours or when the supervisor diffs the
  working tree against the plan's declared scope.
- You wrote to `results/<id>.json` for an id that wasn't yours —
  caught when the actual step's result file is missing.
- Your `stdout_tail` says the change happened, but the actual file
  doesn't reflect it — caught when the next stage's `verification_command`
  runs.

---

## You don't need to be Claude

The contract above is JSON-in / JSON-out. The supervisor doesn't know
or care which model produced the result, as long as:

- The result file's schema validates
- The `target_files` list matches what the dispatch declared
- The `status` and `returncode` are consistent
- The edits actually exist in the working tree

A Codex-as-worker, Gemini-as-worker, or in-house-fine-tune-as-worker all
satisfy the same contract. A worker that uses no LLM at all (a deterministic
script the supervisor hands the action text to) also satisfies the contract
as long as the action is automatable.

This means a single RePERS task can have:
- a Claude supervisor agent
- a Codex worker on lane 1
- a Gemini worker on lane 2
- a deterministic script worker on lane 3
- a Claude reviewer agent at join time

…and the contract holds the whole way through.

---

## TL;DR

```
1. Read your assigned step from plan.json (find your id)
2. Edit ONLY the files in target_files
3. Write repers_tasks/<task>/results/step-<id>.json with schema=repers.step_result.v1
4. Use status="completed" + returncode=0 OR status="failed" + non-zero + stderr_tail
5. Stop. Don't poll. Don't read other workers' results. The supervisor joins.
```

If any of these are unclear, re-read the relevant section above.

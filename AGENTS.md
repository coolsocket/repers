# AGENTS.md — first-contact playbook for AI agents

You're an AI agent (Claude, Codex, Gemini, an in-house model, whatever).
Your user just pointed you at this repo and probably said one of:

- "What is this? Should I install it?"
- "Try this on my project / on this task."
- "Explain this to me."

**This file is your playbook.** Read it before reading the rest of the repo.
The README is for humans browsing; this file is the contract for you.

If you're a human reading this: you can stop here and read [`README.md`](./README.md).
If you're a maintainer EDITING this harness, see [`CLAUDE.md`](./CLAUDE.md) instead.

---

## ⏱️ 60 seconds — what RePERS is

**RePERS = Research → Plan → Execute → Review → Ship.** A contract layer
that lets multiple AI agents (you + other Claudes / Codex / Gemini /
whatever) work on the same codebase in parallel without clobbering, and
hand the result off via JSON evidence another team / repo / agent can
re-verify.

Three things to internalize:

1. **It's a contract, not a runtime.** RePERS does not execute LLM calls.
   It tells you (the runtime) *which lane to take, what shape to produce,
   and how to hand off*. You provide the intelligence; RePERS provides
   coordination.

2. **It is opinionated about when NOT to use it.** For small single-file
   work, the harness's coordination overhead costs more than it saves —
   use a naked agent loop instead. The router exists so you never force
   the harness onto work that's too small for it.

3. **The R/P/E/R/S stages have distinct purposes**:
   - **R**esearch (preflight) → **memory and asset reuse** — don't rebuild what already exists
   - **P**lan + **E**xecute (DAG + dispatch) → **speed and effect** — parallelism with collision guards
   - **R**eview + **S**hip (join + pack) → **alignment and export** — the work becomes consumable by other teams/repos/agents

Skip a layer when the task doesn't need it. The router decides which.

---

## ⏱️ 5 minutes — route the task FIRST, before installing anything

The router runs **cold** — no install needed. Run it from a fresh clone:

```bash
git clone https://github.com/coolsocket/repers.git /tmp/repers
python3 /tmp/repers/.repers/scripts/repers.py route \
  --task "<the user's actual task, one sentence>" \
  --est-files <integer or omit if unknown> \
  --repo-root <path to the USER's repo if you're routing for their codebase, not the harness clone> \
  --json
```

(`--repo-root` defaults to the harness clone, which auto-detects file count and domain count from the harness itself. If you're routing for the user's actual repo, point it there so the signals are real.)

The response carries a `next_step` envelope. **Branch on `next_step.action` — don't parse prose.**

| `next_step.action` | What you do | Install needed? |
|---|---|---|
| `skip_harness` | Return to your user's task using your own Read/Edit/Bash. **Do not mention the harness again.** | No |
| `naked_loop` | Same — naked agent loop. The router is telling you the harness will cost more than it saves. | No |
| `research_only` | Install + run `preflight --query "..." --refresh --json` once, write a research note, stop. Tell the user "this is a spike, not yet a build." | Yes |
| `docs_only_ship` | Install + make the docs/config edit + run `shipping --task <name> --json` to write delivery evidence. Skip plan/execute. | Yes |
| `invoke_bug_hunt_no_ship` | Install + invoke `/repers-bug-hunt` skill (or follow its procedure manually). Full plan→dispatch→review, skip shipping. | Yes |
| `invoke_bug_hunt_full` | Install + invoke `/repers-bug-hunt` end-to-end including shipping. | Yes |

**If the router output's `next_step.action` is `skip_harness` or `naked_loop`,
you are done with RePERS. Do the user's actual task with your own tools.**

---

## ⏱️ 30 minutes — full pipeline, when the router routed you in

If the router returned `invoke_bug_hunt_no_ship` or `invoke_bug_hunt_full`,
the documented walkthrough is at [`docs/e2e-walkthrough.md`](./docs/e2e-walkthrough.md)
— every CLI command shown was actually executed, every artifact is real.
The 10 commands at a glance:

```bash
# Install (once per user repo)
python3 /tmp/repers/.repers/scripts/repers.py install --target /path/to/user/repo --json
cd /path/to/user/repo

# Init the task
python3 .repers/scripts/repers.py init --task <name>
python3 .repers/scripts/repers.py preflight --query "<intent>" --refresh --json

# Plan — fill repers_tasks/<name>/plan.md with a real DAG (see plan.md template).
# For lanes you want a subagent to drive, omit Verification Command (mode = subagent).
# For supervisor-local steps, include Verification Command (mode = local).

python3 .repers/scripts/repers.py plan --task <name> --json
python3 .repers/scripts/repers.py dispatch --task <name> --max-workers 3 --json
```

The dispatch manifest lands at `repers_tasks/<name>/dispatch/manifest.json`.
**Take that JSON and hand each `workers[]` entry to a parallel subagent**
(your own Agent tool, an external runtime, gemini CLI fan-out, your queue
— anything). Each worker writes its `step_result_v1` artifact to
`repers_tasks/<name>/results/step-<id>.json`.

```bash
# Join + verify worker outputs
python3 .repers/scripts/repers.py review --task <name> --update-status --json
python3 .repers/scripts/repers.py plan --task <name> --json   # refresh plan.json (auto-done in v0.1.1)
python3 .repers/scripts/repers.py run --task <name> --action local --use-existing-plan --json

# Ship (only if router said invoke_bug_hunt_full)
python3 .repers/scripts/repers.py shipping --task <name> --json
```

---

## 📜 The `step_result_v1` contract — what each worker writes

> If you ARE the worker on a lane (not the supervisor), the full contract
> is at [Appendix B](#appendix-b--worker-contract-if-you-were-dispatched-onto-a-lane)
> below. The summary below is enough for a supervisor agent driving the pipeline.

When a worker (you or your sibling agent) finishes a lane, write a JSON
file to `repers_tasks/<name>/results/step-<id>.json` with this exact shape:

```json
{
  "schema": "repers.step_result.v1",
  "step_id": "1",
  "title": "<lane title from plan.md>",
  "status": "completed",                                  // or "failed"
  "command": "<short description of what was done>",
  "returncode": 0,                                        // 0 if completed; non-zero if failed
  "duration_seconds": 12.3,
  "stdout_tail": "<last useful output>",
  "stderr_tail": "",
  "target_files": [".repers/scripts/dag_engine.py"]       // disjoint from sibling lanes
}
```

`review` validates this schema before declaring the join successful. If
your status is `failed`, set a non-zero `returncode` and put the error
in `stderr_tail` — don't silently pretend completion.

**The `target_files` field is load-bearing.** A worker that writes outside
its declared `target_files` violates the dispatch contract and breaks the
collision guarantee. Stay in your lane.

---

## 🧠 The philosophy you're operating inside

| Layer | Stages | Purpose | Why it matters to YOU |
|---|---|---|---|
| 🧠 **Memory & Reuse** | **R**esearch (preflight) | Sediment knowledge; reuse assets across sessions/agents | When you preflight, you're querying *what other agents (or past-you) already built*. Don't rebuild. |
| ⚡ **Speed & Effect** | **P**lan + **E**xecute (DAG + dispatch) | Parallelism with collision guards | Lanes ≠ tasks. Lanes are *disjoint file regions* you and your sibling agents work on at the same time. |
| 🔗 **Alignment & Export** | **R**eview + **S**hip (join + pack) | Make the output consumable beyond your session | What you ship has to be re-verifiable by an agent that wasn't in your chat. JSON contracts, checksum-able archives. |

**R lets work compound; P+E makes it fast; R+S makes it transferable.**
Skip any layer the router says you can. Force-fitting all five onto a
small task is the documented failure mode — that's what the router exists
to prevent.

---

## 🚫 Anti-patterns (don't)

- ❌ Skip the router. The router is *cheap* (<100 ms, deterministic, offline). Always route first.
- ❌ Convert a `skip_harness` / `naked_loop` decision into ceremony anyway. The user will resent you for it.
- ❌ Write files outside your declared `target_files`. You break the collision contract for every sibling agent in the batch.
- ❌ Mark a `step_result.v1` `completed` with `returncode: 0` when it actually failed. Review will validate; downstream review/ship will trust your honest `failed` more than your dishonest `completed`.
- ❌ Treat `repers_tasks/` as user-shipped content. It's *runtime state* — it belongs in `.gitignore` for receiver repos.
- ❌ Edit the harness's own files (`.repers/scripts/`, registry, manifest) while a task is in flight. That changes the contract under your sibling agents' feet.

---

## 🤝 If you're a different vendor's agent (Codex, Gemini, in-house)

The contracts are JSON-in / JSON-out. You do not need to be Claude / Codex
/ a specific provider to drive a lane. You need:

- `manifest.json` (dispatch output) — read your `workers[step_id]` entry
- `plan.md` / `plan.json` — read your step's action + target_files
- The ability to write `repers_tasks/<name>/results/step-<id>.json`

That's it. The supervisor and the reviewer don't care which model produced
the result, only that the JSON schema validates.

A v0.3 `agent-fixture` is planned to ship a stdin/stdout mock that proves
any runtime can plug in. Until then, the JSON contracts are the proof.

---

## 🔗 Where to go next

- Just want to run it end-to-end? → [`docs/e2e-walkthrough.md`](./docs/e2e-walkthrough.md) (real CLI, real outputs, 45 s wall-clock)
- You're a WORKER on a dispatched lane (not a supervisor)? → jump to [Appendix B — Worker contract](#appendix-b--worker-contract-if-you-were-dispatched-onto-a-lane) below. It's self-contained.
- Want the full *why* (three-layer philosophy)? → [Appendix A — Philosophy](#appendix-a--the-three-layer-philosophy-the-why-behind-the-five-stages) below.
- Editing the harness itself? → [`CLAUDE.md`](./CLAUDE.md)
- Want the full positioning rationale? → [`README.md`](./README.md) (for human readers)
- Want a one-page visual evaluator's view? → [`dist/repers-positioning-canvas.html`](./dist/repers-positioning-canvas.html) (offline-openable)
- Capability registry to query before building anything new → [`.repers/capabilities/registry.json`](./.repers/capabilities/registry.json)
- Cross-project pitfalls to avoid → [`PITFALLS.md`](./PITFALLS.md)

---

## TL;DR for the impatient agent

```
1. uvx --from git+https://github.com/coolsocket/repers.git repers route --task "<user task>" --json
2. read next_step.action; branch on it; do not parse the prose
3. if skip_harness or naked_loop: use your own tools; do not install
4. otherwise: follow the action's command/skill
```

That's the entire first-contact protocol. Everything else in this file
is detail for paths 4+ above (including the two appendices below — only
read those if your role calls for them).

---

## Appendix A — The three-layer philosophy (the why behind the five stages)

> Five stages, grouped into **three layers**, each with a distinct purpose.
> Understanding the three purposes is how you decide which stages to actually
> run for any given task. The router automates that decision; this appendix
> explains the model the router encodes.

### The three layers

| Layer | Stages | One-line purpose | Who it serves |
|---|---|---|---|
| 🧠 **Memory & Reuse** | **R**esearch (preflight) | Sediment knowledge across sessions; don't rebuild what exists | The *future self* / the *future agents* |
| ⚡ **Speed & Effect** | **P**lan + **E**xecute (DAG + dispatch) | Decompose into disjoint lanes; parallelize without collision | The *current* work-in-flight |
| 🔗 **Alignment & Export** | **R**eview + **S**hip (join + pack) | Make the output consumable by parties not in this session | The *downstream*: other repos / teams / vendors / auditors |

**One-sentence summary**: R lets knowledge compound; P+E makes the doing fast and parallel; R+S makes the result transferable beyond the session. You don't always need all three. The router picks per task.

### 🧠 Layer 1 — Memory & Reuse (Research / preflight)

> *The question this layer answers*: "Has someone (me-in-the-past, my teammate, my other agent session) already built or learned this?"

**What it ships**: `preflight --query "<intent>" --json` (searches typed capability registry + repo file index + optional code-graph), `capabilities/registry.json` (typed inventory of reusable workflows / scripts / hooks / gates), `research.md` template per task, `repers-sinkin` drift audit.

**Why it matters at scale**: At Day 0 you remember everything you built last week. At 50 k LOC you don't. At 200 k LOC across 4 teams *using 3 different agents*, your teammate's Codex session is rebuilding what your Claude session built yesterday — and neither knows. The capability registry is the *shared memory* across agents.

**When to skip**: One-off throwaway tasks. The router's `skip_harness` decision is "your memory layer for this task is your own head, not a registry."

### ⚡ Layer 2 — Speed & Effect (Plan + Execute / DAG + dispatch)

> *The question this layer answers*: "How do I get this done faster AND with fewer mistakes than one agent could in series?"

**What it ships**: `plan.md` template + `plan --json` (markdown-friendly DAG with `target_files` per step), `dispatch --max-workers N --json` (produces `repers.dispatch.v1` manifest with collision-safe batching — no two workers in the same batch write the same file), `orchestration-fixture` (deterministic offline test proving the dispatch contract), `run --action local` (supervisor-side execution).

**Why it matters at scale**: Speed alone is a runtime concern — any agent runtime parallelizes. The **collision contract** is the load-bearing addition: when N agents are working on the same area at the same time, target-file isolation prevents last-writer-wins clobbering. The fixture proves this property *before* live agents are pointed at the lanes.

**Why the plan format is opinionated**: `plan.md` is human-editable markdown, not YAML/JSON. Because in a multi-agent fleet the plan is the **inter-agent contract** — it has to be diff-able, comment-able, and PR-review-able by humans who don't run Claude. Markdown is the universal middle.

### 🔗 Layer 3 — Alignment & Export (Review + Ship / join + pack)

> *The question this layer answers*: "Can someone NOT in this chat — a reviewer, an auditor, a downstream repo, a different vendor's agent — pick this up and verify it independently?"

**What it ships**: `step_result.v1` contract (every worker writes a fixed-schema JSON artifact), `review --update-status --json` (validates all worker results, refreshes plan.json), `shipping --task <name> --json` (writes delivery-evidence artifact), `release-pack` (single transferable zip — install archive + readiness + evidence + handoff + bootstrap + benchmark + state), `release-pack-verify` (receiver re-verifies checksums + manifest + embedded evidence *without trusting the sender's vendor or JSON*), 4 install fixtures.

**Why it matters at scale**: At the small end your audit trail is the git log + chat transcript. At enterprise scale neither survives: the chat is ephemeral, the git log shows the patch but not the reasoning chain, and across vendors no one can read each other's transcripts. **JSON evidence is the only audit format that survives** vendor swaps, team handoffs, and trust boundaries. The release pack is what gets attached to the PR that says "Team A's Codex did this, here's the evidence chain, Team B's CI can re-verify."

**The under-told story**: this layer is RePERS's strongest under-promoted feature. Most agent harnesses ship a runtime; very few ship a **cross-trust-boundary verification protocol**. The release pack is that protocol.

### How the layers interact (the router's job)

The router (`route --task "..." --json`) outputs a permutation: which layers to fire.

| Permutation | Layers | When |
|---|---|---|
| `skip` | (none) | Trivial — harness is overhead. Naked tools win. |
| `R-only` | 🧠 R | Spike. Want memory of "we looked at this and decided…", don't want to build yet. |
| `R-S` | 🧠 R + 🔗 S | Docs/config-only change. Skip the doing layer; just sediment + export. |
| `R-E-R` | 🧠 R + (E) + 🔗 R | Hotfix. One file, test pins answer. Lightweight memory + naked execute + lightweight review. |
| `R-P-E-R` | 🧠 R + ⚡ P+E + 🔗 R | Multi-file in one domain. Memory + parallel + review. Skip export. |
| `R-P-E-R-S` | 🧠 R + ⚡ P+E + 🔗 R+S | Full pipeline. Multi-domain, multi-day, multi-agent, multi-team. Every layer pays. |

**No permutation activates a stage whose layer-purpose doesn't apply.** That's the philosophy enforced in code.

### What RePERS is NOT

- **Not a runtime.** RePERS does not call LLMs. Other harnesses (LangGraph, CrewAI, OpenHands, your own dispatcher) do. RePERS is the contract those runtimes can share.
- **Not a productivity tool for one developer.** A single dev with a single agent on a single repo will measure RePERS as net overhead — the coordination cost has nothing to coordinate. The router will tell that dev to skip the harness. The value is *multi*.
- **Not a competitor to existing agent frameworks.** Layered above, not against. A LangGraph graph can produce `step_result.v1` artifacts; a CrewAI crew can read a `dispatch.v1` manifest.
- **Not "always use all five stages".** Force-fitting the full pipeline onto small work is the documented failure mode. The router exists precisely to route AWAY from this.

---

## Appendix B — Worker contract (if you were dispatched onto a lane)

> **Read this only if a supervisor agent has dispatched you onto one specific lane** of a RePERS pipeline. If you're a first-contact agent or a supervisor, the rest of this file (above) is what you need; this appendix is for the worker role.

You're an AI agent (Claude / Codex / Gemini / a fine-tune / your own). A supervisor agent — running through some agent runtime that doesn't need to be the same vendor as you — has used RePERS to plan multi-lane work and **dispatched you onto one specific lane**.

**This appendix is your contract**: what JSON to read, what JSON to write, what counts as "done", and what'll get your output rejected at review.

### What you're given

The supervisor handed you (in one form or another) two file paths:

1. **The dispatch manifest** — JSON, at `repers_tasks/<task>/dispatch/manifest.json`. Schema: `repers.dispatch.v1`. Contains a `workers` array; find the entry whose `worker_id` or `step_id` matches your assignment.
2. **The plan** — `repers_tasks/<task>/plan.md` (human-friendly) and `repers_tasks/<task>/plan.json` (machine-friendly). The plan.json `steps[]` array has the same `id`s as the dispatch's `step_id`s — find your step there for the action description and target files.

You may not have been given literal paths. Common forms: the supervisor pasted the JSON inline into your prompt; told you "your worker_id is `batch1-step2`" + paths; or handed you only the action text + target_files. In all cases the underlying contract is the same. Your output goes back as a JSON file.

### Your step's shape

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

Key fields:

| Field | Meaning | Your obligation |
|---|---|---|
| `id` | Step number from plan.md | Use this as `step_id` in your result artifact |
| `action` | Free-text instruction | This is *what* to do. Interpret it as you would any natural-language task. |
| `target_files` | List of file paths you're allowed to edit | **HARD CONSTRAINT.** Touching any file outside this list breaks the collision contract. |
| `expected_outcome` | What "done" looks like, in prose | Verify this is true before declaring `completed`. |
| `depends_on` | List of other `id`s this step needs done first | If your step has deps, the supervisor should not have dispatched you until they were `Completed`. Trust the supervisor; don't re-check. |
| `mode` | `subagent` (you) or `local` (supervisor runs it) | If you got dispatched, your step is `subagent` mode. |
| `artifact_contract` | Always `step_result_v1` for v0.1.x | Your output JSON must match this schema. |

### Your four obligations

**1. Stay in your lane.** You may only edit files in your step's `target_files`. Reading other files is fine and encouraged. Editing other files is forbidden, even if the action implies it. If the action says "rename function X everywhere" but `target_files` is only `[src/foo.py]`, your work is *inside* `src/foo.py` only. If the rename needs callers updated, that's a *different lane* the supervisor should have planned. If action and target_files look contradictory, write `status: "failed"` with `stderr_tail` explaining — let the supervisor re-plan.

**2. Don't read other workers' results.** Files at `repers_tasks/<task>/results/step-*.json` (other than your own) may be incomplete, in-progress, or absent. Do not depend on them.

**3. Write your result, then stop.** When done, write **exactly one JSON file** at `repers_tasks/<task>/results/step-<your-id>.json`:

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

Field rules: `schema` exactly `"repers.step_result.v1"`. `status` exactly `"completed"` or `"failed"` (no `"partial"` / `"unknown"`). `returncode` 0 iff `completed`, non-zero iff `failed` — reviewer rejects `completed` + non-zero or `failed` + zero. `target_files` must equal the list you were given — don't add files you happened to touch. After writing, **stop** — don't post-process, don't poll, don't call review yourself.

**4. Be honest about `failed`.** A dishonest `completed` blocks the supervisor's ability to retry your lane / re-plan / ship with your lane skipped. A `failed` with the real error is always safer.

### What gets your result rejected at review

| Rejection reason | Cause |
|---|---|
| `missing keys: …` | You forgot a required schema field |
| `invalid schema` | `schema` field isn't `"repers.step_result.v1"` |
| `invalid status` | `status` is anything other than `"completed"` / `"failed"` |
| `completed result has non-zero returncode` | Contradiction: success + error code |
| `failed result has zero returncode` | Contradiction: failure + success code |

Not auto-caught but will show up later: editing outside `target_files` (sibling worker clobbers yours or supervisor diffs the working tree), writing to a results/<id>.json that wasn't yours (your real id's result file is missing), `stdout_tail` claims an edit that isn't in the file (next stage's verification fails).

### You don't need to be Claude

The contract is JSON-in / JSON-out. The supervisor doesn't know or care which model produced the result, as long as: the result file's schema validates, the `target_files` list matches what dispatch declared, `status` and `returncode` are consistent, and the edits actually exist in the working tree. A single RePERS task can have a Claude supervisor + Codex worker on lane 1 + Gemini worker on lane 2 + deterministic-script worker on lane 3 + Claude reviewer at join time, and the contract holds the whole way through.

### Worker TL;DR

```
1. Read your assigned step from plan.json (find your id)
2. Edit ONLY the files in target_files
3. Write repers_tasks/<task>/results/step-<id>.json with schema=repers.step_result.v1
4. Use status="completed" + returncode=0 OR status="failed" + non-zero + stderr_tail
5. Stop. Don't poll. Don't read other workers' results. The supervisor joins.
```

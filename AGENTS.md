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

2. **It is opinionated about when NOT to use it.** A benchmark on a
   real 4-line bug measured **5.8× wall-clock overhead vs. a naked agent
   loop**. The router exists so you never force the harness onto work
   that's too small for it.

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
small task is the documented failure mode (5.8× overhead).

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
- Editing the harness itself? → [`CLAUDE.md`](./CLAUDE.md)
- Want the full positioning rationale? → [`README.md`](./README.md) (for human readers)
- Want a one-page visual evaluator's view? → [`dist/repers-positioning-canvas.html`](./dist/repers-positioning-canvas.html) (offline-openable)
- Capability registry to query before building anything new → [`.repers/capabilities/registry.json`](./.repers/capabilities/registry.json)
- Cross-project pitfalls to avoid → [`PITFALLS.md`](./PITFALLS.md)

---

## TL;DR for the impatient agent

```
1. git clone https://github.com/coolsocket/repers.git /tmp/repers
2. python3 /tmp/repers/.repers/scripts/repers.py route --task "<user task>" --json
3. read next_step.action; branch on it; do not parse the prose
4. if skip_harness or naked_loop: use your own tools; do not install
5. otherwise: install + follow the action's command/skill
```

That's the entire first-contact protocol. Everything else in this file
is detail for paths 5+ above.

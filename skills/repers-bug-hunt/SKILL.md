---
name: repers-bug-hunt
description: "Run the RePERS bug-hunt workflow for a multi-file or multi-domain bug investigation. ALWAYS routes through /repers-route first — if the router says 'skip' or 'R-E-R', do not invoke the full pipeline; fall back to a naked agent loop. Only proceeds with preflight → plan → dispatch → review → ship when the router recommends a multi-stage permutation."
---

# repers-bug-hunt

> **Layers**: 🧠 **R** (preflight) + ⚡ **P** (plan as DAG) + ⚡ **E** (parallel dispatch) + 🔗 **R** (review/join) — and optionally 🔗 **S** (shipping) when the router returns `R-P-E-R-S`. Skipped entirely when the router says `skip` / `naked_loop`.

Use this skill ONLY when the user asks for help on a bug, AND the router
agrees the harness will earn its overhead. RePERS has a measured **5.8×
wall-clock cost over a naked agent for small single-file bugs** — running
the full bug-hunt skill on the wrong task shape is the most common
anti-pattern.

## Procedure

### Step 1 — Always route first

```bash
python3 .repers/scripts/repers.py route \
  --task "<one-line bug description>" \
  --est-files <N if you can guess; otherwise omit> \
  --json
```

Read the `permutation` field. Then branch:

| router said | what to do |
|---|---|
| `skip` | **STOP. Do not run any more RePERS commands.** Tell the user the router routed away from the harness. Suggest they use their IDE + agent loop directly. |
| `R-E-R` | **Naked agent loop is fine.** Read the failing test, edit, verify. The harness's preflight + plan + dispatch + review will cost more than they save. Don't invoke them. |
| `R-S` | This isn't a bug — it's a docs / config change. Suggest `/repers-release-pack` instead. |
| `R-only` | The user wants to scope, not fix. Run preflight + write a research note (`repers_tasks/<name>/research.md`), then stop. |
| `R-P-E-R`   | Multi-file in one domain. Run Steps 2-7 below; SKIP step 8 (shipping). |
| `R-P-E-R-S` | Full pipeline. Run all of Steps 2-8 below. |

### Step 2 — Preflight (only when router recommends ≥ R-P-E-R)

```bash
python3 .repers/scripts/repers.py preflight --query "<bug or symptom>" --refresh --json
python3 .repers/scripts/repers.py capabilities --action search --query "<bug or subsystem>" --json
```

### Step 3 — Init task workspace

```bash
python3 .repers/scripts/repers.py init --task "<task-name>"
```

### Step 4 — Fill plan.md with a real DAG

Edit `repers_tasks/<task_name>/plan.md` — split work into lanes with
disjoint `Target File` per lane (this is what makes parallel dispatch
collision-safe).

For lanes you want a SUBAGENT to run, **omit `Verification Command`** (the
mode inference reads "no command → subagent"). For local verify steps
(e.g., "all 3 lanes done, run the test suite"), include the verification
command.

### Step 5 — Plan + dispatch

```bash
python3 .repers/scripts/repers.py plan --task "<task-name>" --json
python3 .repers/scripts/repers.py dispatch --task "<task-name>" --max-workers 3 --json
```

The dispatch manifest lands at `repers_tasks/<task>/dispatch/manifest.json`.
Hand its `workers[]` entries to your parallel agent runtime (Agent tool,
Codex subagent, gemini CLI fan-out, whatever) and have each worker write
its result as `repers_tasks/<task>/results/step-<N>.json` conforming to
the `repers.step_result.v1` schema.

### Step 6 — Review

```bash
python3 .repers/scripts/repers.py review --task "<task-name>" --update-status --json
```

This validates each result artifact's schema, updates `plan.md` statuses,
and (since v0.1.1) auto-refreshes `plan.json` so subsequent runs see the
new statuses.

### Step 7 — Run any local verify steps

```bash
python3 .repers/scripts/repers.py run --task "<task-name>" --action local --use-existing-plan --json
```

### Step 8 — Shipping (only when router recommended R-P-E-R-S)

```bash
python3 .repers/scripts/repers.py shipping --task "<task-name>" --json
```

## Report shape

Lead with:

- the router's decision and its reason;
- bug found or not found;
- evidence paths and commands;
- patch summary, if a patch was made;
- verification results;
- unresolved risks.

Do not treat a chat explanation as sufficient evidence when RePERS can
write a task artifact or JSON gate. But equally — **do not invent a
task artifact for a 4-line single-file fix** that the router said to
skip. Match ceremony to scope.

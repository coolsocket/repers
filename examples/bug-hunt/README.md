# Bug-hunt / multi-file task example

A real, observable walk-through of the full **R-P-E-R-S** pipeline on a
multi-file task — every CLI command actually executed, every artifact produced.

> 📖 **The walkthrough lives at [`docs/e2e-walkthrough.md`](../../docs/e2e-walkthrough.md).**
> It records each command, its output, the artifacts produced, and the two
> small UX gotchas encountered. Read that first.

This `README` is the **30-second pitch** for what the walkthrough proves.

---

## The 30-second pitch

A 4-step DAG with 3 parallel subagent lanes + 1 supervisor verify lane was
driven through the entire RePERS CLI in **~45 seconds wall-clock** (dominated
by the parallel worker phase). No subcommand failed. Every artifact landed at
the path the schema documented.

## The 10 commands (in order)

```bash
python3 .repers/scripts/repers.py init --task <name>
python3 .repers/scripts/repers.py preflight --query "<intent>" --refresh --json
# (fill in plan.md with a step DAG)
python3 .repers/scripts/repers.py plan       --task <name> --json
python3 .repers/scripts/repers.py dispatch   --task <name> --max-workers N --json
# (your agent runtime picks up dispatch/manifest.json, runs N parallel workers,
#  each writes results/step-K.json conforming to repers.step_result.v1)
python3 .repers/scripts/repers.py review     --task <name> --update-status --json
python3 .repers/scripts/repers.py plan       --task <name> --json           # refresh stale plan.json
python3 .repers/scripts/repers.py run        --task <name> --action local --use-existing-plan --json
python3 .repers/scripts/repers.py shipping   --task <name> --json
python3 .repers/scripts/repers.py refresh-manifest --json && \
python3 .repers/scripts/repers.py verify-install --json
```

## What you should leave knowing

- The **dispatch manifest** (`repers.dispatch.v1`) is the contract you hand to
  your agent runtime — not just to Claude/Codex, but to anything that can read
  a JSON file and write a `step_result_v1` artifact back.
- `infer_mode` picks each step's mode by whether it has a
  `verification_command`: present → `local` (supervisor runs it); absent →
  `subagent` (dispatched to a worker). Same plan.md serves both.
- The full pipeline is **route-able** — for small bugs the v0.2 router
  (`/repers-route`) will tell you to skip most of it. See
  [`README#-when-to-use--when-not-to-use`](../../README.md#-when-to-use--when-not-to-use)
  for which permutation fits which task shape.

## When to use this shape

The walkthrough's task (add module docstrings to 3 META scripts) is at the
**small end** of the harness sweet spot — chosen for clarity, not because the
overhead would have paid off vs. just editing 3 files by hand. The pipeline
shines on tasks at the **large end**: multi-file refactors, deprecation
sweeps, instrumentation rollouts. Same 10 commands; the lanes carry more
substance.

See the [main README's "When to use / When NOT to use" table](../../README.md#-when-to-use--when-not-to-use)
for the explicit fit criteria.

## What was REMOVED from the old version of this example

The previous `bug-hunt` example was a 4-command sequence that **never
investigated a bug** — it just ran `preflight` + `fixture --action prove` +
`state` and called that a "bug-hunt walk-through". That was framework
introspection, not bug-hunting. The replacement (this file + the walkthrough)
shows real CLI orchestration with real parallel workers producing real
artifacts.

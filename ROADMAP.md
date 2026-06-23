# Roadmap

The RePERS roadmap is organized around the positioning: **operating layer for
multi-agent repository work**. See [`README.md`](./README.md#-when-to-use--when-not-to-use)
for what's in and what's out of scope.

## v0.1 — shipped (2026-06-22)

- Installable `.repers/` runtime (preflight / doctor / audit / install-hook / verify-install / package / bundle-status).
- Package manifests + round-trip archive verification + receiver smoke fixture.
- Deterministic orchestration fixture proving conflict-safe dispatch + join + review.
- `capabilities/registry.json` (24 entries) + `capabilities` CLI; preflight surfaces entries as `source=local_capability`.
- `release-evidence` separating package validity from final Git publish readiness.
- `release-pack.zip` as a transferable, checksum-verifiable handoff bundle.
- Receiver/source/clone install fixtures proving install paths from 3 different start states.
- Codex/Claude plugin with 4 skills (init / bug-hunt / release-pack / sinkin).

## v0.1.1 — shipped (unreleased; in `main`)

UX honesty pass after end-to-end dogfood (see [`docs/e2e-walkthrough.md`](docs/e2e-walkthrough.md)).

- 🧭 **Router shipped** — `/repers-route` skill + `repers.py route --task "<desc>" [--est-files N] --json` CLI. Deterministic keyword + repo-signal decision tree → `skip` / `R-only` / `R-S` / `R-E-R` / `R-P-E-R` / `R-P-E-R-S`. No LLM, <100 ms, offline. Validated on the sqlfluff bug: it would have correctly routed to "naked agent" instead of the 5.8× overhead.
- 🪝 **`/repers-bug-hunt` routes first** — now short-circuits to a naked agent loop when the router says `skip` / `R-E-R`. Only proceeds with preflight → plan → dispatch → review → ship when the router recommends multi-stage.
- 🛠️ **Two CLI UX fixes** from the dogfood:
  - `review --update-status` now also refreshes `plan.json` (no more "you forgot to re-plan" gotcha).
  - `verify-install` emits a `hint` field with the exact `refresh-manifest` command when only sha256 mismatches are detected.
- 📖 **Real end-to-end walkthrough** at `docs/e2e-walkthrough.md` (linked from README hero). 10 CLI commands, real outputs, 45 s wall-clock, 2 gotchas honestly documented.
- 📦 Registry version bumped to `0.1.1` (entry count 24 → 25 with new `route` capability).

## v0.2 — next

- 🎯 **Real "harness wins" example** — extend `examples/bug-hunt/` with a multi-file SWE-bench Verified instance walked end-to-end; show wall-clock comparison vs. naked at the size where the harness DOES pay off.
- 📜 **`WORKER.md`** — contract spec for any AI assigned to a lane (what JSON to read, what JSON to write, when "done" is declared).
- ✂️ **Registry trim** — remove self-referential META scripts (`state_report` / `continuation_runner` / `open_source_benchmark` partial); registry drops from 25 → ~16. Keep what's load-bearing across receivers.
- 🪝 **Router signal extensions** — overlay preflight hit count and similar-PR git-log count onto the heuristic so it can recommend `R-P-E-R-S` when there's strong reuse signal even if the task description is bland.

## v0.3 — agent-agnostic proof

- 🤖 **`agent-fixture`** — prove a non-Claude runtime (gemini CLI, or a stdin/stdout mock) can pick up a lane, produce contract-shaped JSON, and feed it back into the review stage. Defends the "any AI" claim end-to-end.
- 🔀 **Mixed-runtime fixture** — N lanes dispatched to N different runtimes; reviewer agent (could be a third runtime) joins.

## Later

- Optional external CodeGraph providers behind the preflight interface.
- Signed / provenance-rich release artifacts.
- Install profiles for different repository sizes and risk levels.
- Branch/PR automation once a remote + base is committed.

## Out of scope (explicitly)

These have been considered and rejected — opening an issue won't change that without new context.

- **Replacing agent runtimes.** RePERS is the layer above; runtimes (Claude, Codex, LangGraph, CrewAI, OpenHands) stay specialized.
- **Cloud-hosted runtime.** Local-first is a feature, not a limitation. Cloud backends remain optional adapters.
- **One-line-bug "productivity" mode.** That regime belongs to your IDE+agent, not to this harness. The router will route you out of it, not into it.
- **Heavy dependencies.** Stdlib-only Python is intentional.

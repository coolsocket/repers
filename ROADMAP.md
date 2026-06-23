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

## v0.2 — next (positioning + router)

The v0.1 → v0.2 theme is **stop being over-eager**. The benchmark on
`sqlfluff__sqlfluff-2419` measured 5.8× overhead vs. a naked agent on a 4-line
bug — the harness ran every stage when most should have been skipped.

- 🧭 **Router** — `/repers-route` skill + `repers.py route --task "<desc>" --json` CLI. Decision tree over (repo size, domain count, expected patch size, cross-cutting keywords) → recommended permutation (R-E-R / R-P-E-R / R-P-E-R-S / R-S / R-only). Trivial bugs get told to skip the harness entirely.
- 🪝 **`/repers-bug-hunt` routes first**, then conditionally executes only the prescribed stages.
- 🎯 **Real "harness wins" example** — replace `examples/bug-hunt/` with a multi-file SWE-bench Verified instance walked end-to-end; show wall-clock comparison vs. naked.
- 📜 **`WORKER.md`** — contract spec for any AI assigned to a lane (what JSON to read, what JSON to write, when "done" is declared).
- ✂️ **Registry trim** — remove self-referential META scripts (`state_report` / `continuation_runner` / `open_source_benchmark` partial); registry drops from 24 → ~15. Keep what's load-bearing across receivers.

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

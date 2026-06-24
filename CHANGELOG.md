# Changelog

All notable RePERS bundle changes are tracked here. The format follows
[Keep a Changelog](https://keepachangelog.com/) loosely; versioning is
semantic-ish — any user-visible behavior change bumps minor or major.

## Unreleased

## 0.2.0 — 2026-06-24 · BREAKING

Slim + pluggable refactor. **First breaking release in the v0.2 line.**

### Breaking — removed verbs and their scripts

These 4 CLI subcommands and their backing scripts have been **deleted**:

  - `objective-audit` (script: `objective_audit.py`)
  - `continue` (script: `continuation_runner.py`)
  - `snapshot-freshness` (script: `snapshot_freshness.py`)
  - `open-source-benchmark` (script: `open_source_benchmark.py`)

Reason: each was self-referential to RePERS's own v0.1 publication
objective and had no value to receivers. The router's `next_step.action`
never pointed at them. Receiver fixtures and tests that exercised them
have been removed alongside.

### Breaking — `state` slimmed

The `state` verb output no longer carries:
  - `state.objective.*` fields (complete / blocking_incomplete)
  - `state.next.*` fields (local_action_id / external_command)
  - `--deep` / `--objective` CLI flags

What it keeps: `git` / `package` / `capabilities` blocks. Schema
identifier stays `repers.state_report.v1` for now; consumers should
treat the removed fields as deleted, not renamed.

### Breaking — `release-pack` artifact set trimmed

Removed from `REQUIRED_RELEASE_PACK_ARTIFACTS`:
`open_source_benchmark_json`, `objective_audit`, `continuation_markdown`.
The release pack no longer bundles or expects these. Downstream
`release-pack-verify` consumers will simply see fewer artifacts.

### Breaking — registry trimmed 25 → 20

Removed entries: `objective-audit`, `continuation-runner`, `state-report`
(was a meta-entry about state_report.py), `snapshot-freshness`,
`open-source-benchmark`. Registry version bumped `0.1.1 → 0.2.0`.

### Non-breaking (additive in v0.2)

Carries forward Phases A + B + C (already merged in `Unreleased`):

  - `.repers/contracts/` — 7 versioned JSON Schemas (one per stage)
  - `.repers/plugins/` — one plugin slot per pipeline verb
  - `.repers/scripts/plugin_loader.py` — env-var-selectable plugin discovery
  - All 6 pipeline verbs resolve via plugin loader (with legacy fallback)
  - `WORKER.md` — contract spec for any AI on a dispatched lane
  - `PHILOSOPHY.md` — the three-layer model
  - `AGENTS.md` — first-contact agent playbook
  - Router with `next_step.action` enum
  - 5 Codex/Claude skills (init + route + bug-hunt + release-pack + sinkin)

### Migration

For receivers that previously called the removed verbs:

  - `objective-audit` / `continue` / `snapshot-freshness` / `open-source-benchmark`: replace with no-op or drop entirely; they were never load-bearing for receiver-side workflow.
  - `state --deep` → `state` (the `--deep` flag is gone; `state` now always runs the slim path)
  - `state` consumers reading `state.objective.complete` etc. → those fields are gone; if you need a richer objective tracker, write a plugin under `plugins/state/` (recommended).

### v0.2 architecture — Phase B + C: all 6 verbs plugin-loaded + 7 contracts

Phase B: every pipeline verb now resolves via the plugin loader. ZERO
behavior change. The substitution point is now live for all 6 stages.

- `plugins/preflight/default.py` — wraps `research_index.build_research_artifact`
- `plugins/plan/default.py` — wraps `plan_runner.build_plan_json` (+ `propose`)
- `plugins/dispatch/default.py` — wraps `plan_runner.dispatch_ready`
- `plugins/review/default.py` — wraps `reviewer.review_task`
- `plugins/ship/default.py` — wraps `shipping.create_shipping_report`
- `repers.py` handlers for preflight / plan / dispatch / review / shipping all migrated to use `plugin_loader.load_plugin` with legacy fallback. Explicit `REPERS_PLUGIN_<VERB>=missing` raises immediately (no silent fallback masks typos).

Phase C: 3 remaining contract schemas extracted as standalone files —
the full set of 7 stage contracts now lives at `.repers/contracts/`.

- `contracts/preflight.v1.json` — reuse/extend/create recommendation + results array
- `contracts/plan.v1.json` — step DAG with target_files + mode inference rules
- `contracts/shipping.v1.json` — task-level delivery evidence shape

Smoked end-to-end in a fresh receiver repo (`/tmp/phaseb-test/`):
preflight → plan → dispatch → review all produce contract-conforming
output via the plugin path. Manifest 51 → 59 files (+5 plugin defaults,
+3 contract schemas). verify-install + capabilities-validate both green.

### v0.2 architecture seed — Phase A: contracts + plugin loader

Foundation for the v0.2 slim+pluggable refactor. **Zero behavior change**
— existing CLI works identically. What's new is the *substitution path*:
any verb's implementation can now be swapped without forking the harness.

- **New `.repers/contracts/` directory** — first 4 JSON Schemas extracted as standalone files (`router.v1.json`, `step_result.v1.json`, `dispatch.v1.json`, `review.v1.json`). These are the stable shapes that flow between pipeline stages; future stages add `preflight.v1.json`, `plan.v1.json`, `shipping.v1.json`. See `.repers/contracts/README.md`.
- **New `.repers/plugins/` directory** — convention: `plugins/<verb>/<name>.py` exporting a function whose name matches the verb. First plugin shipped: `plugins/route/default.py` (wraps the existing `router.py` so behavior is preserved exactly).
- **New `.repers/scripts/plugin_loader.py`** — discovers + imports a plugin module by `(verb, name)`. Selection precedence: `REPERS_PLUGIN_<VERB>` env var → `default` → fallback to legacy in-tree implementation. Explicit env-var requests for missing plugins raise immediately (no silent fallback to mask typos).
- **`repers.py route` migrated to plugin path** — first verb to use the loader. Verified across three runs: silent default load, explicit `REPERS_PLUGIN_ROUTE=default` load, explicit invalid-name → loud `FileNotFoundError`. Remaining verbs (preflight / plan / dispatch / review / ship) migrate verb-by-verb in subsequent commits, each backwards-compat with legacy fallback.
- **New `docs/components-map.md`** — one-page map of every CLI verb / file template / skill grouped by R-P-E-R-S layer, with output schema column. Use to find substitution points.

### `WORKER.md` shipped

- New top-level [`WORKER.md`](WORKER.md) — the contract spec for any AI agent assigned to a dispatched lane. Covers the `step_result_v1` schema, target_files isolation, reject-at-review failure modes, "you don't need to be Claude" clause (the contract is JSON-in / JSON-out so a single RePERS task can mix Claude supervisor + Codex worker + Gemini worker + reviewer of any vendor). Linked from AGENTS.md "Where to go next" and from the README's "For AI agents" section.

### v0.1.1 — Router shipped

- **`/repers-route` skill + `repers.py route` CLI subcommand.** Deterministic keyword + repo-signal decision tree that maps a task description to one of `skip` / `R-only` / `R-S` / `R-E-R` / `R-P-E-R` / `R-P-E-R-S` plus a one-line reason and recommendation. No LLM call, <100 ms, offline. Validated on real tasks: small single-file work routes to `R-E-R` ("naked agent loop is fine") rather than the full pipeline.
- **`/repers-bug-hunt` skill now routes first.** Hard-coded to short-circuit on `skip` / `R-E-R` (returns control to the IDE/agent without invoking the harness pipeline) and only progresses through plan → dispatch → review → shipping when the router recommends a multi-stage permutation.
- **Capability registry entry added** for `route` (entry count 24 → 25); `capabilities/registry.json` version bumped to `0.1.1`.
- **Skills count badge updated** 4 → 5; capabilities count badge updated 24 → 25.

### Runtime UX fixes (small, from E2E dogfood findings)

- **`review --update-status` now also refreshes `plan.json`.** Previously, after `review` rewrote plan.md statuses to `Completed`, plan.json kept the old `Pending` values; the next `run --use-existing-plan` / `dispatch --use-existing-plan` would not consider dependent steps ready. The refresh removes that whole gotcha — review output now includes `status_update.plan_json_refresh: {refreshed: bool, error: str|null}` so callers can observe whether the sync happened.
- **`verify-install` now emits an actionable `hint` field.** When the only failure mode is `size,sha256` mismatches on otherwise-tracked files (the overwhelming "I edited an installed file in place" case), `hint` carries the exact `refresh-manifest` command to fix it. When there's no helpful action, `hint` is `null` (always-present key for stable consumer code).

Both were surfaced by the end-to-end CLI dogfood documented in [`docs/e2e-walkthrough.md`](docs/e2e-walkthrough.md).

### Documentation surfaces (no runtime change)

- **`README.md`** — added a top-of-fold callout pointing to `docs/e2e-walkthrough.md`, the real CLI dogfood from init through shipping with 3 parallel agent workers.
- **`examples/bug-hunt/README.md`** — rewritten. The old version was 4 self-referential commands (preflight + fixture + state) that never investigated a bug. The new version is a 30-second pitch + the 10-command pipeline + a pointer to the actual walkthrough.

### Repositioning (docs only — no runtime change)

- **README rewritten** around the actual sweet-spot positioning: *operating layer for multi-agent repository work*. New top-of-fold "When to use / When NOT to use" section explicitly tells readers to skip the harness for one-line bugs and single-file fixes.
- **New "5 stages — and when each fires" section** documents the R-P-E-R-S permutations (R-E-R hotfix · R-P-E-R multi-file · R-P-E-R-S full · R-S docs · R-only spike) and which signals the router will use to pick.
- **FAQ honesty pass**: added explicit "Should I use RePERS for a one-line bug?" entry — answers **No**, with the reason (coordination overhead with nothing to coordinate) and the recommendation (naked agent loop). The router routes around this shape of work automatically.
- **ROADMAP rewritten** to surface v0.2 (router + bug-hunt route-first + worker contract + registry trim) and v0.3 (agent-agnostic fixture proving non-Claude runtimes plug in cleanly).
- **CITATION.cff abstract** rewritten to position RePERS as the contract layer *above* agent runtimes (LangGraph / CrewAI / OpenHands), not a competitor.

## 0.1.0 - 2026-06-21

- Added an installable `.repers/` runtime with preflight, doctor, audit,
  install-hook, verify-install, package, and bundle-status commands.
- Added package manifests, package readiness sidecars, and round-trip archive
  verification.
- Added receiver smoke tests and GitHub Actions workflow coverage.
- Added open-source onboarding and governance files for contributors,
  maintainers, support, security, roadmap, and examples.
- Added a deterministic orchestration fixture that proves conflict-safe worker
  dispatch, worker-command execution, local join verification, and review
  evidence.
- Added `capabilities/registry.json` plus a `capabilities` CLI command, and
  indexed registry entries in preflight as `source=local_capability`.
- Added `release-evidence` to generate publish-readiness JSON with package,
  governance, capability registry, and Git branch/commit/remote state.
- Added `receiver-fixture` to install the package into a fresh Git repository
  and prove receiver-side commands after installation.

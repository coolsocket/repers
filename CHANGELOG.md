# Changelog

All notable RePERS bundle changes are tracked here. The format follows
[Keep a Changelog](https://keepachangelog.com/) loosely; versioning is
semantic-ish — any user-visible behavior change bumps minor or major.

## Unreleased

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

# Changelog

All notable RePERS bundle changes are tracked here. The format follows
[Keep a Changelog](https://keepachangelog.com/) loosely; versioning is
semantic-ish — any user-visible behavior change bumps minor or major.

## Unreleased

### Repositioning (docs only — no runtime change)

- **README rewritten** around the actual sweet-spot positioning: *operating layer for multi-agent repository work*. New top-of-fold "When to use / When NOT to use" section explicitly tells readers to skip the harness for one-line bugs and single-file fixes.
- **New "5 stages — and when each fires" section** documents the R-P-E-R-S permutations (R-E-R hotfix · R-P-E-R multi-file · R-P-E-R-S full · R-S docs · R-only spike) and which signals the router will use to pick.
- **FAQ honesty pass**: documented the 5.8× wall-clock overhead measured on `sqlfluff__sqlfluff-2419` (4-line patch in 1 file) — the exact shape of work the router will route around.
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

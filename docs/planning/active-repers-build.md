# Active Plan: RePERS Whole-Repo Build

## Goal

Build RePERS into a self-contained repository that can be installed by another
repository, reused by other agents, and verified without chat history.

## Non-Goals

- Do not require optional cloud SDKs for the core local workflow.
- Do not dispatch real subagents until the plan, ownership, and verification
  contracts are deterministic enough to audit.
- Do not treat package generation as complete unless round-trip installation
  passes.

## Current Evidence

- `preflight --refresh --json` returns `extend` for orchestration fixture work.
- `bundle-status --package --verify-roundtrip --json` passes for the current
  package surface.
- The CLI already exposes `preflight`, `plan`, `run`, `dispatch`, `review`,
  `shipping`, `release`, `package`, `bundle-status`, and `dag`.

## Steps

- [x] Package installed `.repers/` runtime with manifest and readiness sidecar.
- [x] Add open-source receiver files and package readiness gates.
- [x] Add deterministic large-task orchestration fixture and smoke coverage.
- [x] Add richer reusable capability registry/local skills JSON surface.
- [x] Add release-shape branch/commit/PR metadata when the repo state is ready.
- [x] Add installed receiver acceptance fixture.

## Acceptance

- `python -B .repers/scripts/repers.py fixture prove --json` returns `ok=true`.
- `python -B .repers/scripts/repers.py bundle-status --package --verify-roundtrip --json`
  returns `ok=true`.
- `python -B tests/smoke_repers.py` returns success.

## Status

Current phase: deterministic orchestration proof complete.

Validation passed with `fixture --action prove`, `verify-install`,
`bundle-status --package --verify-roundtrip`, and `tests/smoke_repers.py`.

Capability registry phase complete: `capabilities --action validate`,
`capabilities --action search`, and `preflight --refresh --json` now expose
local reusable entries from `capabilities/registry.json`.

Release evidence phase complete: `release-evidence --package --verify-roundtrip
--json` writes `dist/repers-release-evidence.json` and records package,
governance, capability registry, and Git branch/commit/remote state. In the
current uncommitted workspace it correctly reports publish actions still needed.

Receiver acceptance phase complete: `receiver-fixture --json` installs the
packaged archive into a fresh Git repository and proves `verify-install`,
`doctor`, `bundle-status`, `capabilities`, and `fixture` from the receiver.

Publish-readiness continuation: focused gates passed for `compileall`,
`capabilities --action validate`, `receiver-fixture`, `release-evidence
--package --verify-roundtrip`, `bundle-status --package --verify-roundtrip`,
and `tests/smoke_repers.py`. The local initial commit exists on
`codex/repers-initial-package`, and a temp-output publish probe now reports a
clean tree with only one remaining blocker: configure a Git remote before push
or draft PR creation.

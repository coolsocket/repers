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
- [x] Add non-destructive publish handoff artifacts for remote/push/PR steps.
- [x] Add objective completion audit with deep evidence gates.
- [x] Add remote bootstrap artifact and optional `git remote add` apply path.
- [x] Add local bare-remote fixture proving `remote-bootstrap --apply` and push.
- [x] Add objective continuation actions for autonomous handoff/resume.

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

Publish handoff phase complete: `publish-handoff --package --verify-roundtrip
--json` writes `dist/repers-publish-handoff.json` and
`dist/repers-publish-handoff.md`, reuses release evidence, and records
non-destructive commands for adding a remote, pushing the branch, and opening a
draft PR. The command is now in the capability registry and package readiness
receiver commands.

Objective audit phase complete: `objective-audit --deep --json` writes
`dist/repers-objective-audit.json` and checks the full RePERS end-state against
current evidence. The deep audit proves the local repository, receiver install,
capability registry, orchestration fixture, 10-repository structure study,
tests/package gates, and chat-free evidence. It correctly leaves
`publication_ready` incomplete until a Git remote exists.

Remote bootstrap phase complete: `remote-bootstrap --remote-url <url> --json`
writes `dist/repers-remote-bootstrap.json` and
`dist/repers-remote-bootstrap.md`, regenerates publish handoff evidence, and
keeps Git state unchanged unless `--apply` is explicitly passed. This gives the
next maintainer a concrete local command for the only remaining external step:
configuring the publication remote.

Remote apply fixture phase complete: `remote-bootstrap-fixture --json` creates
a temporary Git target, installs RePERS, creates a local bare remote, runs
`remote-bootstrap --apply`, and pushes to that bare remote. This proves the
remote mutation and branch push mechanics without requiring a hosted Git
provider.

Continuation phase complete: `objective-audit --json` now includes
`continuation` with local and external next actions, and writes
`dist/repers-continuation.md`. This keeps the remaining hosted-publication
blocker explicit while giving the next maintainer exact resume commands.

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
- [x] Add autonomous continuation runner for ready local resume actions.
- [x] Add compact repository state report for self-autonomous status handoff.
- [x] Add race-safe sequential `verify-all` local gate.
- [x] Route packaged CI workflow through `verify-all`.
- [x] Add local publish/clone fixture proving clone-side RePERS verification.
- [x] Add source checkout install fixture proving one-command receiver bootstrap
  with the pre-commit hook.

## Acceptance

- `python -B .repers/scripts/repers.py fixture prove --json` returns `ok=true`.
- `python -B .repers/scripts/repers.py bundle-status --package --verify-roundtrip --json`
  returns `ok=true`.
- `python -B .repers/scripts/repers.py publish-clone-fixture --json` returns
  `ok=true`.
- `python -B .repers/scripts/repers.py source-install-fixture --json` returns
  `ok=true` and target-side `doctor` reports the hook installed.
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

Continuation runner phase complete: `continue --json` regenerates objective
audit evidence, reports local/external resume actions, and stays dry-run by
default. `continue --apply --action-id prove_local_remote_apply --json` was
validated against the safe local remote-bootstrap fixture action, while hosted
remote setup, push, and draft PR creation remain explicit external steps.

State report phase complete: `state --json` writes `dist/repers-state.json`
and `dist/repers-state.md`, composing objective status, Git publication state,
package readiness, capability count, test evidence, and next continuation
actions. Use `state --deep --json` when the report must refresh package,
receiver, fixture, and smoke evidence before summarizing.

Sequential verification phase complete: `verify-all --json` runs install,
capability, package round-trip, receiver fixture, remote bootstrap fixture,
smoke, and deep state gates in order with isolated temporary outputs. It
reports `blocked_external` when local gates pass and the only remaining blocker
is hosted publication setup.

CI hardening phase complete: `.github/workflows/repers-smoke.yml` now runs the
single race-safe `verify-all --json` gate. Packaged smoke tests assert that the
workflow contains this command, so receiver governance and CI stay aligned.

Publish clone fixture phase complete: `publish-clone-fixture --json` copies the
current worktree into a temporary source repo, pushes it to a local bare remote,
clones it, and proves clone-side `verify-install`, capability validation, and
state reporting. The installer now writes receiver `.gitattributes` rules so
Git checkout line-ending normalization does not invalidate the installed
manifest on Windows.

Source install fixture phase complete: `install --target <target-repo> --json`
is now the one-command source checkout bootstrap path. `source-install-fixture
--json` copies the current RePERS worktree into a temporary source checkout,
creates a fresh receiver Git repository, runs that install command, and proves
target-side `verify-install`, `doctor` with the hook installed, and capability
registry validation.

# RePERS Installed Bundle

This folder is a target repository with RePERS installed under `.repers/`.

Useful commands:

```powershell
python .repers\scripts\repers.py --help
python .repers\scripts\repers.py preflight --query "capability query" --json --codegraph
python .repers\scripts\repers.py doctor --json
python .repers\scripts\repers.py verify-install --json
python .repers\scripts\repers.py bundle-status --json
python .repers\scripts\repers.py bundle-status --package --verify-roundtrip --json
python .repers\scripts\repers.py capabilities --action search --query "capability query" --json
python .repers\scripts\repers.py fixture --action prove --json
python .repers\scripts\repers.py receiver-fixture --json
python .repers\scripts\repers.py release-evidence --package --verify-roundtrip --json
python .repers\scripts\repers.py publish-handoff --package --verify-roundtrip --json
python .repers\scripts\repers.py remote-bootstrap --remote-url <remote-url> --json
python .repers\scripts\repers.py remote-bootstrap-fixture --json
python .repers\scripts\repers.py objective-audit --deep --json
python .repers\scripts\repers.py package --output dist --json
python .repers\scripts\repers.py package --output dist --verify-roundtrip --json
python .repers\scripts\repers.py install-hook --json
python tests\smoke_repers.py
```

`preflight --codegraph` is optional. It adds `code_evidence` when CodeGraph is
available and returns a structured fallback when the CLI or local index is
missing.

`bundle-status --json` is the fastest receiver health check. Add
`--package --verify-roundtrip` when you need one JSON report that also proves
the archive can be extracted, installed into a fresh Git repository, and
verified.

`package --output dist --json` creates a zip archive with embedded
`repers-package-manifest.json` and `repers-package-readiness.json` files, plus a
sidecar `repers-0.1.0-readiness.json` in `dist/` that records the final archive
hash and receiver commands. This lets the bundle be checked and re-shipped
without relying on chat history.

`fixture --action prove --json` creates a deterministic large-task DAG fixture,
dispatches three worker-command lanes through conflict-safe batches, runs a
local join verification step, and emits `repers.orchestration_fixture.v1`.
Use it as the fastest proof that the supervisor/worker DAG path is wired before
trying optional external agent backends.

`capabilities --action search --query "..." --json` queries the packaged
`capabilities/registry.json` inventory. `preflight --refresh --json` indexes
the same registry as `source=local_capability`, so reusable scripts, hooks,
templates, package gates, and harnesses can be found without rereading the
whole repository.

`release-evidence --package --verify-roundtrip --json` writes
`dist/repers-release-evidence.json`. It records package, governance, capability
registry, and Git branch/commit/remote state. During active development it can
report `publish_ready=false` while still proving the package and local release
checks are valid.

`publish-handoff --package --verify-roundtrip --json` writes
`dist/repers-publish-handoff.json` and `dist/repers-publish-handoff.md`. It
turns release evidence into a non-destructive remote/push/draft-PR checklist so
another agent or maintainer can finish publication without relying on chat
history.

`remote-bootstrap --remote-url <remote-url> --json` writes
`dist/repers-remote-bootstrap.json` and `dist/repers-remote-bootstrap.md`. By
default it does not change Git state; it records the remote setup, publish
handoff, objective audit, push, and draft PR commands. Add `--apply` only when
you want it to run `git remote add`; existing remotes with different URLs are
not overwritten.

`remote-bootstrap-fixture --json` proves the apply path without external
network access. It creates a temporary Git repository, installs RePERS, creates
a local bare remote, runs `remote-bootstrap --apply`, and pushes the fixture
branch to that bare remote.

`objective-audit --deep --json` writes `dist/repers-objective-audit.json`. It
checks the whole repository against the RePERS end-state: installability,
receiver reuse, capability registry, deterministic DAG proof, open-source
structure study, tests/package gates, chat-free evidence, and publication
readiness.

The objective audit also writes `dist/repers-continuation.md` and embeds a
`repers.objective_continuation.v1` object in JSON. That continuation section
splits executable local resume commands from external actions such as providing
a hosted Git remote URL.

`continue --json` consumes that continuation object as the autonomous resume
surface. It defaults to a dry-run report and only runs ready local actions when
`--apply` is passed; remote setup, push, and draft PR creation remain explicit
external steps.

`state --json` is the compact repository dashboard. It writes
`dist/repers-state.json` and `dist/repers-state.md`, combining objective status,
Git publish readiness, package state, capability count, test evidence, and the
next continuation actions.

`receiver-fixture --json` installs the packaged archive into a fresh Git
repository and runs receiver-side checks: `verify-install`, `doctor`,
`bundle-status`, `capabilities`, and `fixture`. Use it before handing the
archive to another repository.

When packaging from an installed `.repers/` bundle, the archive also carries
this receiver `README.md` and `tests/` smoke coverage at the top level of the
archive, alongside the installable RePERS runtime files.

The receiver package also includes open-source promotion signals derived from
the 10-repository structure study in `.repers/docs/open-source-structure-study.md`:
`CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `ROADMAP.md`, `CHANGELOG.md`,
`MAINTAINERS.md`, `.github/workflows/repers-smoke.yml`, and
`examples/basic-task/README.md`. Package readiness fails if these signals are
missing.

Round-trip receiver check:

```powershell
python .repers\scripts\repers.py package --output dist --verify-roundtrip --json
```

Manual receiver check:

```powershell
python .repers\scripts\repers.py package --output dist --json
Expand-Archive dist\repers-0.1.0.zip -DestinationPath .repers-roundtrip
git init .repers-roundtrip-target
python .repers-roundtrip\repers-0.1.0\scripts\install_repers.py --target .repers-roundtrip-target --no-hook
python .repers-roundtrip-target\.repers\scripts\repers.py verify-install --json
```

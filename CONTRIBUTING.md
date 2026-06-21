# Contributing to RePERS

RePERS is a local-first workflow operating layer. Contributions should preserve
the core contracts: preflight before new capability, explicit artifacts, and
machine-readable verification.

## Development Loop

Use the installed bundle from the repository root:

```powershell
python .repers\scripts\repers.py preflight --query "your change" --refresh --json
python .repers\scripts\repers.py bundle-status --json
python .repers\scripts\repers.py bundle-status --package --verify-roundtrip --json
python tests\smoke_repers.py
```

## Change Rules

- Reuse existing CLI commands, scripts, and docs before adding new surfaces.
- Keep runtime state out of packages: no `.repers/index`, `.codegraph`,
  `repers_tasks`, `dist`, caches, or temporary files.
- Add or update smoke coverage when a command contract changes.
- Prefer small JSON contracts that another agent or maintainer can inspect.

## Release Readiness

A handoff is not ready unless `bundle-status --package --verify-roundtrip --json`
returns `ok=true` and the package readiness warnings list is empty.

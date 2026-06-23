<!-- Thanks for the PR. Fill in what applies; delete the rest. -->

## What

<!-- One paragraph. -->

## Why

<!-- The problem this solves or feature it adds. Link issue: Closes #N -->

## Type

- [ ] 🧩 Capability change (`.repers/capabilities/registry.json` or `.repers/scripts/*.py`)
- [ ] 🪝 Hook change (`.repers/hooks/*`)
- [ ] 🧠 Codex skill change (`skills/<name>/SKILL.md`)
- [ ] 📦 Package / release-pack change (`dist/` generators)
- [ ] 🧪 CI / smoke change (`.github/workflows/`, `tests/`)
- [ ] 📚 Docs only
- [ ] 🚨 Breaking change for receivers (explain compat below)

## Preflight evidence

<!--
Before adding new surfaces, paste the preflight output that confirms nothing
duplicate exists. Skip only if this is a pure bugfix or docs-only PR.
-->

```json
$ python .repers/scripts/repers.py preflight --query "<your change>" --refresh --json
{...}
```

## Test evidence

<!--
For runtime changes: paste relevant output from one or more gates.
At minimum, `verify-all --json` should still pass.
-->

```
$ python .repers/scripts/repers.py verify-all --json | head -20
{...}

$ python tests/smoke_repers.py
ok
```

For hook changes, also include a fake-commit reproduction.
For capability changes, include the `capabilities --action validate --json` output.

## Checklist

- [ ] `python .repers/scripts/repers.py verify-all --json` passes
- [ ] `python tests/smoke_repers.py` passes
- [ ] If user-visible: `version` bumped in `.codex-plugin/plugin.json` (and `registry.json` if the registry shape changed)
- [ ] README "Skills" / "Capabilities" / "Core commands" tables updated if relevant
- [ ] `CHANGELOG.md` updated under `Unreleased`
- [ ] No new runtime dependencies (stdlib Python only)
- [ ] No runtime state added to package outputs (`.repers/index/`, `repers_tasks/`, caches stay excluded)

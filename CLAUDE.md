# CLAUDE.md — contributing to the RePERS harness itself

This repo IS the [RePERS](https://github.com/coolsocket/repers) harness.
It ships a `.repers/` runtime (Python CLI + capability registry + hooks +
templates + fixtures), 4 Codex skills, governance docs, a release pack, and
machine-readable JSON evidence for every gate.

If you're **using** RePERS in another project, see that project's README
(installed by `python .repers/scripts/repers.py install --target <repo>` or
`/repers-init` in Codex). **This file is just for editing RePERS itself.**

## What lives where

```
.repers/scripts/        Python CLI (repers.py) + per-capability scripts + installer
.repers/capabilities/   registry.json — canonical inventory of 24 reusable workflows
.repers/hooks/          pre-commit hook (warn / strict policies)
.repers/templates/      files copied into receiver repos at install time
.repers/docs/           internal architecture / spec / workflow notes
.repers/manifest.json   runtime manifest (versions, file fingerprints)
skills/                 4 Codex skills (repers-init / -bug-hunt / -release-pack / -sinkin)
.codex-plugin/          plugin.json for the Codex marketplace
.github/                CI workflow + issue / PR templates + social preview
docs/                   public-facing docs (bug-hunt demo, release checklist, promo)
examples/               runnable adoption examples (basic-task, bug-hunt)
tests/                  smoke_repers.py — end-to-end receiver test
dist/                   generated packages + evidence JSON + markdown summaries
PITFALLS.md             cross-project pitfalls (this repo's responsibility to curate)
```

## Editing rules

| Editing this | Do this |
|---|---|
| `.repers/scripts/*.py` | Run `python tests/smoke_repers.py` after the edit. Keep stdlib-only (no new deps). |
| `.repers/scripts/repers.py` | If you add a subcommand, register it in `capabilities/registry.json` AND mention it in README "Core commands". |
| `.repers/capabilities/registry.json` | Bump `version` if entries change shape. Re-run `python .repers/scripts/repers.py capabilities --action validate --json`. |
| `.repers/hooks/pre-commit` | Test with `python .repers/scripts/repers.py install-hook --hook-policy warn` then a fake commit. |
| `.repers/templates/**` | These get copied verbatim into receiver repos. Don't reference the RePERS repo or maintainer specifics. |
| `skills/<name>/SKILL.md` | Front-matter `name:` + `description:` required. Keep description specific enough that Codex knows when to invoke. |
| `.codex-plugin/plugin.json` | Bump `version` whenever shipped behavior changes. |
| `README.md` "Skills" / "Hooks" / "Commands" tables | Keep in sync when adding the corresponding artifact. |
| `dist/*` | Regenerate via `python .repers/scripts/repers.py release-pack --json`, don't hand-edit. |

## Release flow

The full pre-publish gate is in [`MAINTAINERS.md`](./MAINTAINERS.md). Short form:

1. Bump `.codex-plugin/plugin.json` `version` + `.repers/capabilities/registry.json` `version` if registry shape changed
2. `python .repers/scripts/repers.py bundle-status --package --verify-roundtrip --json` → `ok: true`
3. `python .repers/scripts/repers.py fixture --action prove --json` → `ok: true`
4. `python .repers/scripts/repers.py receiver-fixture --json` → `ok: true`
5. `python .repers/scripts/repers.py release-evidence --package --verify-roundtrip --json`
6. `python tests/smoke_repers.py`
7. `python .repers/scripts/repers.py release-pack --json` → refreshes `dist/repers-release-pack.zip`
8. Update `CHANGELOG.md` (Unreleased → vX.Y.Z + date)
9. `git commit -am "repers vX.Y.Z: <one-line change>"`
10. `git push && gh release create vX.Y.Z dist/repers-X.Y.Z.zip dist/repers-release-pack.zip`

## When NOT to add stuff

- **A new capability** that duplicates an existing entry in `registry.json` — preflight first, extend the existing one.
- **A new skill** that just wraps one CLI call — keep skills load-bearing (multi-step + reasoning instructions).
- **A new pitfall** that's only happened once — wait for cross-session recurrence (this is what `/repers-sinkin` is for).
- **Runtime state in the package** (`.repers/index/`, `repers_tasks/`, `.codegraph/`, caches) — the package gate will refuse.
- **Heavy dependencies** — runtime is stdlib-only Python by design.

## When adding things

- **New capability** → add entry to `.repers/capabilities/registry.json`, implement script under `.repers/scripts/`, mention in README "Core commands" table.
- **New skill** → `skills/<name>/SKILL.md` with frontmatter; mention in README "Skills" table; reference from one of the CLI gates.
- **New pitfall** → `PITFALLS.md` under the right category, with `_Source:_` line for traceability.
- **New CI gate** → `.github/workflows/<name>.yml`; gate should call an existing `repers.py` subcommand, not introduce parallel logic.

## Reference: what RePERS does in receiver projects (NOT in this repo)

If you're confused why this repo doesn't have a `repers_tasks/` workspace or
its own `.repers/index/repers.db` worth examining: this repo IS the harness.
The `dist/repers-0.1.0.zip` is what gets installed into receiver projects to
give them the workflow this codebase implements.

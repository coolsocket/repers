# RePERS Packaging Roadmap

## Current Package Shape

RePERS ships as a local repository bundle:

- `scripts/repers.py`: CLI entrypoint.
- `scripts/dag_engine.py`: Markdown DAG parser and status updater.
- `scripts/install_repers.py`: target repository installer.
- `templates/*.md`: task artifact templates.
- `hooks/pre-commit`: visible hook template.
- `docs/*.md`: user-facing installation and contract docs.
- `manifest.json`: installed bundle version, source state, hook policy, and copied file inventory with SHA-256 hashes.
- `repers-<version>.zip`: distributable source archive created by
  `repers package`, with an embedded `repers.package_manifest.v1` manifest.
- Optional CodeGraph integration through the target machine's existing CLI or
  `CODEGRAPH_BIN`.
- Optional LangGraph SQLite checkpointing when the target environment provides
  the `langgraph-checkpoint-sqlite` package.

The installer copies these into `.repers/` inside a target Git repository,
writes `.repers/manifest.json`, and writes `.git/hooks/pre-commit`.
The installed CLI can verify the manifest later with `verify-install`.
The source checkout can also create a zip archive for handoff:

```powershell
python scripts\repers.py package --output dist --json
```

## Why This First

This keeps the first install path simple and auditable:

- no PyPI publishing
- no global PATH mutation
- no shell profile edits
- no hidden dependency on Codex internals
- no dependency manager requirement
- no bundled CodeGraph binary; structural evidence is enabled only when the
  target environment already provides it

## Next Packaging Steps

1. Add OpenAI Agents handoffs, guardrails, and richer trace capture on top of the guarded function-tool adapter.
2. Add human-in-the-loop state on top of the LangGraph memory/sqlite checkpoint paths.
3. If usage stabilizes, promote the CLI to a Python package with a console script.

## Install Manifest

Each install writes `.repers/manifest.json` using schema
`repers.install_manifest.v1`. The manifest records:

- RePERS bundle version.
- source and target paths.
- source Git commit and dirty status when available.
- hook policy and hook path.
- copied file count.
- per-file path, size, and SHA-256 hash.

`install-hook` updates the manifest hook policy when a bundle already has a
manifest.

Verify a copied bundle from the target repository with:

```powershell
python .repers\scripts\repers.py verify-install --json
```

This reports missing, changed, and extra files. Extra non-runtime files are
allowed by default and can be made fatal with `--strict-extra`.

## Release Gate

Before handing off a bundle, run:

```powershell
python scripts\repers.py release --task autonomous_repers --installed-target C:\path\to\target-repo --json
```

This writes `repers_tasks/<task>/release.json` and combines review, doctor,
shipping, audit, installed manifest evidence, and installed manifest
verification into one machine-readable gate.

## Package Archive

`repers package` writes `dist/repers-<version>.zip` by default. The archive
contains the reusable install surface and intentionally excludes local runtime
state and task workspaces. The embedded `repers-package-manifest.json` records
the source Git state, copied files, sizes, and SHA-256 hashes so a recipient can
inspect exactly what was shipped.

## Hook Policy

The default hook is intentionally conservative:

- It runs `audit`.
- It blocks only audit errors.
- It allows warnings so early adoption does not interrupt normal commits.
- It can be installed in strict mode with `--hook-policy strict`, which makes warnings fail the hook.
- `REPERS_AUDIT_STRICT_WARNINGS=1` forces strict behavior for a single hook run.
- It supports `REPERS_SKIP_HOOK=1` for local bypass.

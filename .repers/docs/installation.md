# RePERS Installation

RePERS can be installed into any Git repository as a local `.repers/` bundle.
The installer copies the CLI, templates, and docs, then optionally installs a
Git `pre-commit` hook.

## Install Into A Repository

From the RePERS source checkout:

```powershell
python scripts\install_repers.py --target C:\path\to\target-repo
```

This creates:

- `.repers/manifest.json`
- `.repers/scripts/repers.py`
- `.repers/scripts/dag_engine.py`
- `.repers/templates/*.md`
- `.repers/docs/*.md`
- `.git/hooks/pre-commit`

## Run Manually

From the target repository:

```powershell
python .repers\scripts\repers.py audit
python .repers\scripts\repers.py init --task "my task"
python .repers\scripts\repers.py preflight --query "my capability" --json --codegraph
python .repers\scripts\repers.py dag --task my_task --action list
python .repers\scripts\repers.py install-hook --json
python .repers\scripts\repers.py install-hook --hook-policy strict --json
python .repers\scripts\repers.py verify-install --json
python .repers\scripts\repers.py doctor --fix --refresh-index --json
```

`preflight --codegraph` is optional. It reuses the normal RePERS preflight
artifact and adds `code_evidence` when CodeGraph is available. If CodeGraph or
the `.codegraph/` index is missing, the command still returns JSON with a
structured reason in `code_evidence.errors`.

## Hook Behavior

The installed `pre-commit` hook runs:

```sh
python .repers/scripts/repers.py audit
```

The hook sets `REPERS_WORKSPACE_ROOT` to the Git repository root before it runs,
so task artifacts and audits target the installed repository rather than the
`.repers/` bundle.

By default, audit warnings do not block commits. To make warnings block commits,
install the hook with:

```powershell
python .repers\scripts\repers.py install-hook --hook-policy strict
```

You can also force strict behavior for a single hook run:

```powershell
$env:REPERS_AUDIT_STRICT_WARNINGS = "1"
git commit
```

Manual commands also infer the parent Git repository when launched from the
installed `.repers\scripts` directory. Set `REPERS_WORKSPACE_ROOT` only when you
need to override that default.

To bypass the hook locally:

```powershell
$env:REPERS_SKIP_HOOK = "1"
git commit
```

## Repair An Existing Bundle

If `.repers/` was copied without a hook, or if the local index is missing, run:

```powershell
python .repers\scripts\repers.py doctor --fix --refresh-index --json
```

`doctor --fix` reuses the installer hook writer and local indexer. It does not
install third-party packages.

## Inspect The Installed Bundle

Every install writes `.repers/manifest.json`. Use it to confirm the installed
bundle version, hook policy, source Git state, copied files, and SHA-256 hashes.
Shipping evidence also reads this manifest when `shipping --installed-target`
is used.

To verify that the installed files still match the manifest:

```powershell
python .repers\scripts\repers.py verify-install --json
```

Use `--strict-extra` when unrecorded non-runtime files inside `.repers/` should
fail verification.

## Current Limits

- The installer is intentionally local-first. It does not publish to PyPI.
- The hook defaults to warning-tolerant mode; use strict policy when warnings should block commits.
- Python must be available as `python`.
- Optional LSP Guard checks depend on the local Codex Agent Tools installation.
- Optional CodeGraph evidence depends on `codegraph` on PATH, `CODEGRAPH_BIN`,
  or the known local CodeGraph checkout.

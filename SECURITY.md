# Security Policy

RePERS is currently a local repository bundle. It does not run a network service
or publish a package registry artifact.

## Reporting Issues

For now, report security concerns to the repository owner through the same
private channel used to receive this bundle. Do not include secrets, private
repository contents, or full local paths unless they are required to reproduce
the issue.

## Security Boundaries

- The installer copies files into `.repers/` and can install a Git pre-commit
  hook.
- The default hook policy allows warnings; strict mode is opt-in with
  `install-hook --hook-policy strict`.
- Package archives exclude runtime state and task workspaces.
- Optional worker backends must preserve declared target-file boundaries.

## Verification

Run the receiver status gate after install:

```powershell
python .repers\scripts\repers.py bundle-status --json
```

Run the full package gate before sharing a bundle:

```powershell
python .repers\scripts\repers.py bundle-status --package --verify-roundtrip --json
```

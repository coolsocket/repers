# Support

RePERS is packaged as a local, installable agent workflow bundle. Start with the
receiver health check before opening a support request:

```powershell
python .repers\scripts\repers.py bundle-status --package --verify-roundtrip --json
```

Include the command output, the operating system, Python version, and a short
description of the target repository when reporting a problem.

Use these triage paths:

- Installation or packaging failure: include `verify-install`, `doctor`, and
  `package --verify-roundtrip` output.
- Preflight quality issue: include the `preflight --query "<query>" --refresh
  --json` output and the files or capability you expected it to find.
- Hook issue: include `.repers/repers-install-manifest.json`, the hook policy,
  and the failing Git command.


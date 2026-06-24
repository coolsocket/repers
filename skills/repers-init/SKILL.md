---
name: repers-init
description: Install or verify the RePERS harness in the current Git repository. Use when adopting RePERS, refreshing the local .repers runtime, installing the pre-commit hook, or checking whether a repo is ready for RePERS workflows.
---

# repers-init

> **Layer**: ⚙️ **Infrastructure** (pre-R) — installs the contract so the R/P/E/R/S layers can be invoked. Not part of the pipeline itself. Run once per repo.

Initialize or verify RePERS for the current repository.

## Procedure

1. Confirm the current directory is the intended Git repository root.
2. If `.repers/scripts/repers.py` exists, run:

   ```powershell
   python3 .repers/scripts\repers.py verify-install --json
   python3 .repers/scripts\repers.py doctor --json
   ```

3. If RePERS exists but the manifest is stale, run:

   ```powershell
   python3 .repers/scripts\repers.py refresh-manifest --json
   ```

4. If the hook is missing or the user asks for hooks, run:

   ```powershell
   python3 .repers/scripts\repers.py install-hook --hook-policy warn --json
   ```

5. If `.repers/` is missing, install from a source checkout or release archive:

   ```powershell
   python <repers-source>\.repers\scripts\repers.py install --target <target-repo> --json
   ```

## Done Criteria

- `verify-install --json` returns `ok=true`.
- `doctor --json` reports the runtime and hook state.
- If a hook was requested, `.git/hooks/pre-commit` exists and `doctor` reports it.

## Notes

The Codex plugin supplies this skill. The reusable runtime still lives under
`.repers/` inside the target repository so the workflow remains chat-free and
verifiable.

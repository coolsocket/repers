---
name: repers-bug-hunt
description: "Run the RePERS bug-hunt workflow for a repository issue: preflight reusable capabilities, create or reuse a task DAG, gather evidence, review findings, and run focused verification before reporting."
---

# repers-bug-hunt

Use this skill when the user asks Codex to find, reproduce, or fix a bug and
the repository has RePERS installed.

## Procedure

1. Run preflight with the user's bug description:

   ```powershell
   python .repers\scripts\repers.py preflight --query "<bug or symptom>" --refresh --json
   ```

2. Search the local capability registry for likely reusable gates:

   ```powershell
   python .repers\scripts\repers.py capabilities --action search --query "<bug or subsystem>" --json
   ```

3. Create or reuse the task plan:

   ```powershell
   python .repers\scripts\repers.py init --task "<task-name>"
   python .repers\scripts\repers.py plan --task "<task-name>" --json
   ```

4. Keep worker lanes evidence-based. When external subagents are unavailable,
   use the deterministic fixture to prove the DAG/review contract:

   ```powershell
   python .repers\scripts\repers.py fixture --action prove --json
   ```

5. After investigation or patching, run focused tests first, then the smallest
   relevant RePERS gate. For packaging or release bugs, prefer:

   ```powershell
   python .repers\scripts\repers.py release-pack-verify --archive dist\repers-release-pack.zip --json
   python .repers\scripts\repers.py verify-all --json
   ```

## Report Shape

Lead with:

- bug found or not found;
- evidence paths and commands;
- patch summary, if a patch was made;
- verification results;
- unresolved risks.

Do not treat a chat explanation as sufficient evidence when RePERS can write a
task artifact or JSON gate.

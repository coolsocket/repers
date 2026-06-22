# Bug Hunt Example

This example shows the smallest RePERS run shape for a bug-investigation task.

## Request

```text
Find why a release pack verifier would fail to catch a broken checksum.
```

## Commands

From a repository with RePERS installed:

```powershell
python .repers\scripts\repers.py preflight --query "release pack checksum bug" --refresh --json
python .repers\scripts\repers.py capabilities --action search --query "release pack verify checksum" --json
python .repers\scripts\repers.py fixture --action prove --json
python .repers\scripts\repers.py state --deep --json
```

## Expected Shape

- Preflight returns the closest reusable capabilities before new work starts.
- The deterministic fixture proves the DAG and worker-lane contract.
- State output records package, tests, capability count, and continuation
  actions.
- A real bug fix should then add focused reproduction, patch, and verification
  artifacts under `repers_tasks/<task>/` and `dist/`.

## What To Reuse

Search these capability IDs first:

- `preflight`
- `capability-registry`
- `orchestration-fixture`
- `release-pack`
- `release-pack-verify`
- `verify-all`

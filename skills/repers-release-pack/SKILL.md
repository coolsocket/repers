---
name: repers-release-pack
description: Build, verify, and publish-ready check a RePERS release pack. Use when preparing a GitHub Release, validating dist artifacts, refreshing release evidence, or handing the harness to another repo.
---

# repers-release-pack

> **Layer**: 🔗 **S** (Shipping) — the export layer. Makes the harness consumable across repo / team / vendor / trust boundaries by packing it into a checksum-verifiable archive another agent can re-verify without trusting the sender.

Build and verify the installable RePERS handoff.

## Procedure

1. Start from a clean or intentionally understood worktree:

   ```powershell
   git status --short
   ```

2. Build the installable archive and round-trip it into a fresh receiver:

   ```powershell
   python3 .repers/scripts\repers.py package --output dist --verify-roundtrip --json
   ```

3. Build the release pack:

   ```powershell
   python3 .repers/scripts\repers.py release-pack --json
   ```

4. Verify the release pack archive:

   ```powershell
   python3 .repers/scripts\repers.py release-pack-verify --archive dist\repers-release-pack.zip --json
   ```

5. Run the full sequential local gate before publishing:

   ```powershell
   python3 .repers/scripts\repers.py verify-all --json
   ```

## Required Release Assets

- `repers-0.1.0.zip`
- `repers-release-pack.zip`
- `repers-release-pack.json`
- `repers-release-pack.md`

## Publish Notes

The release pack command is non-mutating: it does not add remotes, push
branches, or open pull requests. Use Git/GitHub tools only after local gates
pass and the user wants publication.

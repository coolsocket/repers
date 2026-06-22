---
name: repers-sinkin
description: Audit a RePERS workspace for drift between README, plugin skills, capability registry, package gates, release assets, and generated evidence. Use periodically after packaging, publication, or major workflow edits.
---

# repers-sinkin

Run a non-mutating RePERS drift check. Report findings and recommended actions;
do not auto-fix unless the user asks.

## Procedure

1. Check Git and current state:

   ```powershell
   git status --short
   python .repers\scripts\repers.py state --deep --json
   ```

2. Validate local capabilities:

   ```powershell
   python .repers\scripts\repers.py capabilities --action validate --json
   python .repers\scripts\repers.py open-source-benchmark --json
   ```

3. Verify package and release pack surfaces:

   ```powershell
   python .repers\scripts\repers.py package --output dist --verify-roundtrip --json
   python .repers\scripts\repers.py release-pack --json
   python .repers\scripts\repers.py release-pack-verify --archive dist\repers-release-pack.zip --json
   ```

4. Compare public docs with actual package contents:

   - README install path;
   - plugin skills under `skills/`;
   - `.codex-plugin/plugin.json`;
   - capability registry entries;
   - release checklist and published release assets.

## Report Shape

Use HIGH/MED/LOW priorities:

- HIGH: package or verification claims contradict current evidence.
- MED: plugin/README/capability registry drift.
- LOW: copy, metadata, or promotion improvements.

End with exact commands for the next maintainer.

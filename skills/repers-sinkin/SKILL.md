---
name: repers-sinkin
description: Audit a RePERS workspace for drift between README, plugin skills, capability registry, package gates, release assets, and generated evidence. Use periodically after packaging, publication, or major workflow edits.
---

# repers-sinkin

> **Layer**: 🧠 **R** (meta-Memory) — audits the harness's own knowledge layer. Detects drift between sediment (README / registry / skills / dist) and live state so the memory layer stays honest. Run periodically; not part of normal task flow.

Run a non-mutating RePERS drift check. Report findings and recommended actions;
do not auto-fix unless the user asks.

## Procedure

1. Check Git and current state:

   ```powershell
   git status --short
   python3 .repers/scripts\repers.py state --deep --json
   ```

2. Validate local capabilities:

   ```powershell
   python3 .repers/scripts/repers.py capabilities --action validate --json
   ```

3. Verify package and release pack surfaces:

   ```powershell
   python3 .repers/scripts\repers.py package --output dist --verify-roundtrip --json
   python3 .repers/scripts\repers.py release-pack --json
   python3 .repers/scripts\repers.py release-pack-verify --archive dist\repers-release-pack.zip --json
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

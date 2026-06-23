# RePERS — pitfalls

> Cross-project, generalizable "did X, hit Y" lessons.
> **Project-specific gotchas** belong in that project's own `.repers/PITFALLS.md`.
>
> New entries cite a source (date + commit / session id / dist artifact) so
> we can verify the lesson didn't decay.
>
> Curated with help from `/repers-sinkin`; entries land here only after a
> human confirms cross-session recurrence.

---

## Package & release engineering

### Runtime state leaks into the package archive

The first packaging passes shipped `.repers/index/repers.db`, `repers_tasks/`,
and `.codegraph/` caches inside `repers-0.1.0.zip`. Receivers then booted with
*another repo's* preflight index — invisible, very confusing.

**Symptom**: `preflight --query "..."` on a freshly-installed receiver returns
results from the sender's codebase. `bundle-status --verify-roundtrip` reports
unexpected file count after extraction.

**Fix**: the package manifest must explicitly exclude runtime state. Treat
`bundle-status --package --verify-roundtrip --json` as the gate — if file
count diverges from manifest, the archive is wrong, not the verifier.

```powershell
python .repers\scripts\repers.py bundle-status --package --verify-roundtrip --json
```

- _Source: dist/repers-state.md, 2026-06-21 release readiness review_

### Two-file version bump is easy to forget

A user-visible change requires bumping **both** `.codex-plugin/plugin.json`
`version` AND `.repers/capabilities/registry.json` `version` (if the registry
shape changed). One without the other means receivers see a "new" plugin
pointing at an unchanged registry — silent inconsistency.

**Fix**: the release gate in `MAINTAINERS.md` runs `release-evidence
--verify-roundtrip` which compares both versions. Trust the gate, not memory.

- _Source: MAINTAINERS.md release-gate checklist, 2026-06-22_

---

## Agent orchestration

### "Just dispatch parallel workers" sounds safe but isn't

Naively splitting a task across N workers writing to overlapping file globs
produces last-write-wins merges that destroy intermediate work. The
deterministic orchestration fixture in `repers.py fixture --action prove`
exists *specifically* to catch this before a real agent backend runs.

**Symptom**: parallel run looks fast, final diff is missing changes from one
or more workers, no error surfaces.

**Fix**: every multi-lane plan must declare `target_files` per lane. The DAG
engine refuses to start a step whose target overlaps a still-running peer.
The fixture proves conflict-safe batching without needing real agents:

```powershell
python .repers\scripts\repers.py fixture --action prove --json
```

If `conflict_safe: false` in the output, the plan is unsafe regardless of
which backend you point at it.

- _Source: dist/repers-verify-all.json fixture section, 2026-06-22_

### Preflight before planning, not after

Adding a "new" capability that already exists in `capabilities/registry.json`
fragments the harness. Every multi-step request should start with `preflight
--query "<intent>"` — if a capability matches, extend it; don't make a sibling.

**Symptom**: registry grows past 30 entries with near-duplicates;
`/repers-sinkin` flags drift between README "Core commands" and registry IDs.

**Fix**: preflight is intentionally cheap (~50 ms on a cold registry). Always
run it. CLAUDE.md formalizes this as an edit rule.

- _Source: ROADMAP.md "Current" section + /repers-sinkin drift rule, 2026-06-22_

---

## Codex plugin development

### Cached plugin install survives source changes

After editing a plugin file locally, the running Codex session keeps using
the in-memory snapshot. Even after `/plugin update repers` the cache may not
refresh if the marketplace source is a local path.

**Symptom**: edits to `skills/<name>/SKILL.md` don't take effect; Codex
keeps quoting the old description.

**Fix**:
```
/plugin marketplace update repers
/plugin uninstall repers
/plugin install repers
# if still stale: exit and re-open the Codex session
```

- _Source: cross-project recurrence with t3d plugin migration, 2026-06-21_

### Plugin source migration leaves stale path references

Moving a plugin from a local-dir marketplace to `github.com/owner/repo` (or
renaming the directory) doesn't update in-flight sessions. The plugin
registry is loaded into memory at session start.

**Quick fix** (don't restart): symlink old path → new path.
**Permanent fix**: restart the agent session after any plugin source change.

- _Source: parallel pitfall observed in t3d migration, 2026-06-21_

---

## Template for new entries

```markdown
### <one-line title: behavior / symptom>

<2-4 lines: what was attempted / why it failed / how to avoid>

**Symptom**: <observable evidence>

**Fix**:
\`\`\`
<minimal repro + fix snippet>
\`\`\`

- _Source: <dist artifact OR session id OR commit>, YYYY-MM-DD_
```

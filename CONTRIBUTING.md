# Contributing to RePERS

Thanks for considering a contribution. RePERS is a local-first workflow
operating layer with hard rules: **preflight before new capability**,
**explicit artifacts**, and **machine-readable verification**. Small PRs that
respect those rules are very welcome.

---

## Local dev loop

```bash
git clone https://github.com/coolsocket/repers.git
cd repers

# install locally as a Codex plugin (optional — only if you're editing skills):
/plugin marketplace add ./.
/plugin install repers

# after edits, run the development gate from the repo root:
python .repers/scripts/repers.py preflight --query "your change" --refresh --json
python .repers/scripts/repers.py bundle-status --json
python .repers/scripts/repers.py bundle-status --package --verify-roundtrip --json
python .repers/scripts/repers.py verify-all --json
python tests/smoke_repers.py
```

Test a fresh-receiver install before any release:

```bash
# install into a throwaway repo and run the receiver gate:
mkdir /tmp/repers-receiver && cd /tmp/repers-receiver && git init -q
python /path/to/repers/.repers/scripts/repers.py install --target . --json
python .repers/scripts/repers.py verify-install --json
python .repers/scripts/repers.py doctor --json
```

The `receiver-fixture` capability automates this end-to-end:

```bash
python .repers/scripts/repers.py receiver-fixture --json
```

---

## Change rules

- **Reuse first.** Run `preflight --query "<intent>"` BEFORE adding a new capability, CLI subcommand, or skill. The registry already has 24 entries — extend one before adding a sibling.
- **No runtime state in packages.** `.repers/index/`, `repers_tasks/`, `.codegraph/`, `dist/`, caches, and temp files must stay out of the install archive. The `bundle-status --verify-roundtrip` gate catches this.
- **Stdlib only.** The runtime is pure-stdlib Python. New dependencies need a maintainer-level discussion first.
- **Every gate returns JSON.** Human Markdown summaries are fine alongside, but the JSON is the contract.
- **Smoke coverage moves with the contract.** If a command's JSON output shape changes, update `tests/smoke_repers.py` in the same PR.

---

## Releasing

Full pre-publish gate lives in [`MAINTAINERS.md`](./MAINTAINERS.md). Summary:

1. Bump `.codex-plugin/plugin.json` `version` (+ `registry.json` `version` if registry shape changed).
2. `python .repers/scripts/repers.py bundle-status --package --verify-roundtrip --json` → `ok: true`.
3. `python .repers/scripts/repers.py verify-all --json` → all gates green.
4. `python .repers/scripts/repers.py release-pack --json` → refreshes `dist/repers-release-pack.zip`.
5. Update `CHANGELOG.md` (Unreleased → v0.X.Y + date).
6. `git commit -am "repers v0.X.Y: <one-line change>" && git push`.
7. `gh release create v0.X.Y dist/repers-0.X.Y.zip dist/repers-release-pack.zip`.

---

## PR conventions

- **Title**: imperative, short. "Fix preflight rank for local_capability source", not "fix the bug".
- **One concern per PR.** Capability + skill + README rewrite ≠ same PR.
- **Fill the [PR template](.github/pull_request_template.md)** — especially the preflight evidence + test evidence sections.

---

## What good PRs look like

- A **new capability** with a registry entry, an implementation script, a verification command, and a README "Capabilities" row — proven by `capabilities --action validate --json`.
- A **bugfix to a gate** with: failing-case JSON before, passing-case JSON after, and a `verify-all --json` snippet.
- A **new pitfall in PITFALLS.md** with a clear `_Source:_` line proving cross-session or cross-project recurrence (not "I think this might happen").
- A **smoke test addition** that pins down a contract another agent would otherwise have to discover by failing.
- A **CI matrix expansion** (Linux / macOS) — the current `repers-smoke.yml` only runs Windows.

---

## What we'd push back on

- Adding heavy dependencies (Node, Docker, a database, a vendored binary). The runtime is intentionally stdlib Python.
- Generalizing for "any backend" too early. Cloud agent integrations are explicitly optional adapters; the deterministic fixture is the contract.
- Skills that just wrap one CLI call. Skills should carry actual multi-step reasoning instructions.
- New evidence artifacts that duplicate `verify-all`. If you need richer evidence, extend the existing JSON shape.
- Bypassing the package readiness gate ("it works on my machine"). The gate is the gate.

For open-ended questions or design discussions, prefer [GitHub Discussions](https://github.com/coolsocket/repers/discussions) over an issue.

For security disclosures, see [`SECURITY.md`](./SECURITY.md).

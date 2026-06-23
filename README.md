<div align="center">

# RePERS

**Reusable Planning, Execution, Review, and Release — a local-first harness that turns a vague engineering request into a repeatable, verifiable agent workflow.**

[![Version](https://img.shields.io/github/v/release/coolsocket/repers?label=version&color=purple)](https://github.com/coolsocket/repers/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Capabilities: 24](https://img.shields.io/badge/capabilities-24-orange.svg)](./.repers/capabilities/registry.json)
[![Skills: 4](https://img.shields.io/badge/skills-4-green.svg)](./skills/)
[![CI](https://github.com/coolsocket/repers/actions/workflows/repers-smoke.yml/badge.svg)](https://github.com/coolsocket/repers/actions/workflows/repers-smoke.yml)
[![GitHub stars](https://img.shields.io/github/stars/coolsocket/repers?style=flat&color=yellow)](https://github.com/coolsocket/repers/stargazers)

🚀 [Install](#-install) · 🔧 [Daily workflow](#-daily-workflow) · 🧠 [Skills](#-skills) · 🧩 [Capabilities](#-capabilities) · 📦 [Deliverables](#-deliverables) · 🩺 [Troubleshooting](#-troubleshooting) · ❓ [FAQ](#-faq)

</div>

---

## 🎯 What it is

RePERS is a local-first harness for agent-run repository work. Instead of a
chat transcript, every run produces machine-readable evidence another repo
can verify. It ships:

- **A 24-entry capability registry** — preflight, DAG planning, install hooks, package gates, release pack, evidence bundles. Reuse first; build last.
- **A deterministic orchestration fixture** that proves conflict-safe worker dispatch BEFORE you point a real agent backend at it.
- **A `.repers/` runtime** (stdlib Python — no extra deps) installable into any Git repo with one command.
- **4 Codex skills** — `init` · `bug-hunt` · `release-pack` · `sinkin` (drift audit).
- **A transferable release pack** — `repers-release-pack.zip` — that another repo can extract, install, and verify end-to-end.

Designed for agents and maintainers who need more than "trust me, it works":
capability discovery before work starts, a concrete task graph, deterministic
local fixtures, installable hooks, JSON evidence, and a checksum-verifiable
release pack.

---

## 🚀 Install

**As a Codex plugin** (recommended):

```text
/plugin marketplace add coolsocket/repers
/plugin install repers
```

Then invoke any skill:

```text
/repers-init           # adopt RePERS in the current repo
/repers-bug-hunt       # run a full preflight → DAG → review cycle
/repers-release-pack   # build + verify dist artifacts
/repers-sinkin         # weekly drift audit
```

**As a repository-local runtime** (no plugin needed):

```bash
git clone https://github.com/coolsocket/repers.git
python repers/.repers/scripts/repers.py install --target /path/to/your-repo --json
cd /path/to/your-repo
python .repers/scripts/repers.py verify-install --json
```

The plugin gives Codex the workflow entrypoints. The `.repers/` runtime inside
the target repo supplies the CLI, hooks, templates, capability registry,
fixtures, package gates, and JSON evidence. **Neither hides the other.**

---

## 🔧 Daily workflow

```bash
# 1. find what already exists before building new
python .repers/scripts/repers.py preflight --query "bug hunt reusable workflow" --refresh --json

# 2. prove the orchestration contract (no real agents needed)
python .repers/scripts/repers.py fixture --action prove --json

# 3. run the full local gate before any push
python .repers/scripts/repers.py verify-all --json
```

Every command emits a JSON evidence object — pipe to `jq`, store in CI, or
let `/repers-sinkin` cross-check against `README` / `registry.json` /
`dist/`.

---

## 🧠 Skills

| Slash command | When to use | Cost |
|---|---|---|
| `/repers-init` | Once per repo — installs `.repers/` runtime + optional pre-commit hook | ~1 k tok on invoke |
| `/repers-bug-hunt` | Bug investigation — preflight, task DAG, worker dispatch, evidence review, focused verification | ~3 k tok on invoke |
| `/repers-release-pack` | Cutting a release — build, round-trip, verify both archives | ~2 k tok on invoke |
| `/repers-sinkin` | Periodic — audit drift across plugin skills, README, capability registry, package gates, release assets | ~5 k tok on invoke |

Always-on cost: **~600 tok per session** (loaded skill descriptions).

---

## 🧩 Capabilities

Twenty-four reusable capabilities live in [`.repers/capabilities/registry.json`](.repers/capabilities/registry.json).
Each has `id`, `kind`, `summary`, `commands`, `paths`, `verification` —
queryable by the CLI:

```bash
python .repers/scripts/repers.py capabilities --action search --query "release" --json
python .repers/scripts/repers.py capabilities --action validate --json
```

Highlights:

| Capability | Kind | What it does |
|---|---|---|
| `preflight` | workflow | Search local files, registry, global skills, optional CodeGraph evidence before building anything new |
| `task-dag` | workflow | Generate a conflict-safe task DAG with `target_files` per lane |
| `orchestration-fixture` | gate | Prove conflict-safe worker dispatch + join/review without a real backend |
| `package-readiness` | gate | Bundle status + round-trip verify the install archive |
| `release-pack` | workflow | Build the transferable `repers-release-pack.zip` (install + evidence + handoff + bootstrap) |
| `release-pack-verify` | gate | Verify a release pack received from another repo |
| `receiver-fixture` | gate | Install the package into a fresh Git repo and prove receiver-side commands |
| `verify-all` | gate | Run every local gate in one command |

Full inventory in [`registry.json`](.repers/capabilities/registry.json).

---

## 🪝 Hooks

| Hook | Trigger | Action |
|---|---|---|
| `.repers/hooks/pre-commit` | `git commit` | Run RePERS audit. **Warn mode** (default): log issues, don't block. **Strict mode**: block commit on audit failure. |

Install:

```bash
python .repers/scripts/repers.py install-hook --hook-policy warn   # or strict
```

State files live under `${REPO}/.repers/` — **per-repo, never shared across
projects.**

---

## 📦 Deliverables

A RePERS handoff is not just source code. It's a verifiable bundle:

| Artifact | Consumer | Format |
|---|---|---|
| `dist/repers-0.1.0.zip` | Receiver repo (extract + install) | zip |
| `dist/repers-release-pack.zip` | Another agent / repo (verify pack) | zip |
| `dist/repers-verify-all.json` | Auditor / CI | JSON evidence (328 KB) |
| `dist/repers-release-evidence.json` | Publish gate | JSON readiness |
| `dist/repers-state.{json,md}` | Status check | machine + human summary |
| `dist/repers-release-pack.{json,md}` | Release notes | manifest + summary |

Generate all with:

```bash
python .repers/scripts/repers.py release-pack --json
```

---

## 🗂️ Repository layout

```
.repers/
├── scripts/             stdlib-only Python: repers.py (CLI) + per-capability scripts
├── capabilities/        registry.json — 24 reusable workflows / scripts / hooks / gates
├── hooks/               pre-commit (warn / strict policies)
├── templates/           files copied into receiver repos
├── docs/                internal architecture / spec / workflow notes
├── manifest.json        runtime manifest (file fingerprints)
└── index/               local capability index (excluded from packages)

skills/                  4 Codex skills (init · bug-hunt · release-pack · sinkin)
.codex-plugin/           Codex marketplace plugin manifest
.github/                 CI + issue / PR templates + social preview
docs/                    public docs — bug-hunt demo, release checklist, promotion playbook
examples/                runnable adoption examples (basic-task, bug-hunt)
tests/                   smoke_repers.py — end-to-end receiver test
dist/                    generated packages + JSON evidence + markdown summaries
```

---

## 🩺 Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `preflight` returns results from another repo | Runtime state (`.repers/index/`) leaked into a previous install. Re-run `bundle-status --package --verify-roundtrip --json`; the archive is wrong, the verifier is right. |
| `fixture --action prove` reports `conflict_safe: false` | Multi-lane plan has overlapping `target_files`. Re-split lanes so each owns disjoint paths. |
| Codex skill changes don't take effect | Cached plugin install. `/plugin marketplace update repers && /plugin uninstall repers && /plugin install repers`; if still stale, restart the Codex session. |
| `verify-install` fails on a fresh receiver | Run `doctor --json` for the structured diagnosis. Typical cause: Python version <3.9 or missing optional CodeGraph adapter (which is fine — it falls back). |
| Pre-commit hook blocks every commit | You installed `--hook-policy strict` and have unresolved audit findings. Either fix them or reinstall with `--hook-policy warn`. |

Still stuck? Open a [Discussion](https://github.com/coolsocket/repers/discussions)
or paste the `bundle-status --package --verify-roundtrip --json` output in an
issue.

---

## ❓ FAQ

### What is RePERS?

A local-first harness that turns an agent's repository work into a repeatable
pipeline: **preflight → DAG → worker lanes → join/review → package → evidence**.
Every step is a CLI command with JSON output another repo can verify.

### How is RePERS different from LangGraph / CrewAI / AutoGen / OpenHands?

Those are agent **runtimes** — they execute LLM calls. RePERS is an
**operating layer above** any of them. It enforces capability reuse (preflight),
emits a conflict-safe task DAG, gates work behind a deterministic fixture, and
packages outcomes into a verifiable handoff. Point any agent backend at the
DAG; the contracts and evidence stay the same.

### Why "local-first"?

Three reasons:
1. **Reproducibility** — the same `verify-all --json` runs on a maintainer laptop, in CI, and in a receiver's fresh clone. No hidden service state.
2. **Trust** — agents shouldn't need cloud credentials to prove orchestration is safe. The fixture runs entirely offline.
3. **Portability** — `repers-release-pack.zip` is a single file another team can verify without onboarding.

Cloud backends remain optional, layered on top of the local contracts.

### Do I need to install RePERS in every project?

No. Install the Codex plugin **once** at user scope. Then run `/repers-init`
only in projects where you want the `.repers/` runtime + pre-commit hook
installed.

### How do I extend RePERS with a new capability?

1. `preflight --query "<intent>"` — confirm nothing similar exists. Extend instead of duplicating.
2. Add an entry to `.repers/capabilities/registry.json` (see existing entries for shape).
3. Implement the script under `.repers/scripts/` — stdlib only, JSON output.
4. Add a row to README "Core commands" if it's user-facing.
5. Re-run `capabilities --action validate --json` and `verify-all --json`.

Full rules in [`CLAUDE.md`](./CLAUDE.md).

### Does RePERS make any network calls at runtime?

No. The runtime is stdlib Python. Optional adapters (CodeGraph, cloud agent
backends) are explicitly opt-in and fall back to a structured "unavailable"
result instead of failing.

### What are the current limits?

- The deterministic fixture proves orchestration **contracts**, not real
  multi-agent execution. Real dispatch must respect the same `target_files`
  rules, then attach backend-specific traces.
- CodeGraph integration is optional — `preflight --codegraph` reports a
  structured fallback when the binary isn't on PATH.
- The full `verify-all` smoke is temporarily narrowed in CI to the three
  high-confidence gates (`verify-install`, `capabilities --action validate`,
  `release-pack-verify`) on ubuntu / windows / macos. The broader smoke
  suite has two pre-existing fragilities tracked in
  [#1](https://github.com/coolsocket/repers/issues/1).

### How do I uninstall?

```text
/plugin uninstall repers
/plugin marketplace remove repers
```

The `.repers/` runtime inside receiver repos stays — delete it manually if
you want.

---

## 🌟 Star history

[![Star History Chart](https://api.star-history.com/svg?repos=coolsocket/repers&type=Date)](https://www.star-history.com/#coolsocket/repers&Date)

---

## 🤝 Contributing & forking

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the development loop and
[`CLAUDE.md`](./CLAUDE.md) for the editing rules.

RePERS is intentionally small and stdlib-only — forks for non-Python receivers
or alternative agent backends are welcomed. The contracts (preflight, DAG,
evidence shape) are the load-bearing part; the runtime is replaceable.

For security disclosures, see [`SECURITY.md`](./SECURITY.md).
For cross-project pitfalls, see [`PITFALLS.md`](./PITFALLS.md).

---

## 📄 License

MIT. See [`LICENSE`](./LICENSE).

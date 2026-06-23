<div align="center">

# RePERS

**Operating layer for multi-agent repository work.**

Parallel lanes that don't collide. JSON evidence handed off between agents (any LLM). Verifiable release packs another repo can re-verify end-to-end.

[![Version](https://img.shields.io/github/v/release/coolsocket/repers?label=version&color=purple)](https://github.com/coolsocket/repers/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Capabilities: 24](https://img.shields.io/badge/capabilities-24-orange.svg)](./.repers/capabilities/registry.json)
[![Skills: 4](https://img.shields.io/badge/skills-4-green.svg)](./skills/)
[![CI](https://github.com/coolsocket/repers/actions/workflows/repers-smoke.yml/badge.svg)](https://github.com/coolsocket/repers/actions/workflows/repers-smoke.yml)
[![GitHub stars](https://img.shields.io/github/stars/coolsocket/repers?style=flat&color=yellow)](https://github.com/coolsocket/repers/stargazers)

🎯 [When to use](#-when-to-use--when-not-to-use) · 🚀 [Install](#-install) · 🔧 [Daily workflow](#-daily-workflow) · 🧠 [Skills](#-skills) · 🧩 [Capabilities](#-capabilities) · 📦 [Deliverables](#-deliverables) · 🩺 [Troubleshooting](#-troubleshooting) · ❓ [FAQ](#-faq)

</div>

---

## 🎯 What it is

> **A contract layer for AI agents working on the same codebase at the same time.**

When the work is **too big for one agent in one session** — a 12-file refactor, a deprecation sweep across 3 services, a feature that touches API + worker + UI — RePERS is the operating layer that lets a fleet of agents (Claude / Codex / Gemini / your own) carve it up, run lanes in parallel **without clobbering each other**, hand off via JSON evidence, and ship verifiable.

It is **not** an agent runtime. It is the **contract above** any runtime — preflight before new work, plan as a DAG with target-file isolation, dispatch with collision guards, review-on-join, evidence-based ship.

> ▶️ **See it run end-to-end**: [`docs/e2e-walkthrough.md`](./docs/e2e-walkthrough.md) — a real dogfood through every CLI subcommand (`init → preflight → plan → dispatch → 3 parallel workers → review → run → shipping → verify-install`) in ~45 s wall-clock. Every command shown was actually executed; every artifact is real.

What ships:
- 🧭 **A router** (`/repers-route`, coming in v0.2) that picks the right permutation per task — most one-liners are told to skip the harness entirely.
- 🧩 **A capability registry** (24 entries) as shared memory across agents — preflight before adding new.
- 🛡️ **A plan → DAG → dispatch contract** with `target_files` isolation — proven by a deterministic fixture before any live agent runs.
- 📜 **JSON evidence at every stage** — so Agent B picks up where Agent A stopped, and a reviewer (human or AI) can audit without the chat log.
- 📦 **A transferable release pack** — `repers-release-pack.zip` — that another repo extracts, installs, and re-verifies end-to-end.
- 🐍 **Stdlib-only Python runtime** — no extra deps, installs with one command.

---

## ✅ When to use / 🚫 When NOT to use

RePERS is **opinionated**: it earns its keep on a specific shape of work. Most everyday tasks should skip it. (A 1-bug benchmark on `sqlfluff__sqlfluff-2419` measured **5.8× wall-clock overhead vs. a naked agent for no quality lift** — that's the exact shape the router will route around.)

| ✅ Use RePERS when… | 🚫 Skip RePERS when… |
|---|---|
| Work touches **≥ 3 files across ≥ 2 domains** | Single-file, single-function fix |
| **≥ 1 day** of agent work, or spans multiple sessions | Bug where the failing test already shows the expected output verbatim |
| You're orchestrating **multiple agents** (Claude + Codex + Gemini, or N parallel Claudes) | One agent, one chat, one IDE — your editor + agent is faster |
| Cross-cutting work: migration / deprecation sweep / instrumentation rollout / refactor of a god-class | Throwaway spike or prototype |
| Hand-off matters: agent → reviewer agent → human → CI | No hand-off — you ship in the same session you started |
| Verifiable evidence required (audit / compliance / release gate) | Quick local change you'll commit and forget |

If you're not sure, run `/repers-route "<your task>"` (v0.2) — it'll tell you which permutation (or "skip the harness") fits.

---

## 🧭 The 5 stages — and when each fires

The full pipeline is **R-P-E-R-S** (Research → Plan → Execute → Review → Ship), but the **router picks the permutation per task**. You should rarely run all 5.

| Stage | What it does | Pays off when… | Skip when… |
|---|---|---|---|
| **R**esearch (preflight) | Search local capability registry + git log + similar past work | Reuse matters; repo is large; multiple agents need shared memory | Toy repo or one-off task |
| **P**lan (DAG) | Decompose into lanes with `target_files` isolation | ≥3 files OR ≥2 independent sub-problems | Patch is <10 lines in 1 file |
| **E**xecute (dispatch) | Spawn N worker agents on lanes in parallel; contract prevents collisions | Lanes are genuinely independent (different files / different concerns) | All lanes read/write the same one file |
| **R**eview (join) | Reviewer agent (or human) takes lane outputs, decides, verifies | Risk of regression; multiple candidate fixes to weigh | Test already pins the answer |
| **S**hip | Apply patch, run focused tests, pack evidence for hand-off | Multi-day work; multi-stakeholder; release-gated | You'll commit and merge in the same session |

Common permutations the router emits:
- **R-E-R** (hotfix, single-file): skip plan + parallel dispatch
- **R-P-E-R** (multi-file in one domain): plan + dispatch, light ship
- **R-P-E-R-S** (multi-domain, multi-day): full pipeline — this is the sweet spot
- **R-S** (docs / config only): skip execute, review + ship
- **R only** (spike): write a research note, stop, decide later

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
/repers-bug-hunt       # run a full preflight → DAG → review cycle (route-first)
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

The plugin gives Codex / Claude Code / your agent the workflow entrypoints. The `.repers/` runtime inside the target repo supplies the CLI, registry, dispatch contracts, fixtures, package gates, and JSON evidence. **Neither hides the other.**

---

## 🔧 Daily workflow

```bash
# 1. find what already exists (or what other agents have built) before adding new
python .repers/scripts/repers.py preflight --query "<your intent>" --refresh --json

# 2. prove the dispatch contract holds before you send live agents at it
python .repers/scripts/repers.py fixture --action prove --json

# 3. run the full local gate before any push
python .repers/scripts/repers.py verify-all --json
```

Every command emits a JSON evidence object — pipe to `jq`, store in CI, ship in the release pack, or let `/repers-sinkin` cross-check against `README` / `registry.json` / `dist/`.

---

## 🧠 Skills

| Slash command | When to use | Cost |
|---|---|---|
| `/repers-init` | Once per repo — installs `.repers/` runtime + optional pre-commit hook | ~1 k tok on invoke |
| `/repers-bug-hunt` | Multi-file bug investigation — preflight, task DAG, parallel worker dispatch, evidence review, focused verification. **Calls router first**; for trivial bugs it short-circuits | ~3 k tok on invoke |
| `/repers-release-pack` | Cutting a release — build, round-trip, verify both archives | ~2 k tok on invoke |
| `/repers-sinkin` | Periodic — audit drift across plugin skills, README, capability registry, package gates, release assets | ~5 k tok on invoke |

Always-on cost: **~600 tok per session** (loaded skill descriptions).

> **v0.2 plan**: surface the router as a standalone `/repers-route` skill so it can gate any agent's decision to invoke the harness, not just bug-hunts.

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
| `preflight` | workflow | Search local files, registry, global skills, optional CodeGraph before adding new |
| `task-dag` | workflow | Generate a conflict-safe task DAG with `target_files` per lane |
| `orchestration-fixture` | gate | Prove conflict-safe worker dispatch + join/review without a real backend |
| `package-readiness` | gate | Bundle status + round-trip verify the install archive |
| `release-pack` | workflow | Build the transferable `repers-release-pack.zip` (install + evidence + handoff + bootstrap) |
| `release-pack-verify` | gate | Verify a release pack received from another repo |
| `receiver-fixture` | gate | Install the package into a fresh Git repo and prove receiver-side commands |
| `verify-all` | gate | Run every local gate in one command |

Full inventory in [`registry.json`](.repers/capabilities/registry.json).

> **v0.2 plan**: trim the registry from 24 → ~15 by removing self-referential META scripts (state report, continuation runner, open-source-benchmark) that don't earn their keep outside the harness itself.

---

## 🪝 Hooks

| Hook | Trigger | Action |
|---|---|---|
| `.repers/hooks/pre-commit` | `git commit` | Run RePERS audit. **Warn mode** (default): log issues, don't block. **Strict mode**: block commit on audit failure. |

Install:

```bash
python .repers/scripts/repers.py install-hook --hook-policy warn   # or strict
```

State files live under `${REPO}/.repers/` — **per-repo, never shared across projects.**

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
| Codex skill changes don't take effect | Cached plugin install. `/plugin marketplace update repers && /plugin uninstall repers && /plugin install repers`; if still stale, restart the agent session. |
| `verify-install` fails on a fresh receiver | Run `doctor --json` for the structured diagnosis. Typical cause: Python version <3.9 or missing optional CodeGraph adapter (which is fine — it falls back). |
| Pre-commit hook blocks every commit | You installed `--hook-policy strict` and have unresolved audit findings. Either fix them or reinstall with `--hook-policy warn`. |

Still stuck? Open a [Discussion](https://github.com/coolsocket/repers/discussions)
or paste the `bundle-status --package --verify-roundtrip --json` output in an
issue.

---

## ❓ FAQ

### Should I use RePERS for a one-line bug fix?

**No.** A 1-bug benchmark on `sqlfluff__sqlfluff-2419` (4-line patch in 1 file) measured **5.8× wall-clock overhead vs. a naked agent for no quality lift** — both produced functionally identical patches. The router will tell you to skip the harness for that shape of work. RePERS is designed for the **opposite** end: multi-file, multi-domain, multi-day, multi-agent coordination. See [`When to use`](#-when-to-use--when-not-to-use).

### How is RePERS different from LangGraph / CrewAI / AutoGen / OpenHands?

Those are agent **runtimes** — they execute LLM calls. RePERS is the **contract layer above** any of them. Point any agent backend at the DAG; the dispatch contract, JSON evidence, and verifiable release pack stay the same. RePERS does not run LLM calls itself.

### Does it really work with any AI, or just Claude/Codex?

The contract is JSON in / JSON out and stdlib-Python dispatch — runtime-agnostic by design. As of v0.1.0, all wired entrypoints are Codex/Claude skills. A reference `agent-fixture` proving a non-Claude runtime (Gemini CLI, mock stdin/stdout) end-to-end is on the v0.2 list.

### Why "local-first"?

Three reasons:
1. **Reproducibility** — the same `verify-all --json` runs on a maintainer laptop, in CI, and in a receiver's fresh clone. No hidden service state.
2. **Trust** — agents shouldn't need cloud credentials to prove orchestration is safe. The fixture runs entirely offline.
3. **Portability** — `repers-release-pack.zip` is a single file another team can verify without onboarding.

Cloud backends remain optional, layered on top of the local contracts.

### How do I extend RePERS with a new capability?

1. `preflight --query "<intent>"` — confirm nothing similar exists. Extend instead of duplicating.
2. Add an entry to `.repers/capabilities/registry.json` (see existing entries for shape).
3. Implement the script under `.repers/scripts/` — stdlib only, JSON output.
4. Add a row to README "Core commands" if it's user-facing.
5. Re-run `capabilities --action validate --json` and `verify-all --json`.

Full rules in [`CLAUDE.md`](./CLAUDE.md).

### Does RePERS make any network calls at runtime?

No. The runtime is stdlib Python. Optional adapters (CodeGraph, cloud agent backends) are explicitly opt-in and fall back to a structured "unavailable" result instead of failing.

### What are the current limits?

- v0.1 ships the skills hard-coded to one permutation each. **The router that picks per-task permutations is on the v0.2 list** — until it lands, `/repers-bug-hunt` will be over-eager on small bugs.
- The deterministic fixture proves orchestration **contracts**, not real multi-agent execution. Real dispatch must respect the same `target_files` rules, then attach backend-specific traces.
- CodeGraph integration is optional — `preflight --codegraph` reports a structured fallback when the binary isn't on PATH.
- The full `verify-all` smoke is temporarily narrowed in CI to three high-confidence gates (`verify-install`, `capabilities --action validate`, `release-pack-verify`) on ubuntu / windows / macos. The broader smoke suite has two pre-existing fragilities tracked in [#1](https://github.com/coolsocket/repers/issues/1).

### How do I uninstall?

```text
/plugin uninstall repers
/plugin marketplace remove repers
```

The `.repers/` runtime inside receiver repos stays — delete it manually if you want.

---

## 🌟 Star history

[![Star History Chart](https://api.star-history.com/svg?repos=coolsocket/repers&type=Date)](https://www.star-history.com/#coolsocket/repers&Date)

---

## 🤝 Contributing & forking

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the development loop and [`CLAUDE.md`](./CLAUDE.md) for the editing rules.

RePERS is intentionally small and stdlib-only — forks for non-Python receivers or alternative agent backends are welcomed. The contracts (preflight, DAG, evidence shape) are the load-bearing part; the runtime is replaceable.

For security disclosures, see [`SECURITY.md`](./SECURITY.md).
For cross-project pitfalls, see [`PITFALLS.md`](./PITFALLS.md).

---

## 📄 License

MIT. See [`LICENSE`](./LICENSE).

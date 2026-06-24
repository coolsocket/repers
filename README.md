<div align="center">

# RePERS

**`R`**esearch · **`P`**lan · **`E`**xecute · **`R`**eview · **`S`**hip
— a contract layer for **multi-agent** repository work.

Parallel lanes that don't collide. JSON evidence handed off between agents (any LLM). Verifiable release packs another repo can re-verify end-to-end.

[![Version](https://img.shields.io/github/v/release/coolsocket/repers?label=version&color=purple)](https://github.com/coolsocket/repers/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Capabilities: 25](https://img.shields.io/badge/capabilities-25-orange.svg)](./.repers/capabilities/registry.json)
[![Skills: 5](https://img.shields.io/badge/skills-5-green.svg)](./skills/)
[![CI](https://github.com/coolsocket/repers/actions/workflows/repers-smoke.yml/badge.svg)](https://github.com/coolsocket/repers/actions/workflows/repers-smoke.yml)
[![GitHub stars](https://img.shields.io/github/stars/coolsocket/repers?style=flat&color=yellow)](https://github.com/coolsocket/repers/stargazers)

🤖 [For AI agents](#-for-ai-agents--first-contact-in-60-seconds) · 📊 [Maturity curve](#-where-repers-fits-on-the-codebase-maturity-curve) · 🔗 [Cross-repo handoff](#-cross-repo-and-cross-team-handoff) · 🎯 [When to use](#-when-to-use--when-not-to-use) · 🧠 [Skills](#-skills) · 🩺 [Troubleshooting](#-troubleshooting) · ❓ [FAQ](#-faq)

</div>

---

## 🤖 For AI agents — first contact in 60 seconds

> **You're an agent. Your user just pointed you at this repo. Do not install anything yet.** Run the router cold to find out whether you should bother:

```bash
git clone https://github.com/coolsocket/repers.git /tmp/repers   # ~3 s
python3 /tmp/repers/.repers/scripts/repers.py route \
  --task "<the user's actual task in one sentence>" \
  --est-files <your estimate or omit> \
  --json
```

The router returns a JSON envelope with a `next_step.action` enum — branch on **that**, not the prose:

| `next_step.action` | What you do | Cost |
|---|---|---|
| `skip_harness` | Do **not** install. Use your own Edit/Read/Bash. Return control to the user. | 0 |
| `naked_loop` | Same — naked agent loop is correct. Do not install. | 0 |
| `research_only` | Install + run `preflight` once, write a research note, stop. | ~3 min |
| `docs_only_ship` | Install + edit + run `shipping`. Skip plan/execute. | ~5 min |
| `invoke_bug_hunt_no_ship` | Install + run `/repers-bug-hunt`. Full plan→dispatch→review, skip shipping. | ~15 min + agent time |
| `invoke_bug_hunt_full` | Install + run `/repers-bug-hunt` end-to-end including shipping. | ~30 min + agent time |

Then continue with whichever path the router picked. Full agent playbook for each path: **[`AGENTS.md`](./AGENTS.md)**. If you're a *worker* on a dispatched lane (not the supervisor): **[`WORKER.md`](./WORKER.md)**.

If you're a human reading this section: the same router works for you — `route --task "..."` returns a one-line recommendation. Don't install anything until it tells you to.

---

## 🎯 What it is (for humans)

> **A contract layer for AI agents working on the same codebase at the same time.**

When the work is **too big for one agent in one session** — a 12-file refactor, a deprecation sweep across 3 services, a feature that touches API + worker + UI — RePERS is the operating layer that lets a fleet of agents (Claude / Codex / Gemini / your own) carve it up, run lanes in parallel **without clobbering each other**, hand off via JSON evidence, and ship verifiable.

It is **not** an agent runtime. It is the **contract above** any runtime — preflight before new work, plan as a DAG with target-file isolation, dispatch with collision guards, review-on-join, evidence-based ship.

> 🧠 **Why these five stages?** The full *why* — the three-layer philosophy (Memory · Speed · Alignment) and which stages serve which purpose — lives in [`PHILOSOPHY.md`](./PHILOSOPHY.md).

> ▶️ **See it run end-to-end**: [`docs/e2e-walkthrough.md`](./docs/e2e-walkthrough.md) — a real dogfood through every CLI subcommand (`init → preflight → plan → dispatch → 3 parallel workers → review → run → shipping → verify-install`) in ~45 s wall-clock. Every command shown was actually executed; every artifact is real.

What ships:
- 🧭 **A router** (`/repers-route` + `repers.py route --json`) that picks the right permutation per task — small tasks are told to skip the harness entirely, so the pipeline only fires when its shape matches the work.
- 🧩 **A capability registry** (25 entries, including the new `route` capability) as shared memory across agents — preflight before adding new.
- 🛡️ **A plan → DAG → dispatch contract** with `target_files` isolation — proven by a deterministic fixture before any live agent runs.
- 📜 **JSON evidence at every stage** — so Agent B picks up where Agent A stopped, and a reviewer (human or AI) can audit without the chat log.
- 📦 **A transferable release pack** — `repers-release-pack.zip` — that another repo extracts, installs, and re-verifies end-to-end.
- 🐍 **Stdlib-only Python runtime** — no extra deps, installs with one command.

---

## 📊 Where RePERS fits on the codebase maturity curve

The harness's overhead is **fixed**. The work it coordinates **compounds**. So whether it earns its keep depends almost entirely on **what shape and scale of work you're doing** — not what stack you're on. The honest answer changes as a codebase grows from greenfield to enterprise to cross-org ecosystem:

| You are… | Repo shape | Should you adopt RePERS? | What you actually need at this stage |
|---|---|---|---|
| **Day 0 — solo, prototype** (<1 k LOC, no tests) | One file or two; you're sketching | **No.** Naked agent in your IDE wins every time. | A chat window. Skip the harness. |
| **Early product** (1–3 devs, 1–10 k LOC, single domain) | A handful of files, light tests, one repo | **Almost always no.** Maybe pin `/repers-route` so the team has the option later. | CI + pre-commit lint. The router will keep telling you "skip". |
| **Growing product** (5–10 devs, 50 k LOC, 2–3 domains: api / web / worker) | Multi-file PRs are now common. Merge conflicts start. People step on each other. | **Selectively.** Adopt for the *big* changes — migrations, deprecation sweeps, refactors of a god-class. Skip for everyday PRs. | Branch protection + structured code review. The router routes most tasks to `R-E-R` and the occasional one to `R-P-E-R`. |
| **Scale-up** (20+ engineers, 200 k+ LOC monorepo, multi-team) | Parallel feature work daily. **Multiple AI agents** are helping multiple engineers. Sometimes you set off two Codex sessions on the same area at once and they clobber. | **Yes — this is the sweet spot.** The router will recommend `R-P-E-R` or `R-P-E-R-S` for most non-trivial tasks. | A contract that **prevents N agents (yours and your teammates') from clobbering each other's lanes.** ← that's what the `target_files` isolation + dispatch contract is. |
| **Big company / regulated** (100+ engineers, multi-service, audit trails required) | Cross-cutting work (security patches, compliance migrations) needs evidence chains. Different teams pick different agents (Claude / Codex / Gemini / in-house fine-tunes). | **Yes — as the lingua franca.** Adopt it across teams. JSON evidence is auditable; release-pack-verify lets a downstream team re-verify another team's claim without trusting their chat log. | A standard contract across agent fleets + a portable audit trail. |
| **Cross-org / OSS ecosystem** (multi-repo dependencies, vendor diversity) | Agent in repo A produces something repo B's CI or maintainer has to consume / verify. You don't trust repo A's vendor or their evidence. | **Yes — for the handoff.** `repers-release-pack.zip` is the transfer protocol; the receiving repo extracts it and **re-verifies independently** without trusting either the sender's vendor or their JSON. | A contract that survives vendor + organizational + trust boundaries. |

**Pattern**: at the small end the overhead dominates; at the large end the coordination *is* the work, and the absence of a contract is what causes the pain. RePERS feels cheaper as the codebase gets bigger. The router exists so a tool that genuinely earns its keep at one end doesn't get force-fitted onto the other.

---

## 🔗 Cross-repo and cross-team handoff

The single most under-told story in v0.1 was: **RePERS already ships the cross-repo handoff primitives**. Most agent harnesses assume one repo + one agent + one team. Real engineering work at scale doesn't:

| Cross-repo flow | RePERS primitive | What it proves |
|---|---|---|
| Team A produces a release artifact; Team B's CI must consume + audit | `release-pack.zip` (transferable archive — install + readiness + evidence + bootstrap + benchmark + state) | A single signed zip moves between repos / orgs / clouds without losing audit context |
| Team B receives the pack; their AI/CI needs to verify it independently | `release-pack-verify --archive <pack> --json` | Receiver re-verifies checksums + manifest + embedded evidence **without trusting** the sender's vendor or JSON |
| A fresh repo wants to adopt the harness from a pack | `receiver-fixture --json` / `source-install-fixture --json` | Fresh `git init` + 1 command → working `.repers/` runtime; both contracts proven in CI |
| Two repos cooperate via a temporary bare remote (e.g., an air-gapped review) | `publish-clone-fixture --json` | Source pushes to bare remote → clone repo re-verifies → no network deps |
| A different LLM vendor (Codex / Gemini / your own) drives a lane | `dispatch.v1` manifest + `step_result.v1` artifact | Contract is JSON-in / JSON-out; the worker doesn't need to know which vendor the supervisor uses |

For a Series-A startup with one repo, these primitives look like over-engineering. For a Fortune-500 with 12 services and 4 teams using 3 different AI vendors, they're the only thing that lets the audit + handoff actually work without "trust me, my agent did the right thing."

> **What this means for evaluation**: if you're evaluating RePERS for a small repo, evaluate the **router + naked-agent recommendation** — does it correctly tell you not to use the harness? If you're evaluating for a large repo or multi-team org, evaluate the **dispatch contract + release-pack handoff** — can you make repo A produce a pack repo B can re-verify without trusting repo A's vendor? Both are valid, and they're different evaluations.

---

## ✅ When to use / 🚫 When NOT to use

RePERS is **opinionated**: it earns its keep on a specific shape of work. Most everyday tasks should skip it — the router will tell you when.

| ✅ Use RePERS when… | 🚫 Skip RePERS when… |
|---|---|
| Work touches **≥ 3 files across ≥ 2 domains** | Single-file, single-function fix |
| **≥ 1 day** of agent work, or spans multiple sessions | Bug where the failing test already shows the expected output verbatim |
| You're orchestrating **multiple agents** (Claude + Codex + Gemini, or N parallel Claudes) | One agent, one chat, one IDE — your editor + agent is faster |
| Cross-cutting work: migration / deprecation sweep / instrumentation rollout / refactor of a god-class | Throwaway spike or prototype |
| Hand-off matters: agent → reviewer agent → human → CI | No hand-off — you ship in the same session you started |
| Verifiable evidence required (audit / compliance / release gate) | Quick local change you'll commit and forget |

If you're not sure, ask the router:

```bash
python3 .repers/scripts/repers.py route --task "<your task description>" --json
# or via the Codex skill: /repers-route
```

The router is a deterministic keyword + repo-signal decision tree (no LLM call, <100 ms, offline). It returns one of `skip` / `R-only` / `R-S` / `R-E-R` / `R-P-E-R` / `R-P-E-R-S` plus the reason — and it defaults to the smaller permutation when in doubt, so the worst case is a minute spent reading instead of being pulled into ceremony the task doesn't warrant.

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
python3 .repers/scripts/repers.py verify-install --json
```

The plugin gives Codex / Claude Code / your agent the workflow entrypoints. The `.repers/` runtime inside the target repo supplies the CLI, registry, dispatch contracts, fixtures, package gates, and JSON evidence. **Neither hides the other.**

---

## 🔧 Daily workflow

```bash
# 1. find what already exists (or what other agents have built) before adding new
python3 .repers/scripts/repers.py preflight --query "<your intent>" --refresh --json

# 2. prove the dispatch contract holds before you send live agents at it
python3 .repers/scripts/repers.py fixture --action prove --json

# 3. run the full local gate before any push
python3 .repers/scripts/repers.py verify-all --json
```

Every command emits a JSON evidence object — pipe to `jq`, store in CI, ship in the release pack, or let `/repers-sinkin` cross-check against `README` / `registry.json` / `dist/`.

---

## 🧠 Skills

| Slash command | When to use | Cost |
|---|---|---|
| `/repers-route` | **First.** Before any other R-P-E-R-S skill — decides whether the harness fits this task at all (returns `skip` / `R-only` / `R-S` / `R-E-R` / `R-P-E-R` / `R-P-E-R-S` + reason). Deterministic, <100 ms, no LLM call. | ~500 tok on invoke |
| `/repers-init` | Once per repo — installs `.repers/` runtime + optional pre-commit hook | ~1 k tok on invoke |
| `/repers-bug-hunt` | Multi-file bug investigation. **Routes first via `/repers-route`** and short-circuits to a naked agent loop when the router says `skip` / `R-E-R`. Only runs preflight → plan → dispatch → review → ship when the router recommends a multi-stage permutation. | ~3 k tok on invoke |
| `/repers-release-pack` | Cutting a release — build, round-trip, verify both archives | ~2 k tok on invoke |
| `/repers-sinkin` | Periodic — audit drift across plugin skills, README, capability registry, package gates, release assets | ~5 k tok on invoke |

Always-on cost: **~700 tok per session** (loaded skill descriptions for 5 skills).

---

## 🧩 Capabilities

Twenty-five reusable capabilities live in [`.repers/capabilities/registry.json`](.repers/capabilities/registry.json).
Each has `id`, `kind`, `summary`, `commands`, `paths`, `verification` —
queryable by the CLI:

```bash
python3 .repers/scripts/repers.py capabilities --action search --query "release" --json
python3 .repers/scripts/repers.py capabilities --action validate --json
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

> **v0.2.0 shipped**: registry trimmed 25 → 20 by removing self-referential META verbs (objective-audit / continue / snapshot-freshness / open-source-benchmark) that didn't earn their keep outside the harness itself. `state` slimmed to git + package + capabilities only. See [`CHANGELOG.md`](./CHANGELOG.md) for the breaking-change list.

---

## 🪝 Hooks

| Hook | Trigger | Action |
|---|---|---|
| `.repers/hooks/pre-commit` | `git commit` | Run RePERS audit. **Warn mode** (default): log issues, don't block. **Strict mode**: block commit on audit failure. |

Install:

```bash
python3 .repers/scripts/repers.py install-hook --hook-policy warn   # or strict
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
python3 .repers/scripts/repers.py release-pack --json
```

---

## 🗂️ Repository layout

```
.repers/
├── scripts/             stdlib-only Python: repers.py (CLI) + per-capability scripts
├── capabilities/        registry.json — 25 reusable workflows / scripts / hooks / gates
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

**No.** For a single-file, single-function bug — especially when the failing test already pins the expected output — your editor plus a naked agent loop is faster than the harness's coordination ceremony. The router will tell you to skip. RePERS is designed for the **opposite** end: multi-file, multi-domain, multi-day, multi-agent coordination. See [`When to use`](#-when-to-use--when-not-to-use).

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

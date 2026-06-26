<div align="center">

# RePERS

**Research · Plan · Execute · Review · Ship**

A contract layer for multi-agent repository work — parallel lanes that don't collide, JSON evidence handed off between agents (any LLM), verifiable release packs another repo can re-verify end-to-end.

[![Version](https://img.shields.io/github/v/release/coolsocket/repers?label=version&color=purple)](https://github.com/coolsocket/repers/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Capabilities: 20](https://img.shields.io/badge/capabilities-20-orange.svg)](./.repers/capabilities/registry.json)
[![Skills: 5](https://img.shields.io/badge/skills-5-green.svg)](./skills/)
[![CI](https://github.com/coolsocket/repers/actions/workflows/repers-smoke.yml/badge.svg)](https://github.com/coolsocket/repers/actions/workflows/repers-smoke.yml)
[![GitHub stars](https://img.shields.io/github/stars/coolsocket/repers?style=flat&color=yellow)](https://github.com/coolsocket/repers/stargazers)

🎯 [What it is](#-what-it-is-for-humans) · 🤖 [For AI agents](#-for-ai-agents--first-contact-in-60-seconds) · ✅ [When to use](#-when-to-use--when-not-to-use) · 🚀 [Install](#-install) · 🧠 [Skills](#-skills) · 🩺 [Troubleshooting](#-troubleshooting) · ❓ [FAQ](#-faq)

</div>

---

## 🎯 What it is (for humans)

> **A contract layer for AI agents working on the same codebase at the same time.**

When the work is **too big for one agent in one session** — a 12-file refactor, a deprecation sweep across 3 services, a feature that touches API + worker + UI — RePERS is the operating layer that lets a fleet of agents (Claude / Codex / Gemini / your own) carve it up, run lanes in parallel **without clobbering each other**, hand off via JSON evidence, and ship verifiable.

It is **not** an agent runtime. It is the **contract above** any runtime — preflight before new work, plan as a DAG with target-file isolation, dispatch with collision guards, review-on-join, evidence-based ship.

> 🧠 **Why these five stages?** The full *why* — the three-layer philosophy (Memory · Speed · Alignment) and which stages serve which purpose — lives in [`AGENTS.md § Appendix A`](./AGENTS.md#appendix-a--the-three-layer-philosophy-the-why-behind-the-five-stages).

> ▶️ **See it run end-to-end**: [`docs/e2e-walkthrough.md`](./docs/e2e-walkthrough.md) — a real dogfood through every CLI subcommand (`init → preflight → plan → dispatch → 3 parallel workers → review → run → shipping → verify-install`) in ~45 s wall-clock. Every command shown was actually executed; every artifact is real.

What ships:
- 🧭 **A router** (`/repers-route` + `repers.py route --json`) that picks the right permutation per task — small tasks are told to skip the harness entirely, so the pipeline only fires when its shape matches the work.
- 🧩 **A capability registry** (20 entries) as shared memory across agents — preflight before adding new.
- 🛡️ **A plan → DAG → dispatch contract** with `target_files` isolation — proven by a deterministic fixture before any live agent runs.
- 📜 **JSON evidence at every stage** — so Agent B picks up where Agent A stopped, and a reviewer (human or AI) can audit without the chat log.
- 📦 **A transferable release pack** — `repers-release-pack.zip` — that another repo extracts, installs, and re-verifies end-to-end.
- 🐍 **Stdlib-only Python runtime** — no extra deps, installs with one command.

---

## 🤖 For AI agents — first contact in 60 seconds

> **You're an agent. Your user just pointed you at this repo. Do not install anything yet.** Run the router cold — **one line, zero install** — to find out whether you should bother:

```bash
uvx --from git+https://github.com/coolsocket/repers.git repers route \
  --task "<the user's actual task in one sentence>" \
  --json
```

uvx clones + builds + runs in a single command; nothing is written to your working directory. No `pip install`, no `git clone` you have to clean up. If your environment doesn't have `uv` / `uvx`, the longer-form fallback works identically:

```bash
git clone https://github.com/coolsocket/repers.git /tmp/repers   # ~3 s
python3 /tmp/repers/.repers/scripts/repers.py route \
  --task "<the user's actual task in one sentence>" \
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

Then continue with whichever path the router picked. Full agent playbook for each path (plus the worker contract as an appendix): **[`AGENTS.md`](./AGENTS.md)**.

---

## ✅ When to use / 🚫 When NOT to use

RePERS is **opinionated**: it earns its keep on a specific shape of work. Most everyday tasks should skip it — the router will tell you when.

| ✅ Use RePERS when… | 🚫 Skip RePERS when… |
|---|---|
| Work touches **≥ 3 files across ≥ 2 domains** | Single-file, single-function fix |
| **≥ 1 day** of agent work, or multiple sessions | Failing test already pins the expected output |
| Multiple agents collaborating (Claude + Codex + Gemini, or N parallel Claudes) | One agent, one chat, one IDE |
| Cross-cutting: migration / deprecation / god-class refactor | Throwaway spike or prototype |
| Hand-off matters: agent → reviewer → human → CI | Ship in the same session you started |
| Audit / compliance / release-gated evidence required | Quick local change you'll commit and forget |

If unsure, **ask the router** (1 line, no install, <100 ms, deterministic):

```bash
uvx --from git+https://github.com/coolsocket/repers.git repers route --task "<your task>" --json
```

Returns one of `skip` / `R-only` / `R-S` / `R-E-R` / `R-P-E-R` / `R-P-E-R-S` + reason. Defaults to the smaller permutation when in doubt.

> 📊 **Maturity curve** — [`docs/maturity-curve.md`](./docs/maturity-curve.md) maps Day-0 → Cross-org tiers to adopt-decisions (6 rows).<br/>
> 🔗 **Cross-repo handoff** — [`docs/cross-repo-handoff.md`](./docs/cross-repo-handoff.md) covers the 5 primitives for multi-team / cross-vendor evidence chains.<br/>
> 🧭 **The 5 stages in depth** — `R → P → E → R → S` per-stage breakdown lives in [`AGENTS.md § Appendix A`](./AGENTS.md#appendix-a--the-three-layer-philosophy-the-why-behind-the-five-stages).

---

## 🚀 Install

| Channel | Command | When |
|---|---|---|
| **Zero-install one-shot** | `uvx --from git+https://github.com/coolsocket/repers.git repers route --task "..."` | First contact. `uvx` clones + builds + runs without writing to your cwd. Works for every subcommand. |
| **CLI globally** | `pipx install git+https://github.com/coolsocket/repers.git` | You'll call `repers route / preflight / fixture` across many repos. |
| **MCP server** (agent-native) | `uvx --from 'git+https://github.com/coolsocket/repers.git[mcp]' repers-mcp` | You're in an MCP-aware agent (Claude Code / Cursor / OpenCode / Continue / Goose) — drop 4 lines into MCP config and RePERS appears as native tools. |
| **Receiver mode** (writes `.repers/` into your repo) | `repers install --target /path/to/your-repo` | Team commits the harness alongside code; JSON evidence enters git history; release packs reproducible from commit. |
| **Codex / Claude Code plugin** | `/plugin marketplace add coolsocket/repers` then `/plugin install repers` | Slash-command UX: `/repers-route`, `/repers-init`, `/repers-bug-hunt`, `/repers-release-pack`, `/repers-sinkin`. |

The 5 channels do not hide each other — install whichever surface fits your role, or multiple.

---

## 🔧 Daily workflow

```bash
repers preflight --query "<your intent>" --refresh --json   # 1. reuse before build
repers fixture --action prove --json                        # 2. prove collision contract
repers verify-all --json                                    # 3. full local gate
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

Twenty reusable capabilities in [`.repers/capabilities/registry.json`](.repers/capabilities/registry.json), each with `id` / `kind` / `summary` / `commands` / `paths` / `verification`. Queryable:

```bash
repers capabilities --action search --query "release" --json
repers capabilities --action validate --json
```

Load-bearing ones to know:

| Capability | Does |
|---|---|
| `preflight` | Search local files + registry + global skills before adding new |
| `task-dag` | Generate a conflict-safe DAG with `target_files` per lane |
| `orchestration-fixture` | Prove conflict-safe dispatch + join/review without a real backend |
| `release-pack` + `release-pack-verify` | Build a transferable bundle; receiver re-verifies independently |

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

`repers release-pack --json` produces `dist/repers-release-pack.zip` — a single transferable bundle containing the install archive, readiness sidecar, release evidence, publish-handoff, remote-bootstrap, state, and verify-all evidence. The receiver runs `repers release-pack-verify --archive <pack>` and re-verifies checksums + manifest + embedded evidence **without trusting the sender**. See [`docs/release-checklist.md`](./docs/release-checklist.md) for the full artifact inventory.

---

## 🗂️ Repository layout

See [`docs/components-map.md`](./docs/components-map.md) for the one-page map of every CLI verb / capability / contract per R-P-E-R-S layer, and [`CLAUDE.md`](./CLAUDE.md) for the "what lives where" + editing rules.

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

**No.** For a single-file, single-function bug — especially when the failing test already pins the expected output — your editor plus a naked agent loop is faster than the harness's coordination ceremony. The router will tell you to skip. RePERS is designed for the **opposite** end: multi-file, multi-domain, multi-day, multi-agent coordination.

### How is RePERS different from LangGraph / CrewAI / AutoGen / OpenHands?

Those are agent **runtimes** — they execute LLM calls. RePERS is the **contract layer above** any of them. Point any agent backend at the DAG; the dispatch contract, JSON evidence, and verifiable release pack stay the same. RePERS does not run LLM calls itself.

### Does it work with any AI, or just Claude/Codex?

Contract is JSON in / JSON out and stdlib-Python dispatch — runtime-agnostic by design. v0.2 ships skills for Codex/Claude, an MCP server (`repers-mcp`) for any MCP-aware agent, and the worker contract (`step_result.v1`) any LLM or deterministic script can satisfy. A single task can have a Claude supervisor + Codex worker on lane 1 + Gemini worker on lane 2.

### Does RePERS make any network calls at runtime?

No. The runtime is stdlib Python. Optional adapters (CodeGraph, cloud agent backends) are explicitly opt-in and fall back to a structured "unavailable" result instead of failing.

### Current limits

- The deterministic fixture proves orchestration **contracts**, not real multi-agent execution. Real dispatch must respect the same `target_files` rules and attach backend-specific traces.
- `verify-all` CI is narrowed to three high-confidence gates (`verify-install` / `capabilities validate` / `release-pack-verify`) across ubuntu / windows / macos. Broader smoke has two pre-existing fragilities tracked in [#1](https://github.com/coolsocket/repers/issues/1).

### How do I uninstall?

```text
/plugin uninstall repers && /plugin marketplace remove repers   # Codex/Claude Code plugin
pipx uninstall repers                                            # CLI
```

The `.repers/` runtime inside receiver repos stays — delete the directory manually if you want.

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

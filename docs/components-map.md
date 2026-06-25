# Components map — what RePERS ships at each pipeline stage

One-page map of every component currently shipped, grouped by R-P-E-R-S layer.
Use this to (a) find the right CLI for a stage, (b) audit what's load-bearing
vs. ceremonial, (c) plan substitutions or extensions.

> Audience: maintainer / contributor / agent making product-shape decisions.
> If you're a first-contact agent, use `AGENTS.md` instead.

---

## At a glance — one verb per stage

```
[pre]  🛠️ Setup       install · verify-install · refresh-manifest · doctor · install-hook · init
[pre]  🧭 Route        route                    → next_step.action enum
 R     🧠 Research     preflight + capabilities → repers.preflight.v1 / repers.capability_query.v1
 P     ⚡ Plan          plan                     → repers.plan.v1  (cycle + missing-dep validated)
 E     ⚡ Execute       dispatch + run           → repers.dispatch.v1 manifest → step_result.v1 per worker
 R     🔗 Review       review                   → repers.review.v1  (schema-validates each step_result)
 S     🔗 Ship          shipping + release-pack  → repers.shipping.v1 + repers-release-pack.zip + 4 install fixtures
```

Every stage emits a JSON artifact with a versioned schema. That's the contract; the implementation behind it is replaceable.

---

## Stage-by-stage component table

### 🛠️ Setup — install the contract layer

| CLI subcommand | Output schema | What it solves |
|---|---|---|
| `install --target <repo>` | text + manifest written | One-command install of `.repers/` into any git repo |
| `verify-install --json` | `repers.install_verify.v1` | Sha256 + size check on all 43 installed files; emits actionable `hint` if just stale-manifest |
| `refresh-manifest --json` | `repers.refresh_manifest.v1` | Update hashes after intentional in-place edits |
| `doctor --json` | (dict) | Python / git / hook / optional backend health |
| `install-hook --hook-policy warn\|strict` | text | Install pre-commit hook |
| `bundle-status [--package --verify-roundtrip]` | `repers.bundle_status.v1` | One-shot rollup of install + doctor + package |
| `init --task <name>` | text | Scaffold `repers_tasks/<name>/` with 4 templates |

### 🧭 Router — decide which slice of the pipeline fits

| CLI subcommand | Output schema | What it solves |
|---|---|---|
| `route --task "..." [--est-files N] --json` | `repers.router.v1` | Map task description → permutation enum (`skip` / `R-only` / `R-S` / `R-E-R` / `R-P-E-R` / `R-P-E-R-S`) + `next_step.action` for agent handoff |
| `/repers-route` skill | (same) | Codex/Claude skill wrapper |

### 🧠 R · Research — memory & reuse

| CLI subcommand | Output schema | What it solves |
|---|---|---|
| `preflight --query/--task "..." --refresh --json` | `repers.preflight.v1` | Search local files + capability registry + (optional) CodeGraph; emit reuse/extend/create recommendation |
| `capabilities --action {search\|validate\|list} --json` | `repers.capability_query.v1` / `…validation.v1` | Query / validate the 25-entry registry |
| `--codegraph[-bin\|-init\|-limit]` flags on preflight | (embedded) | Optional CodeGraph evidence adapter |
| `research.md` template | file (per task) | Free-text research notes that survive the session |

### ⚡ P · Plan — parallel-decomposed DAG

| CLI subcommand | Output schema | What it solves |
|---|---|---|
| `plan --task <name> [--from-research] [--json]` | `repers.plan.v1` | Parse `plan.md` → `plan.json`; validate cycles + missing deps; infer per-step `mode` |
| `plan.md` template | file | Markdown DAG declaration (human + agent editable, PR-reviewable) |
| `dag --help` | (dict) | Manual DAG inspection / status update |

### ⚡ E · Execute — parallel worker dispatch

| CLI subcommand | Output schema | What it solves |
|---|---|---|
| `dispatch --task <name> --max-workers N [--backend X] --json` | `repers.dispatch.v1` | Produce manifest: workers, batches, per-worker target_files. **Collision-safe batching enforced** |
| `run --action {dry-run\|local} [--backend X] [--worker-command "..."] --json` | `repers.run_plan.v1` / `…run_result.v1` | Supervisor-side execution for `mode=local` steps |
| `fixture --action prove --json` | `repers.orchestration_fixture.v1` | Offline proof the dispatch contract holds — runs without any live agent |
| `step_result.v1` schema | (worker writes file) | The worker→supervisor contract; `AGENTS.md § Appendix B` is the spec |
| `--backend {local,worker-command,openai-agents,langgraph,mcp}` | (selects executor) | Plug in different agent runtimes |

### 🔗 R · Review — schema-validate the join

| CLI subcommand | Output schema | What it solves |
|---|---|---|
| `review --task <name> [--update-status] --json` | `repers.review.v1` | Validate every `step_result.v1` artifact; flag missing keys / status/returncode contradictions |
| `--update-status` flag | (also writes plan.md + plan.json) | v0.1.1: writes both plan.md AND auto-refreshes plan.json |

### 🔗 S · Ship — export for downstream consumption

| CLI subcommand | Output schema | What it solves |
|---|---|---|
| `shipping --task <name> --json` | `repers.shipping.v1` | Task-level delivery evidence (artifacts + summary + warnings) |
| `release --task <name> [--strict-warnings] [--update-status] --json` | (composite) | review + doctor + shipping + audit in one gate |
| `release-pack --json` | `repers.release_pack.v1` | Build `repers-release-pack.zip` (install + readiness + handoff + bootstrap + benchmark + state) |
| `release-pack-verify --archive <zip> --json` | `repers.release_pack_verification.v1` | **Receiver-side**: re-verify checksums + embedded evidence without trusting sender |
| `release-evidence [--package] [--verify-roundtrip] --json` | `repers.release_evidence.v1` | Publish-readiness rollup |
| `receiver-fixture --json` | `repers.receiver_fixture.v1` | Install pack into fresh git repo, run 11 receiver-side commands |
| `source-install-fixture --json` | `repers.source_install_fixture.v1` | One-command source→target install proof |
| `publish-clone-fixture --json` | `repers.publish_clone_fixture.v1` | bare-remote push + clone + re-verify (air-gapped) |
| `remote-bootstrap [--apply] --json` | `repers.remote_bootstrap.v1` | Generate (or apply) remote setup + push handoff |
| `remote-bootstrap-fixture --json` | `repers.remote_bootstrap_apply_fixture.v1` | Prove `--apply` path against a temp bare remote |
| `publish-handoff --json` | `repers.publish_handoff.v1` | Non-destructive push/PR handoff artifact |
| `verify-all --json` | `repers.verify_all.v1` | Run 13 gates sequentially in isolated outputs |

### 🧠 Meta — slim after v0.2.0

| CLI subcommand | Status |
|---|---|
| `state [--output] --json` | slim repo state rollup (git + package + capabilities). v0.2 dropped `objective` + `next` fields. |
| `audit [--strict-warnings]` | pre-shipping checks. Backs the pre-commit hook. |

> **v0.2.0 BREAKING (removed)**: `objective-audit`, `continue`,
> `snapshot-freshness`, `open-source-benchmark`. These were self-referential
> to RePERS's own publication objective and had no value to receivers.
> See [`CHANGELOG.md`](../CHANGELOG.md) v0.2.0.

### 🧠 Skills (Codex/Claude plugin layer)

| Skill | Wraps |
|---|---|
| `/repers-init` | install + verify-install + doctor + install-hook |
| `/repers-route` | route |
| `/repers-bug-hunt` | route → (preflight + plan + dispatch + workers + review + run + shipping) per recommended permutation |
| `/repers-release-pack` | release-pack + release-pack-verify |
| `/repers-sinkin` | state + capabilities validate + drift check (meta) |

---

## CLI coverage today

**Almost everything is CLI.** Every stage emits versioned JSON. That's the
baseline for "shell command in, JSON out" composability — anything that
matches the contract can be substituted.

What's NOT currently a CLI:
- `dag_engine.py` — internal library (plan parser)
- `dispatch backends` — enum, not a registered plugin
- `result schema validator` — hardcoded in `reviewer.py`
- `plan.md parser regex` — hardcoded in `dag_engine.py`
- `router decision tree` — hardcoded in `router.py`

These are the **fork-or-extend points** that v0.2 should turn into proper
plugin slots (config-discoverable, swappable without editing core).

---

## High-level shape: 7 verbs × 1 schema each

If you read nothing else, the harness is:

```
verb        schema written        what it lets you swap
─────────────────────────────────────────────────────────────────
route       repers.router.v1      decision-tree heuristic (today) → LLM router (v0.3)
preflight   repers.preflight.v1   registry+grep search (today) → embeddings+codegraph (later)
plan        repers.plan.v1        markdown parser (today) → YAML/Mermaid/JSON parser (later)
dispatch    repers.dispatch.v1    collision-safe batching (today) → priority/cost-aware (later)
worker      repers.step_result.v1 (any agent runtime — contract is JSON-in/JSON-out)
review      repers.review.v1      schema validator (today) → semantic verifier (later)
ship        repers.shipping.v1    release-pack format (today) → SBOM / SLSA provenance (later)
```

Everything else (META, fixtures, skills, docs) is scaffolding around these 7.

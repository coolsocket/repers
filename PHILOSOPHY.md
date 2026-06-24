# PHILOSOPHY.md — three layers, three purposes

RePERS is **`R`**esearch · **`P`**lan · **`E`**xecute · **`R`**eview · **`S`**hip.
Five stages, grouped into **three layers, each with a distinct purpose**.
Understanding the three purposes is how you decide which stages to actually
run for any given task. The router automates that decision; this document
explains the model the router encodes.

If you're an AI agent: the practical playbook is at [`AGENTS.md`](./AGENTS.md).
This file is the *why*. AGENTS.md is the *what to do*.

---

## The three layers

| Layer | Stages | One-line purpose | Who it serves |
|---|---|---|---|
| 🧠 **Memory & Reuse** | **R**esearch (preflight) | Sediment knowledge across sessions; don't rebuild what exists | The *future self* / the *future agents* |
| ⚡ **Speed & Effect** | **P**lan + **E**xecute (DAG + dispatch) | Decompose into disjoint lanes; parallelize without collision | The *current* work-in-flight |
| 🔗 **Alignment & Export** | **R**eview + **S**hip (join + pack) | Make the output consumable by parties not in this session | The *downstream*: other repos / teams / vendors / auditors |

**One-sentence summary**:
**R lets knowledge compound; P+E makes the doing fast and parallel; R+S makes the result transferable beyond the session.**

You don't always need all three. The router picks per task.

---

## 🧠 Layer 1 — Memory & Reuse (Research / preflight)

> **The question this layer answers**: *"Has someone (me-in-the-past, my teammate, my other agent session) already built or learned this?"*

### What it ships
- `preflight --query "<intent>" --json` — searches a typed capability registry, repo file index, and (optionally) a code-graph for anything semantically close to the intent.
- `capabilities/registry.json` — typed inventory of reusable workflows / scripts / hooks / gates. Each entry has `id`, `kind`, `summary`, `commands`, `paths`, `verification`.
- `research.md` template in every task workspace — humans / agents jot what they learned. It accumulates.
- `repers-sinkin` (drift audit) — keeps the sediment honest against live state.

### Why it matters at scale
At Day 0 you remember everything you built last week. At 50 k LOC you don't. At 200 k LOC across 4 teams **using 3 different agents**, your teammate's Codex session is rebuilding what your Claude session built yesterday — and neither knows. The capability registry is the *shared memory* across agents; preflight is the *query*. Without this layer, the org rebuilds the same workflow N times.

### When to skip
For one-off throwaway tasks. A 4-line bug fix needs no memory. The router's `skip_harness` decision is "your memory layer for this task is your own head, not a registry."

### The honest gap
v0.1 registry is mostly *self-inventory* (it lists the harness's own scripts). The richer flavor — **"what did past tasks of similar type look like"** — is on the v0.2 roadmap. Today the registry catches duplicate *capabilities*; v0.2 will catch duplicate *kinds of work*.

---

## ⚡ Layer 2 — Speed & Effect (Plan + Execute / DAG + dispatch)

> **The question this layer answers**: *"How do I get this done faster AND with fewer mistakes than one agent could in series?"*

### What it ships
- `plan.md` template + `plan --json` — markdown-friendly DAG declaration with `target_files` per step. Mode auto-inferred: present `verification_command` → local; absent → subagent.
- `dispatch --max-workers N --json` — produces `repers.dispatch.v1` manifest assigning each step to a worker, with collision-safe batching (no two workers in the same batch write the same file).
- `orchestration-fixture` — deterministic offline test proving the dispatch contract before any live agent runs.
- `run --action local` — supervisor-side execution of `mode=local` steps (e.g., test verification).

### Why it matters at scale
Speed alone is a runtime concern — any agent runtime parallelizes. The **collision contract** is the load-bearing addition: when N agents (yours and your teammates') are working on the same area at the same time, **target-file isolation** is what prevents the last writer from clobbering the first. The fixture proves this property *before* live agents are pointed at the lanes.

### When to skip
When the task is genuinely one-file or single-function. Parallelism over one work-item is just overhead. The router's `R-E-R` decision is "you don't need lanes; you need a tight read/edit/verify loop."

### Why the plan format is opinionated
`plan.md` is human-editable markdown, not YAML or JSON. The reason: in a multi-agent fleet, the plan is the **inter-agent contract**, and it has to be diff-able, comment-able, and PR-review-able by humans who don't run Claude. Markdown is the universal middle.

---

## 🔗 Layer 3 — Alignment & Export (Review + Ship / join + pack)

> **The question this layer answers**: *"Can someone NOT in this chat — a reviewer, an auditor, a downstream repo, a different vendor's agent — pick this up and verify it independently?"*

### What it ships
- `step_result.v1` contract — every worker writes a JSON artifact with a fixed schema; missing or malformed fields fail review.
- `review --update-status --json` — validates all worker results, updates `plan.md` statuses, auto-refreshes `plan.json`.
- `shipping --task <name> --json` — writes a delivery-evidence artifact with the task's full provenance chain.
- `release-pack` — a single transferable zip containing install archive + readiness + evidence + handoff + bootstrap + benchmark + state.
- `release-pack-verify` — the receiver's side: re-verifies checksums + manifest + embedded evidence *without trusting the sender's vendor or JSON*.
- 4 install fixtures (`receiver-fixture`, `source-install-fixture`, `publish-clone-fixture`, `remote-bootstrap-fixture`) — prove the receive-and-verify path from 3 different start states.

### Why it matters at scale
At the small end, your audit trail is the git log + the chat transcript. At enterprise scale neither survives: the chat is ephemeral, the git log shows the patch but not the reasoning chain, and across vendors no one can read each other's transcripts anyway. **JSON evidence is the only audit format that survives** vendor swaps, team handoffs, and trust boundaries. The release pack is what gets attached to the PR that says "Team A's Codex agent did this, here's the evidence chain, Team B's CI can re-verify it without re-running anything."

### When to skip
When the work is staying in your session and getting committed by you. The "Ship" stage is for handoff; if there's no handoff, `shipping` is overhead. (The router routes `R-P-E-R` instead of `R-P-E-R-S` for in-domain work.)

### The under-told story
This layer is RePERS's strongest under-promoted feature. Most agent harnesses ship a runtime; very few ship a **cross-trust-boundary verification protocol**. The release pack is that protocol.

---

## How the layers interact (the router's job)

The router (`route --task "..." --json`) reads task description + repo signals and outputs a permutation: which layers to actually fire.

| Permutation | Layers | When |
|---|---|---|
| `skip` | (none) | Trivial — the harness is overhead. Naked tools win. |
| `R-only` | 🧠 R | Spike. Want memory of "we looked at this and decided…", don't want to build yet. |
| `R-S` | 🧠 R + 🔗 S | Docs/config-only change. Skip the doing layer; just sediment + export. |
| `R-E-R` | 🧠 R + (E) + 🔗 R | Hotfix. One file, test pins answer. Lightweight memory + naked execute + lightweight review. |
| `R-P-E-R` | 🧠 R + ⚡ P+E + 🔗 R | Multi-file in one domain. Memory + parallel + review. Skip export. |
| `R-P-E-R-S` | 🧠 R + ⚡ P+E + 🔗 R+S | Full pipeline. Multi-domain, multi-day, multi-agent, multi-team. Every layer pays. |

**No permutation activates a stage whose layer-purpose doesn't apply.**
That's the philosophy enforced in code.

---

## What this is NOT

- **Not a runtime.** RePERS does not call LLMs. Other harnesses (LangGraph, CrewAI, OpenHands, your own dispatcher) do. RePERS is the contract those runtimes can share.
- **Not a productivity tool for one developer.** A single dev with a single agent on a single repo will measure RePERS as net overhead (we did — 5.8× on a 4-line bug). The router will tell that dev to skip the harness. The value is *multi*.
- **Not a competitor to existing agent frameworks.** Layered above, not against. A LangGraph graph can produce `step_result.v1` artifacts; a CrewAI crew can read a `dispatch.v1` manifest. The contracts are JSON; the implementations are yours.
- **Not "always use all five stages".** Force-fitting the full pipeline onto small work is the documented failure mode. The router exists precisely to route AWAY from this.

---

## How to evaluate RePERS for your context

Use this mental decision tree:

1. **Are multiple AI agents (yours, your teammates', other vendors') ever working on the same codebase at the same time?**
   - No → you don't need the dispatch contract. Maybe install for the memory/export layers only, maybe skip entirely.
   - Yes → continue.

2. **Do agent outputs need to be consumable by parties not in the original session (other agents, teammates, auditors, downstream repos)?**
   - No → install for memory + parallelism only; skip shipping.
   - Yes → full value.

3. **Is your codebase big enough that "did we build this before?" is a real question?**
   - No (you remember everything) → you don't need preflight / registry. Use just the parallel-execution layer.
   - Yes → memory layer pays.

Most evaluators answer "no, no, no" — and the router will route them away from the harness on every task. **That's a valid evaluation outcome.** RePERS is for the "yes, yes, yes" end of the curve.

---

## Further reading

- [`AGENTS.md`](./AGENTS.md) — the practical playbook for first-contact agents.
- [`README.md`](./README.md) — the human-facing positioning, including the codebase maturity curve and the cross-repo handoff story.
- [`docs/e2e-walkthrough.md`](./docs/e2e-walkthrough.md) — every CLI stage executed end-to-end in 45 s, real output.
- [`dist/repers-positioning-canvas.html`](./dist/repers-positioning-canvas.html) — one-page visual evaluator's view (offline-openable).
- [`CLAUDE.md`](./CLAUDE.md) — only relevant if you're EDITING the harness itself.

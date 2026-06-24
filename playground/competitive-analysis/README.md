# Competitive analysis — the Claude Code skill ecosystem

> Playground note: research artifact. Findings live here for review; if any
> conclusion sticks, distill into `docs/` and update positioning.
> Methodology: WebFetch on actual READMEs + `gh api` for stars/topics. No
> speculation about numbers I didn't see.

**Companion doc**: [`evaluation-methodology.md`](./evaluation-methodology.md) —
how SWE-bench, Aider, METR, and Anthropic evaluate agent harnesses, and
what RePERS should measure to be comparable.

---

## TL;DR — RePERS competes with a real ecosystem I missed last round

The prior competitive analysis named LangGraph / CrewAI / OpenHands etc.
Those are agent **runtimes** and aren't actually in RePERS's market today.
The real competitors are **Claude Code (and cross-harness) skill bundles**.
The three poles already consolidated by the community:

1. **Superpowers** (`obra/superpowers` — Jesse Vincent) — **237k ⭐ / 21k forks**
2. **Matt Pocock skills** (`mattpocock/skills`) — second pole, "skills for real engineers"
3. **ECC** — third pole (mentioned in `Cherzing/claude-code-skills-zh` as "三大体系")

Plus smaller adjacent:
- `Matt-Hulme/claude-power-tools` (69 ⭐) — suggester of workflows/goals/loops/hooks
- `matt-k-wong/mkw-DAG-architect` (14 ⭐) — DAG-shaped *prompt* skill (no real dispatch)
- `zpyoung/quirk` — explicit fusion of Superpowers + Matt Pocock
- `calneymgp/solodev` (2 ⭐) — "brainstorm → plan → code. No ceremony, no vibes"

**RePERS** currently sits at single-digit stars in this market.

---

## Head-to-head, real data

### vs. Superpowers (the elephant)

Quote from their README:
> "Superpowers is a complete software development methodology for your coding agents, built on top of a set of composable skills"

> "subagent-driven-development … having agents work through each engineering task, inspecting and reviewing their work"

| Dimension | Superpowers (today) | RePERS (today) |
|---|---|---|
| Tagline | "complete methodology for coding agents" | "operating layer for multi-agent repo work" |
| Multi-agent dispatch | ✅ `dispatching-parallel-agents` skill | ✅ `dispatch` CLI + `repers.dispatch.v1` |
| Plan as artifact | ✅ `writing-plans` + `executing-plans` | ✅ `plan.md` + `repers.plan.v1` |
| Parallel work isolation | **branch-level** via `using-git-worktrees` | **file-level** via `target_files` |
| Collision-safety proof | None observed | ✅ `orchestration_fixture` offline determinism |
| Router with **skip** | ❌ — "Mandatory workflows, not suggestions" | ✅ — primary purpose of `route` |
| Cross-repo / cross-team handoff | ❌ — distribution via per-harness plugin marketplace | ✅ — `release-pack-verify` lets receiver re-verify w/o trusting sender |
| Cross-harness install | ✅ Claude Code / Codex / Cursor / Gemini / Copilot / 10+ | ❌ Codex + Claude only |
| Skill count | 14+ | 5 |
| Stars | 237 256 | ~5 |
| Forks | 21 065 | 0 |
| Backing | Prime Radiant, paid enterprise tier, Discord, hiring | One maintainer |
| Philosophy | maximalist ("mandatory") | minimalist ("skip when small") |

**The hard truth**: Superpowers **already does** subagent-driven multi-agent work. It claims agents can "work autonomously for a couple hours at a time without deviating from the plan." Their distribution and methodology are 4 orders of magnitude ahead.

What RePERS still has that they **don't**:
- File-level (not branch-level) collision contract proven by offline fixture
- Cross-repo handoff with independent re-verification
- "Skip the harness" router (this is **philosophically opposite** to their pitch)
- Versioned JSON Schemas (`.repers/contracts/*.v*.json`) as substitution points
- Stdlib-only Python (their skills are Shell + per-harness install scripts)

### vs. Matt Pocock skills

Quote from his README:
> "My agent skills that I use every day to do real engineering - not vibe coding."

> "**ask-matt** — A router over the user-invoked skills in this repo."

| Dimension | Matt Pocock | RePERS |
|---|---|---|
| Router | ✅ `ask-matt` (skill-level) | ✅ `route` (stage-level — R/P/E/R/S permutation) |
| Multi-agent / parallel | ❌ explicit no | ✅ |
| DAG decomposition | ❌ (`to-issues` produces tracker tickets, not a DAG) | ✅ `plan.md` + `dag_engine` |
| Handoff | ✅ `handoff` skill — session-level | ✅ `shipping` + `release-pack` (cross-session, cross-repo) |
| Philosophy | "small composable, model-agnostic, anti-autopilot" | "minimal-when-small, full-when-multi-agent" |
| Install | `npx skills@latest add mattpocock/skills` | repers.py install --target |

**Overlap**: both have a router with same name conceptually (Matt's `ask-matt` ↔ our `/repers-route`). His routes between **skills**, ours routes between **pipeline stages**. Different scope.

**Where RePERS still differs**: multi-agent dispatch + cross-repo handoff are explicitly absent in his philosophy ("not vibe coding") — and he's vocal about not wanting them.

### vs. mkw-DAG-architect (honest comparison)

Their own README quote:
> "80% of multi-agent DAG power. 0% setup. Works everywhere Claude does."
> "DAG is the _planning layer_. Real tools are the _execution layer_."
> Their own comparison table: "True parallelism: ❌ Sequential under hood"

| Dimension | mkw-DAG-architect | RePERS |
|---|---|---|
| DAG decomposition | ✅ structured prompting | ✅ |
| Actual parallel dispatch | ❌ (sequential simulated) | ✅ real |
| Roadmap mentions | "Companion MCP server for true parallelism" | already shipped |

This is one place RePERS genuinely is ahead. mkw is honest about being prompt-only.

### vs. claude-power-tools (Matt Hulme)

Quote:
> "Skills that make Claude Code proactively suggest its own power tools"
> "A multi-agent **Workflow** (with pipeline sketch + cost, **never auto-launched**)"

It's a **suggester**, not an executor. Surfaces opportunities to use Claude Code's native workflow/goal/loop features. RePERS actually runs the pipeline.

### vs. quirk / solodev / others

These are explicit derivatives ("Fusion of Matt Pocock, OpenSpec, get-shit-done"). The ecosystem is **already consolidating** around the Superpowers + Matt Pocock axis. Yet-another-bundle is the wrong play.

---

## What this really means

### RePERS's actual unique angles (verified against the ecosystem)

| Angle | Verified-unique because |
|---|---|
| **File-level `target_files` collision contract** | Superpowers uses git-worktrees (branch level); nobody does file-level |
| **Offline `orchestration_fixture` proving dispatch safety** | mkw-DAG-architect admits sequential; Superpowers ships no proof |
| **`release-pack-verify` (cross-trust-boundary re-verification)** | Nobody else even attempts this |
| **Router that says "skip the harness"** | Superpowers explicitly opposite philosophy |
| **Versioned JSON Schemas + plugin-slot architecture** | Nobody has this — everyone forks instead |
| **Stdlib-only Python, no npm/marketplace dependency** | Most ecosystem leans on npx + harness-specific marketplaces |

### RePERS's real disadvantages

| Gap | Reality |
|---|---|
| Mindshare | 237 000 ⭐ vs 5 ⭐ |
| Cross-harness | Codex + Claude only vs Superpowers' 10+ harnesses |
| Skill count | 5 vs Superpowers 14, Matt Pocock 20+ |
| Distribution channel | per-repo install vs cross-marketplace presence |
| Brand owner-of-term | Superpowers owns "subagent-driven-development"; Matt Pocock owns "skills for real engineers" |

### Strategic implication

**Trying to be "another skill bundle" loses to Superpowers / Matt Pocock by 5 orders of magnitude on every metric except technical novelty.** The market has consolidated.

The real options:

| Option | What it means | Realistic |
|---|---|---|
| **A. Compete head-on as skill bundle** | Add more skills, market harder | ❌ Lose on every metric |
| **B. Become the contract SPEC** | Publish `dispatch.v1` / `step_result.v1` / `router.v1` as a standard. Let Superpowers / Matt Pocock implement it. RePERS becomes the spec, others the runtime. | ✅ Real moat. Hard sell |
| **C. Drop in as a Superpowers plug-in** | Ship the unique pieces (file-level isolation, release-pack-verify) as a Superpowers-compatible skill bundle so Superpowers users layer us on | ✅ Realistic — borrow their distribution |
| **D. Narrow to enterprise / cross-team / cross-vendor** | Don't compete in solo-dev land at all. Target "multiple AI vendors in one org, need audit trail" — Superpowers doesn't address this | ✅ Defensible niche |
| **E. Hybrid: B + D** | Publish contracts as spec **and** focus product on cross-team handoff. Open-source the spec, sell support to enterprise. | ✅ Most defensible |

### Recommended pivot (my honest read)

**E. Reposition RePERS as:**

> "The cross-trust-boundary handoff contract for multi-agent SWE work.
> Open spec; reference implementation; sample skill bundle."

Concretely:
1. Stop framing RePERS as a "skill bundle." That market is owned.
2. Push the JSON contracts (`router.v1`, `dispatch.v1`, `step_result.v1`, `review.v1`, `shipping.v1`) as **the spec** anyone can implement. Submit to RFC-like venue (or just write `SPEC.md`).
3. Keep our reference implementation but **call it a reference impl, not the product**.
4. Target audience changes: not "solo dev with Claude Code" → **"platform team running N AI agents across M teams who need a contract layer".**
5. Write a Superpowers-compatible skill that exposes RePERS's unique pieces (file-level isolation, release-pack-verify) — so Superpowers users can layer us on without leaving Superpowers.

### What we should stop doing

- ❌ Trying to grow "skills count" to match competitors
- ❌ Promoting RePERS to solo-dev / hobbyist audience (Superpowers + Matt Pocock own this)
- ❌ Marketing language that overlaps Superpowers' "subagent-driven-development" — rename our internal terminology

### What we should start doing

- ✅ Write `SPEC.md` formalizing the 7 JSON contracts as a vendor-neutral standard
- ✅ Build the Superpowers-compatible skill (uses Superpowers' install path, adds our unique primitives)
- ✅ Find 1 enterprise / OSS-maintainer pilot user who actually has the cross-team / cross-vendor problem
- ✅ Reach out to Jesse Vincent (obra) — propose alignment (we provide the contract spec; Superpowers implements; alliance not competition)

---

## Open questions

1. Is the "contract spec" pivot something the maintainer (you) wants? It changes how the project is described and what success looks like.
2. Is there a real enterprise / OSS-team contact we could pilot with? Without a real adopter the cross-trust-boundary story is theoretical.
3. Should we approach Jesse Vincent / Matt Pocock directly (cold email / GitHub Discussions / Discord) and propose alignment?

---

## Methodology + sources used

- `gh api repos/obra/superpowers` (live API)
- `gh api search/repositories?q="matt claude skills"` (live API)
- WebFetch on `raw.githubusercontent.com/obra/superpowers/main/README.md`
- WebFetch on `raw.githubusercontent.com/mattpocock/skills/main/README.md`
- WebFetch on `github.com/matt-k-wong/mkw-DAG-architect`
- WebFetch on `github.com/Matt-Hulme/claude-power-tools`
- Grep on `/tmp/awesome-claude-code/THE_RESOURCES_TABLE.csv` (cloned earlier)
- Star counts as of 2026-06-24

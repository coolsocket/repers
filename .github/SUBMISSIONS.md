# Awesome-list / marketplace submissions tracker

Drafts ready for review. **NOTHING is submitted yet** — these are local artifacts
the maintainer reviews and then says "open it" before any external PR fires.

---

## Submission 1 — `hesreallyhim/awesome-claude-code`

**Repo health (2026-06-24)**
- 47.2k stars · 542 open issues · **0 open PRs** · "Update in progress" banner
- The maintainer is mid-reorg of the table-of-contents and resources model.
- New entries go through a CSV (`THE_RESOURCES_TABLE.csv`), not direct README edits.
- **Merge likelihood**: low-to-medium short-term (reorg may pause new entries); high once the new structure lands.

### Draft entry (CSV row to add to `THE_RESOURCES_TABLE.csv`)

```csv
wf-repers01,RePERS,Workflows,Multi-agent / Orchestration,https://github.com/coolsocket/repers,,coolsocket,https://github.com/coolsocket,TRUE,2026-06-24:08-00-00,2026-06-24:08-00-00,2026-06-24:08-00-00,MIT,"Operating layer for multi-agent Claude Code work. R-P-E-R-S contract layer (Research · Plan · Execute · Review · Ship) with parallel lanes that don't collide, JSON evidence between agents, verifiable release packs. Ships a deterministic router (/repers-route) that tells you to SKIP the harness when overhead exceeds value — measured 5.8x on a 4-line bug. Plugin with 5 skills: init / route / bug-hunt / release-pack / sinkin.",FALSE,FALSE,2026-06-22:14-25-00,2026-06-23:13-23-00,v0.1.1,github-releases
```

### PR title

`Add: RePERS — multi-agent operating layer (router + parallel dispatch + verifiable release packs)`

### PR body draft

```markdown
## What

Adds [RePERS](https://github.com/coolsocket/repers) (v0.1.1) to the workflows category.

## Why it fits

RePERS is a Claude Code plugin shipping 5 skills (`/repers-init`, `/repers-route`,
`/repers-bug-hunt`, `/repers-release-pack`, `/repers-sinkin`) PLUS a stdlib-only
Python CLI in `.repers/scripts/` installable into any Git repo.

It's deliberately positioned as a **contract layer above** any agent runtime
(Claude Code, Codex, Gemini, LangGraph, CrewAI). Most novel piece: a deterministic
router that recommends *skipping the harness* for tasks too small to earn its
overhead — validated by a benchmark on the sqlfluff__sqlfluff-2419 bug where the
harness measured 5.8× wall-clock cost over a naked agent for functionally
identical patches.

## Category

`Workflows` (top-level) · `Multi-agent / Orchestration` (sub-category)

## Verification

- Live: https://github.com/coolsocket/repers/releases/tag/v0.1.1
- CI: green on ubuntu / windows / macos
- End-to-end CLI walkthrough: https://github.com/coolsocket/repers/blob/main/docs/e2e-walkthrough.md (~45s real run, every command executed)
- License: MIT
```

---

## Submission 2 — `e2b-dev/awesome-ai-agents`

**Repo health (2026-06-24)**
- 24k+ stars · 131 open issues · **644 open PRs**
- Massive review backlog; PRs typically wait weeks to months.
- Format: alphabetical markdown entries under `# Open-source projects`, with a `<details>` block per entry.
- **Merge likelihood**: medium-to-high eventually; slow.

### Draft entry (markdown, alphabetical placement under `# Open-source projects`)

```markdown
## [RePERS](https://github.com/coolsocket/repers)
Operating layer for multi-agent repository work — parallel lanes that don't collide
<details>

### Category
Multi-agent, Build-your-own (agent-builing frameworks and platforms), SDK for agents, Open-source

### Description

- "Not an agent runtime — a *contract layer above* any runtime (Claude / Codex / Gemini / LangGraph / CrewAI / OpenHands). You provide the LLM; RePERS provides the coordination."
- "Five stages: Research (preflight, capability registry as shared memory) → Plan (DAG with target_files isolation) → Execute (parallel dispatch with collision guards) → Review (JSON evidence join) → Ship (transferable release pack another repo can re-verify without trusting the sender)."
- "Ships a deterministic router that picks a permutation per task. For tasks too small to earn the harness's overhead, the router tells the calling agent to skip — measured 5.8× wall-clock cost on a 4-line bug fix."
- "Stdlib-only Python runtime, no extra deps. JSON-in / JSON-out contracts at every stage so different vendor agents (or different teams' agents) can hand off without trust."
- "Plugs into Claude Code as a 5-skill plugin (init / route / bug-hunt / release-pack / sinkin) but the core contracts are AI-agnostic."

### Links

- [GitHub](https://github.com/coolsocket/repers)
- [Philosophy](https://github.com/coolsocket/repers/blob/main/PHILOSOPHY.md) — the three-layer model
- [Agent first-contact playbook](https://github.com/coolsocket/repers/blob/main/AGENTS.md)
- [End-to-end walkthrough](https://github.com/coolsocket/repers/blob/main/docs/e2e-walkthrough.md) — real CLI in 45 s

</details>
```

### PR title

`Add: RePERS — contract layer above any agent runtime (multi-agent · parallel dispatch · verifiable handoff)`

### PR body draft

```markdown
## What

Adds [RePERS](https://github.com/coolsocket/repers) (v0.1.1, MIT) to `# Open-source projects`.
Placed alphabetically between [Q*] entries (after the last 'R' or before 'S' entries).

## Why it fits the list

The list already includes runtimes that EXECUTE multi-agent calls (CrewAI,
AgentVerse, GPTSwarm, FastAgency). RePERS occupies a different layer: it's the
contract that SITS ABOVE any of those runtimes so N agents (any vendor) can
share dispatch, collision-avoidance, and evidence handoff. Concretely it ships
4 install fixtures proving the receive-and-verify path from 3 different start
states — a cross-trust-boundary handoff protocol that most agent harnesses
don't ship.

The router is the differentiator: it's the only harness I'm aware of that
deterministically tells the calling agent **not** to use itself for small
tasks, backed by a measured 5.8× overhead benchmark on a real bug.

## Closest peers in the list

- CrewAI, AgentVerse, GPTSwarm, FastAgency — runtimes RePERS layers above
- Adala, Langroid — multi-agent orchestrators
- Eidolon — multi-agent SDK

## Verification

- Live: https://github.com/coolsocket/repers/releases/tag/v0.1.1
- CI: green on 3 platforms
- License: MIT, stdlib-only Python, no extra deps at runtime
```

---

## Submission 3 — Codex / Claude Code plugin marketplaces

**TBD** — needs more research on whether there's a centralized marketplace
beyond the README mention of `/plugin marketplace add coolsocket/repers`.
The `.codex-plugin/plugin.json` is already shaped for this. Hold until we
know the official submission path.

---

## Submissions we are NOT planning

- **Show HN** — wait until we have ≥1 external adopter / case study. Premature.
- **dev.to / Substack long-form** — drafting separately; not a list submission.
- **Twitter / X thread** — maintainer's call; not something this repo opens.
- **Hacker News show post** — same as Show HN above.
- **Reddit r/MachineLearning, r/LocalLLaMA** — wait for organic traction first.

---

## How to actually open these PRs

When the maintainer approves a draft above:

```bash
# Submission 1 (awesome-claude-code):
gh repo fork hesreallyhim/awesome-claude-code --clone --remote
cd awesome-claude-code
# Append the CSV row to THE_RESOURCES_TABLE.csv (or use their tooling if applicable)
git add THE_RESOURCES_TABLE.csv
git commit -m "Add: RePERS — multi-agent operating layer"
git push origin HEAD:add-repers
gh pr create --repo hesreallyhim/awesome-claude-code \
  --title "Add: RePERS — multi-agent operating layer (router + parallel dispatch + verifiable release packs)" \
  --body-file /tmp/repers-pr-body.md

# Submission 2 (awesome-ai-agents):
# Same fork-then-PR pattern, edit README.md alphabetically.
```

Each PR should reference this `SUBMISSIONS.md` so reviewers can see the
provenance / draft history.

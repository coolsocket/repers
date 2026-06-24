# Awesome-list / marketplace submissions tracker

Status log of submission attempts. **Read the "Outcome" line on each entry
first** — several attempted channels turned out to be wrong-fit or
human-only.

---

## Submission 1 — `hesreallyhim/awesome-claude-code` · ❌ BLOCKED (human-only)

**Outcome (2026-06-24)**: cannot be submitted by an AI agent. Their
`docs/CONTRIBUTING.md` explicitly says:

> "ALL RECOMMENDATIONS MUST BE MADE USING THE WEB UI ISSUE FORM TEMPLATE,
> OR YOU RISK BEING BANNED FROM INTERACTING WITH THIS REPOSITORY
> TEMPORARILY OR PERMANENTLY."
>
> "It is **not** possible to submit a resource recommendation using the gh CLI."
>
> "resource recommendations must be created by human beings."

The draft CSV row + PR body below is retained so the maintainer can
manually submit via the [issue form](https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml).

**Repo health (2026-06-24)**
- 47.2k stars · 542 open issues · **0 open PRs** · "Update in progress" banner
- The maintainer is mid-reorg of the table-of-contents and resources model.
- New entries go through a CSV (`THE_RESOURCES_TABLE.csv`), not direct README edits.
- **Merge likelihood**: low-to-medium short-term (reorg may pause new entries); high once the new structure lands.

### Draft entry (CSV row to add to `THE_RESOURCES_TABLE.csv`)

```csv
wf-repers01,RePERS,Workflows,Multi-agent / Orchestration,https://github.com/coolsocket/repers,,coolsocket,https://github.com/coolsocket,TRUE,2026-06-24:08-00-00,2026-06-24:08-00-00,2026-06-24:08-00-00,MIT,"Operating layer for multi-agent Claude Code work. R-P-E-R-S contract (Research · Plan · Execute · Review · Ship) with target_files-isolated parallel lanes, JSON evidence handoff between agents, and a transferable release pack another repo can re-verify without trusting the sender. Ships a deterministic per-task router (/repers-route) that picks the right slice of the pipeline so the harness only fires when it earns its weight. 5 skills: init / route / bug-hunt / release-pack / sinkin.",FALSE,FALSE,2026-06-22:14-25-00,2026-06-23:13-23-00,v0.1.1,github-releases
```

### PR title

`Add: RePERS — multi-agent operating layer (router + parallel dispatch + verifiable release packs)`

### PR body draft

```markdown
## What

Adds [RePERS](https://github.com/coolsocket/repers) (v0.1.1) to the workflows category.

## Why it fits

RePERS is a Claude Code plugin shipping 5 skills (`/repers-init`, `/repers-route`,
`/repers-bug-hunt`, `/repers-release-pack`, `/repers-sinkin`) plus a stdlib-only
Python CLI installable into any Git repo.

What's novel for Claude Code users:

- **A contract layer above the runtime.** When multiple Claude Code sessions
  (or Claude + Codex + Gemini) work on the same repo at once, RePERS gives
  them target-file-isolated lanes so they don't clobber each other, plus
  JSON evidence so each can pick up where another left off.
- **A transferable release pack.** `repers-release-pack.zip` is a bundle
  another team or repo extracts and re-verifies independently — auditable
  handoff across vendors / orgs / trust boundaries. 4 install fixtures
  prove the receive-and-verify path from 3 different start states.
- **A per-task router.** Deterministic `/repers-route` skill that picks
  which slice of the R-P-E-R-S pipeline fits the task (skip / R-only /
  R-S / R-E-R / R-P-E-R / R-P-E-R-S), so the harness fires only when its
  shape matches the work.

## Category

`Workflows` (top-level) · `Multi-agent / Orchestration` (sub-category)

## Verification

- Live: https://github.com/coolsocket/repers/releases/tag/v0.1.1
- CI: green on ubuntu / windows / macos
- End-to-end CLI walkthrough: https://github.com/coolsocket/repers/blob/main/docs/e2e-walkthrough.md (~45 s real run, every command executed)
- Philosophy / when-to-use scope: https://github.com/coolsocket/repers/blob/main/PHILOSOPHY.md
- License: MIT, stdlib-only Python, no extra runtime deps
```

---

## Submission 2 — `e2b-dev/awesome-ai-agents` · ❌ WRONG LIST (redirect to SDKs)

**Outcome (2026-06-24)**: scope mismatch. The list's own README says:

> "This list is only for AI assistants and agents. For adding AI agents'-related
> SDKs, frameworks and tools, please visit [Awesome SDKs for AI Agents](https://github.com/e2b-dev/awesome-sdks-for-ai-agents)."

RePERS is an SDK / framework, not an agent. Submitting to this list
would just be politely redirected; opening that PR is wasted work.
**Use Submission 3 below instead.**

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
- "Ships a deterministic per-task router that picks the right slice of the pipeline (skip / R-only / R-S / R-E-R / R-P-E-R / R-P-E-R-S) so the harness only fires when the work shape benefits from it. No LLM call, sub-100ms, offline."
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
share dispatch, collision-avoidance, and evidence handoff.

Two things that are uncommon in the agent-harness space:

1. **A transferable release pack** (`repers-release-pack.zip`) that another
   repo extracts and **re-verifies independently without trusting the
   sender's vendor or JSON.** 4 install fixtures (`receiver-fixture`,
   `source-install-fixture`, `publish-clone-fixture`,
   `remote-bootstrap-fixture`) prove the receive-and-verify path from 3
   different start states. This is the cross-trust-boundary handoff
   protocol most agent harnesses don't ship.

2. **A deterministic per-task router** that picks which slice of the
   R-P-E-R-S pipeline matches the task shape (skip / R-only / R-S /
   R-E-R / R-P-E-R / R-P-E-R-S). Sub-100ms, no LLM call, offline. Makes
   the harness opinionated about its own fit instead of forcing every
   task through every stage.

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

## Submission 3 — `e2b-dev/awesome-sdks-for-ai-agents` · ✅ OPENED

**PR**: https://github.com/e2b-dev/awesome-ai-sdks/pull/256 (opened 2026-06-24)

**Outcome (2026-06-24)**: this is the right list. Same maintainer as
Submission 2, but scoped to "SDKs, frameworks, libraries, and tools for
creating, monitoring, debugging and deploying autonomous AI agents".
Existing entries include Chidori, Langchain, Steamship, AgentOps,
Helicone, Vercel AI SDK — all framework/infra plays, none individual
agents. RePERS fits cleanly alongside. Placed alphabetically between
LangSmith and SID.

**Format**: H2 + one-line tagline + `<details>` collapsible (Description
+ Links). Flat alphabetical, no category subsections.

### Draft entry (markdown — placed alphabetically; RePERS goes between SID and Steamship)

```markdown
## RePERS

The operating layer for multi-agent repository work — parallel lanes that don't collide, JSON evidence handed off between agents, transferable release packs another repo can re-verify.

<details>

### Description

- "Not an agent runtime — a contract layer above any runtime (Claude / Codex / Gemini / LangGraph / CrewAI / OpenHands). You provide the LLM; RePERS provides the coordination."
- "Five stages: Research (preflight, capability registry as shared memory) → Plan (DAG with target_files isolation) → Execute (parallel dispatch with collision guards) → Review (JSON evidence join) → Ship (transferable release pack another repo can re-verify without trusting the sender)."
- "Ships a deterministic per-task router that picks the right slice of the pipeline so the harness only fires when the work shape matches it. No LLM call, sub-100ms, offline."
- "Stdlib-only Python runtime, no extra deps. JSON-in / JSON-out contracts at every stage so different vendor agents can hand off without trust."

### Links

- [GitHub](https://github.com/coolsocket/repers)
- [Philosophy](https://github.com/coolsocket/repers/blob/main/PHILOSOPHY.md)
- [Agent first-contact playbook](https://github.com/coolsocket/repers/blob/main/AGENTS.md)
- [End-to-end walkthrough](https://github.com/coolsocket/repers/blob/main/docs/e2e-walkthrough.md)

</details>
```

### PR title

`Add RePERS — operating layer for multi-agent repository work`

### PR body

```markdown
## What

Adds [RePERS](https://github.com/coolsocket/repers) (v0.1.1, MIT,
stdlib-only Python) to the list.

## Why it fits

RePERS occupies a layer above the agent runtimes already on this list.
Where Chidori, Langchain, and Steamship execute LLM calls, RePERS is the
contract sitting above any of them so N agents (your own, your teammates',
different vendors') can carve up the same codebase without clobbering each
other's lanes, hand off via JSON evidence, and ship a release pack a
downstream repo extracts and re-verifies independently without trusting
the sender's vendor or JSON.

Two pieces that are uncommon in the agent-infra space:

1. **A transferable release pack** with 4 install fixtures proving the
   receive-and-verify path from 3 different start states.
2. **A deterministic per-task router** that picks which slice of the
   R-P-E-R-S pipeline matches the work shape (skip / R-only / R-S /
   R-E-R / R-P-E-R / R-P-E-R-S), so the harness fires only when its
   shape benefits the task.

Placed alphabetically between SID and Steamship.

## Verification

- v0.1.1: https://github.com/coolsocket/repers/releases/tag/v0.1.1
- CI: green on ubuntu / windows / macos
- End-to-end CLI walkthrough (real run, 45s wall-clock): https://github.com/coolsocket/repers/blob/main/docs/e2e-walkthrough.md
- License: MIT, no extra runtime deps
```

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

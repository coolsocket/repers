# Promotion Playbook

RePERS should be promoted as a narrow developer tool:

```text
An installable harness that makes agent-run repository work preflighted,
planned, reviewable, and transferable without relying on chat history.
```

## Primary Users

| User | Problem | RePERS Promise |
|---|---|---|
| Maintainer using coding agents | Agent work is hard to resume or audit | Every run leaves task artifacts, state, and release evidence |
| Tooling builder | Repeated workflows become scattered scripts | Capabilities are JSON-indexed and searchable by preflight |
| Reviewer | Multi-agent claims are weak or unverifiable | Worker lanes must join through review and verification gates |
| Adopter testing a harness | Install paths often break outside the source repo | Package, receiver, clone, source-install, and release-pack fixtures prove reuse |

## Public Message

Use this short description for GitHub and launch posts:

```text
RePERS is a local-first harness for agent-run repo work: preflight reusable
capabilities, build a task DAG, coordinate worker lanes, review evidence, and
ship a verifiable release pack.
```

Use this shorter repository description:

```text
Local-first agent workflow harness: preflight, DAG planning, worker review,
hooks, and verifiable release packs for repository tasks.
```

## Channels

| Channel | What to show |
|---|---|
| GitHub README | 30-second value statement, quick start, bug-hunt flow, release assets |
| GitHub Release | `repers-0.1.0.zip`, `repers-release-pack.zip`, checksums, verification commands |
| Hacker News / Reddit / Discord | A concrete bug-hunt walkthrough, not a broad agent manifesto |
| Agent/tooling communities | Capability registry, preflight reuse, JSON handoff contracts |
| Maintainer docs | Install path, hook policy, troubleshooting, security/support |

## Launch Checklist

- README first screen explains the product before listing commands.
- Repository description and topics are set.
- `LICENSE` exists and package archive includes it.
- GitHub Release has the install archive and release pack attached.
- Demo page shows a single bug-hunt run from request to evidence.
- `verify-all --json` passes locally.
- `release-pack-verify` passes against the published asset.
- `SUPPORT.md`, `SECURITY.md`, `CONTRIBUTING.md`, and `ROADMAP.md` are visible.

## Anti-Patterns

- Do not lead with every generated `dist/*.json` file.
- Do not describe RePERS as a general agent framework.
- Do not claim real parallel subagent execution from the deterministic fixture
  alone. Say the fixture proves the protocol.
- Do not require optional CodeGraph or cloud backends for the first install.

## Source Patterns Used

The current shape follows the stored benchmark in
`.repers/docs/open-source-benchmark.json` and the study in
`.repers/docs/open-source-structure-study.md`: visible README, governance,
automation, examples, tests, package gates, and contributor instructions.

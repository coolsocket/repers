# RePERS Autonomous Architecture

RePERS should be a local-first workflow operating layer, not a monolithic agent
framework. The core owns contracts, state, evidence, and gates. External agent
frameworks are adapters.

## Current Core

Implemented:

- `init`: create task artifacts from templates.
- `preflight`: search for existing capabilities.
- `index`: build/search a local SQLite FTS index.
- `capabilities`: list, search, and validate the packaged local capability
  registry.
- `research`: write `research.md` and `research.json` from index evidence.
- `plan`: generate `plan.json` from `plan.md` and `research.json`; `--from-research` writes proposed DAG artifacts.
- `run`: show dry-run batches, execute ready local steps, run worker prompts through `worker-command`, run worker prompts through the optional OpenAI Agents SDK adapter, or execute worker batches through the optional LangGraph adapter.
- `dispatch`: write conflict-safe parallel worker manifests and prompt packets for ready non-local steps.
- `fixture`: create and prove a deterministic large-task orchestration fixture
  through dispatch, worker-command execution, local join verification, and
  review.
- `receiver-fixture`: install the packaged archive into a fresh Git repository
  and prove installed receiver commands.
- `review`: validate result JSON contracts for a task and optionally update `plan.md` statuses.
- `shipping`: write machine-readable delivery evidence for a task.
- `release`: run review, doctor, shipping, and audit as one machine-readable release gate.
- `release-evidence`: write publish-readiness evidence that records package,
  governance, capability registry, and Git branch/commit/remote state.
- `release-pack`: compose the installable package and generated evidence into
  one transferable handoff archive.
- `package`: create a distributable RePERS zip archive with a package manifest.
- `install-hook`: install or refresh the RePERS `pre-commit` hook.
- `verify-install`: verify `.repers/manifest.json` against installed bundle files.
- `doctor`: check Python, Git, hook, index, optional LSP Guard, and backend adapter readiness; `--fix` repairs hook/index state.
- `dag`: parse `plan.md`, list steps, show ready steps, update status.
- `audit`: check Git state, task artifacts, temp files, and optional LSP Guard; `--strict-warnings` lets teams fail on warnings.
- `install_repers.py`: install `.repers`, `.repers/manifest.json`, and Git hook into another repository.
- Hook policy: installer and `install-hook` support `warn` and `strict` warning policies.
- Optional CodeGraph evidence in `preflight --codegraph`: attach structural code
  evidence when a CodeGraph CLI/index exists, and emit a structured fallback
  when CodeGraph is unavailable or the index has not been initialized.

## Technology Decisions

| Layer | Technology | Role |
|---|---|---|
| Local search/index | SQLite FTS5 | Durable local capability index without a service dependency. |
| Workflow model | RePERS DAG contracts + optional LangGraph adapter | Stateful graph execution, ready queues, parallelizable steps. |
| External agent backend | Worker command adapter, OpenAI Agents SDK adapter | Current command-template execution and optional execution through `agents.Agent` + `Runner` with guarded local function tools; future handoffs, guardrails, and richer tracing. |
| External tools/capabilities | MCP adapter | Future discovery of tool/resource/prompt capabilities from MCP servers. |
| Structural code inventory | Optional CodeGraph CLI now, Tree-sitter adapter later | CodeGraph supplies structural evidence during preflight; tree-sitter can later add local symbol extraction without a service dependency. |
| Repo installation | Local `.repers` bundle + Git hook | Works before PyPI/global PATH packaging exists. |
| Installed bundle evidence | `.repers/manifest.json` + `verify-install` | Records bundle version, source state, hook policy, copied file hashes, and verifies install drift. |

LangGraph is a reference architecture for durable, stateful, human-in-the-loop
agent orchestration. RePERS now integrates it as an optional backend that wraps
conflict-safe worker batches in a `StateGraph`; it does not require LangGraph
for the local CLI.

OpenAI Agents SDK is an execution backend, not the RePERS core. RePERS hands it
a worker prompt contract and receives the normal step result contract. The
adapter runs one prompt per `Agent` with `Runner.run_sync` and can attach local
function tools. Tool mode defaults to readonly; workspace mode allows writes
only to the worker's declared target files and runs bounded commands.

MCP should be indexed as capability metadata so RePERS can discover external
tools without hard-coding each connector.

## Data Flow

```text
index refresh
  -> .repers/index/repers.db

capabilities
  -> .repers/capabilities/registry.json
  -> ranked local reusable workflows, scripts, hooks, templates, and gates

preflight --json
  -> capability matches + reuse recommendation
  -> local_capability matches from registry when indexed

preflight --json --codegraph
  -> capability matches + reuse recommendation
  -> optional code_evidence from CodeGraph
  -> structured fallback if CodeGraph/index is unavailable

research --task X --query Y
  -> repers_tasks/X/research.json
  -> repers_tasks/X/research.md

plan --from-research
  -> repers_tasks/X/plan.proposed.json
  -> repers_tasks/X/plan.proposed.md

plan
  -> repers_tasks/X/plan.md
  -> repers_tasks/X/plan.json

run
  -> ready steps
  -> dry-run batches
  -> local execution
  -> result.json per step

run --backend worker-command
  -> dispatch/manifest.json
  -> external worker command per prompt
  -> result.json per worker step

run --backend openai-agents
  -> dispatch/manifest.json
  -> Agent + guarded tools + Runner.run_sync per prompt
  -> result.json per worker step

run --backend langgraph
  -> dispatch/manifest.json
  -> StateGraph batch node
  -> optional memory/sqlite checkpointer + thread_id
  -> command-backed worker execution
  -> result.json per worker step

dispatch
  -> ready non-local steps
  -> conflict-safe batches
  -> dispatch/manifest.json
  -> dispatch/workers/<worker_id>.md

fixture --action prove
  -> repers_tasks/<task>/plan.md
  -> initial dry-run with three ready worker lanes
  -> worker-command dispatch and result JSON files
  -> local join verification
  -> review.json

receiver-fixture
  -> package archive
  -> temporary receiver Git repository
  -> install_repers.py
  -> verify-install, doctor, bundle-status
  -> capabilities validate/search
  -> fixture --action prove inside receiver

review
  -> result JSON contract checks
  -> review.json
  -> pass/fail summary
  -> optional plan.md status update

shipping
  -> artifact inventory
  -> git/doctor/review/dispatch evidence
  -> installed bundle manifest and verification evidence when checked
  -> shipping.json

release
  -> review gate
  -> doctor gate
  -> shipping gate
  -> audit gate
  -> release.json

release-evidence
  -> dist/repers-release-evidence.json
  -> package readiness and optional round-trip evidence
  -> governance and capability registry status
  -> Git publish metadata and missing publish actions

release-pack
  -> package
  -> release-evidence
  -> publish-handoff
  -> remote-bootstrap
  -> open-source-benchmark
  -> state
  -> dist/repers-release-pack.zip

package
  -> dist/repers-<version>.zip
  -> repers-package-manifest.json inside archive

doctor --fix
  -> install hook when missing
  -> refresh index when requested or missing

verify-install
  -> compare .repers/manifest.json with installed files
  -> report missing, changed, and extra files
```

## Next Required Harnesses

1. Add OpenAI Agents handoffs, guardrails, and richer trace capture.
2. Add human-in-the-loop state on top of the LangGraph memory/sqlite checkpoint paths.

## Contract Direction

Markdown remains the human interface. JSON is the machine contract.

Required future files:

```text
repers_tasks/<task>/research.json
repers_tasks/<task>/plan.proposed.json
repers_tasks/<task>/plan.json
repers_tasks/<task>/dispatch/manifest.json
repers_tasks/<task>/results/<step_id>.json
repers_tasks/<task>/review.json
repers_tasks/<task>/shipping.json
```

This gives the autonomous runner a stable surface without losing readable
project artifacts.

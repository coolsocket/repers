# RePERS Artifact Contracts

RePERS keeps Markdown as the human interface and JSON as the machine contract.
Agents may propose changes, but executable state should move through explicit
artifacts so another agent can inspect, run, review, and package the work.

CLI commands that emit machine JSON to stdout use ASCII-escaped JSON so Windows
consoles and parent processes with legacy encodings can consume the output
reliably. JSON artifacts written to disk remain UTF-8 files.

## Research

`research.json` is written by `research --task <task> --query <query>`.

Required top-level fields:

- `query`
- `workspace_root`
- `index_db`
- `counts`
- `results`
- `recommendation`

Optional top-level fields:

- `code_evidence`: present when `preflight --json --codegraph` is used.

Each result should include:

- `source`
- `kind`
- `path`
- `title`
- `summary`
- `metadata`

When the local capability registry is present, `preflight --refresh --json`
also reports `counts.capability_hits` and may include results with
`source=local_capability`.

## Capability Registry

`capabilities/registry.json` records the reusable local RePERS surface as
machine-readable data. `capabilities --action validate --json` validates the
registry, and `capabilities --action search --query "<query>" --json` ranks
entries for a capability query.

Required registry fields:

- `schema`: `repers.capability_registry.v1`
- `version`
- `entries`

Each entry must include:

- `id`
- `kind`
- `name`
- `summary`
- `tags`
- `commands`
- `paths`
- `verification`

Capability search emits:

- `schema`: `repers.capability_query.v1`
- `ok`
- `registry_path`
- `query`
- `count`
- `errors`
- `entries`

`code_evidence` currently uses the CodeGraph provider:

- `provider`: `codegraph`
- `enabled`
- `available`
- `ok`
- `bin`
- `repo`
- `index_exists`
- `actions`
- `status`
- `query`
- `context`
- `uncertainty`
- `errors`

If CodeGraph is not installed, the explicit binary path is invalid, or the
repository has no `.codegraph/codegraph.db`, `preflight --codegraph` still
exits normally and records the reason under `code_evidence.errors`. Use
`--codegraph-init` only when creating or updating the local `.codegraph/` index
is intended.

## Plan Proposal

`plan.proposed.json` and `plan.proposed.md` are written by
`plan --from-research`. A proposal is a reviewable draft; it does not overwrite
the canonical `plan.md`.

Required top-level fields:

- `schema`: `repers.plan_proposal.v1`
- `task`
- `task_dir`
- `objective`
- `research_json`
- `research_query`
- `recommendation`
- `evidence_refs`
- `steps`

Each proposed step must include:

- `id`
- `title`
- `action`
- `target_files`
- `verification_command`
- `expected_outcome`
- `depends_on`
- `status`
- `mode`

## Plan

`plan.json` is written by `plan --task <task>` from the canonical `plan.md`.

Required top-level fields:

- `schema`: `repers.plan.v1`
- `task`
- `task_dir`
- `plan_md`
- `research_json`
- `research_recommendation`
- `steps`

Each executable step must include:

- `id`
- `title`
- `action`
- `target_files`
- `verification_command`
- `expected_outcome`
- `depends_on`
- `status`
- `mode`
- `artifact_contract`

## Step Result

`results/<step_id>.json` is written by `run --action local`.

Required fields:

- `schema`: `repers.step_result.v1`
- `step_id`
- `title`
- `status`: `completed` or `failed`
- `command`
- `returncode`
- `duration_seconds`
- `stdout_tail`
- `stderr_tail`
- `target_files`

For `run --backend worker-command`, step results also include:

- `worker_id`
- `prompt_path`

For `run --backend openai-agents`, step results also include:

- `worker_id`
- `prompt_path`
- `backend`: `openai-agents`

For `run --backend langgraph`, step results also include:

- `worker_id`
- `prompt_path`
- `backend`: `langgraph`

## Dispatch

`dispatch --task <task>` writes `dispatch/manifest.json` plus one Markdown
prompt per ready non-local worker step under `dispatch/workers/`.

Required manifest fields:

- `schema`: `repers.dispatch.v1`
- `task`
- `task_dir`
- `plan_json`
- `plan_md`
- `backend`
- `max_workers`
- `ready_count`
- `batch_count`
- `workers`
- `batches`

Each worker entry must include:

- `worker_id`
- `batch`
- `slot`
- `backend`
- `step_id`
- `title`
- `mode`
- `target_files`
- `depends_on`
- `verification_command`
- `prompt_path`

Worker prompts must include the task, ownership, forbidden actions,
dependencies, acceptance criteria, verification, and return format.

## Worker Command Backend

`run --backend worker-command` executes ready non-local steps through a command
template. The template can be passed with `--worker-command` or
`REPERS_WORKER_COMMAND`.

The worker process receives:

- `REPERS_WORKER_ID`
- `REPERS_STEP_ID`
- `REPERS_PROMPT_PATH`
- `REPERS_TASK_DIR`
- `REPERS_WORKSPACE_ROOT`

The command template may also use Python format placeholders:

- `{prompt_path}`
- `{worker_id}`
- `{step_id}`
- `{task_dir}`
- `{workspace_root}`

Each worker command writes a normal `repers.step_result.v1` result file, so
`review --update-status` can apply the result back to `plan.md`.

## Orchestration Fixture

`fixture --action prove --json` writes and executes a deterministic large-task
DAG fixture under `repers_tasks/<task>/`.

Required top-level fields:

- `schema`: `repers.orchestration_fixture.v1`
- `ok`
- `task`
- `created`
- `initial_dry_run`
- `dispatch`
- `worker_run`
- `join_dry_run`
- `local_run`
- `join`
- `review`

The fixture proves:

- three initially ready worker lanes
- conflict-safe batching, where two shared-target lanes are not in the same
  batch
- worker-command result files with worker metadata
- a local join step that validates dispatch and worker evidence
- review pass over the produced `repers.step_result.v1` files

## Receiver Fixture

`receiver-fixture --json` creates a package archive, installs it into a fresh
temporary Git repository, and proves the installed receiver command surface.

Required fields:

- `schema`: `repers.receiver_fixture.v1`
- `ok`
- `generated_at`
- `workspace_root`
- `install_root`
- `package`
- `steps`
- `checks`
- `errors`

The receiver checks include:

- `verify-install --json`
- `doctor --json`
- `bundle-status --json`
- `capabilities --action validate --json`
- `capabilities --action search --query "fixture worker-command parallel dag" --json`
- `fixture --action prove --task receiver-fixture --json`

## OpenAI Agents Backend

`run --backend openai-agents` executes ready non-local steps through the
optional OpenAI Agents SDK. The backend is available only when the `agents`
Python package can be imported.

Runtime settings:

- `REPERS_OPENAI_AGENT_MODEL`: optional model passed to `Agent`.
- `REPERS_OPENAI_AGENT_MAX_TURNS`: maximum turns for `Runner.run_sync`; default `8`.
- `REPERS_OPENAI_AGENT_TOOLS`: `none`, `readonly`, or `workspace`; default `readonly`.

The adapter creates one agent per RePERS worker prompt, calls
`Runner.run_sync`, stores `final_output` in `stdout_tail`, writes normal
`repers.step_result.v1` result files, and can update `plan.md` through the
same review/status path as other backends.

Tool modes:

- `none`: attach no function tools.
- `readonly`: attach `repers_list_files` and `repers_read_file`.
- `workspace`: also attach `repers_write_file` and `repers_run_command`.

Safety boundaries:

- all file paths must stay inside the workspace
- `.git` and `__pycache__` paths are blocked
- writes are allowed only to the worker step's `target_files`
- shell commands run in the workspace, have a bounded timeout, and reject a
  small set of destructive command patterns

## LangGraph Backend

`run --backend langgraph` executes ready non-local steps through the optional
LangGraph runtime. The backend is available only when the `langgraph` Python
package can be imported.

Runtime settings:

- `REPERS_LANGGRAPH_WORKER_COMMAND`: command template used by each graph worker.
- `REPERS_WORKER_COMMAND`: fallback command template when the LangGraph-specific
  setting is absent.
- `REPERS_LANGGRAPH_CHECKPOINT`: `none`, `memory`, or `sqlite`; default `none`.
- `REPERS_LANGGRAPH_THREAD_ID`: optional LangGraph checkpoint thread id. If
  checkpointing is enabled and this is absent, RePERS derives `repers-<task>`.
- `REPERS_LANGGRAPH_CHECKPOINT_PATH`: optional SQLite checkpoint file path. If
  `sqlite` checkpointing is enabled and this is absent, RePERS writes
  `langgraph-checkpoints.sqlite` under the task directory.

The adapter builds a `StateGraph` with one batch execution node, compiles it,
and invokes it once per conflict-safe RePERS batch. The graph state carries the
batch workers and their `repers.step_result.v1` outputs. LangGraph owns graph
orchestration; the worker command performs the actual implementation work and
receives the same environment variables as `worker-command`.

When `REPERS_LANGGRAPH_CHECKPOINT=memory`, the adapter compiles the graph with
LangGraph's in-memory checkpointer. When
`REPERS_LANGGRAPH_CHECKPOINT=sqlite`, the adapter imports
`langgraph.checkpoint.sqlite.SqliteSaver`, opens the configured checkpoint
database, and compiles the graph with that checkpointer. Both checkpoint modes
invoke the graph with `configurable.thread_id`. Run results include
`checkpoint_mode`, `thread_id`, and `checkpoint_path` for SQLite mode.

## Review

`review.json` is written by `review --task <task>`.

Required top-level fields:

- `schema`: `repers.review.v1`
- `task_dir`
- `results_dir`
- `result_count`
- `ok_count`
- `failed_count`
- `ok`
- `results`

When `review --update-status` is used, the artifact also includes
`status_update` with `updated`, `skipped`, and `error`.

## Install Hook

`install-hook --json` emits:

- `schema`: `repers.install_hook.v1`
- `ok`
- `workspace_root`
- `install_root`
- `hook_path`
- `gitignore_path`
- `hook_policy`: `warn` or `strict`

`warn` is the default. `strict` writes a hook that runs
`audit --strict-warnings`, making warnings fail the hook. The environment
variable `REPERS_AUDIT_STRICT_WARNINGS=1` also forces strict behavior for a
single hook run.

## Install Manifest

`install_repers.py --target <repo>` writes `.repers/manifest.json`.

Required fields:

- `schema`: `repers.install_manifest.v1`
- `version`
- `generated_at`
- `source_root`
- `target_root`
- `install_root`
- `source_git`
- `with_hook`
- `hook_policy`
- `hook_path`
- `gitignore_path`
- `file_count`
- `files`

Each file entry includes:

- `path`
- `size_bytes`
- `sha256`

## Install Verify

`verify-install --json` verifies the installed `.repers/manifest.json` against
the current installed bundle.

Required fields:

- `schema`: `repers.install_verify.v1`
- `ok`
- `install_root`
- `manifest_path`
- `manifest_schema`
- `manifest_version`
- `strict_extra`
- `file_count`
- `checked_count`
- `missing`
- `changed`
- `extra`
- `errors`

Missing files, changed file sizes, changed SHA-256 hashes, invalid manifest
entries, and unsupported manifest schemas make `ok` false. Extra files are
reported but allowed by default; pass `--strict-extra` to make unrecorded
non-runtime files fail verification.

## Package Manifest

`package --output <dir>` writes `repers-<version>.zip` and embeds
`repers-package-manifest.json` at the archive root.

Required package command fields:

- `schema`: `repers.package.v1`
- `ok`
- `archive_path`
- `archive_size_bytes`
- `archive_sha256`
- `manifest`

Required embedded manifest fields:

- `schema`: `repers.package_manifest.v1`
- `version`
- `generated_at`
- `source_root`
- `source_git_root`
- `archive_path`
- `archive_root`
- `source_git`
- `file_count`
- `files`

Package archives include the reusable install surface: `README.md`, `docs/`,
`hooks/`, `scripts/`, `templates/`, and `tests/`. Runtime state such as
`.repers/`, `.codegraph/`, `dist/`, bytecode caches, and `repers_tasks/` is
excluded.

## Doctor

`doctor --json` reports runtime readiness. `doctor --fix --json` adds a `fix`
object with actions and errors.

Important checks:

- `python`
- `git`
- `git_repo`
- `hook`
- `index`
- `lsp_guard`
- `backends`
- `paths`
- `ok`

## Shipping

`shipping --task <task>` writes `shipping.json`. `shipping.md` remains the
human delivery note.

Required fields:

- `schema`: `repers.shipping.v1`
- `task`
- `task_dir`
- `generated_at`
- `summary`
- `artifacts`
- `git`
- `doctor`
- `review`
- `dispatch`
- `package_archive`
- `installed_bundle`

`summary.ok` is false when required Markdown artifacts are missing, doctor is
not ok, review failed, or an explicitly checked installed bundle target is
missing `.repers/`. A dirty Git tree is recorded as a warning rather than a
hard error during active development.

When `--installed-target` is passed, `installed_bundle` also reports manifest
presence, schema, version, file count, hook policy, and manifest verification
status. A failed manifest verification makes `summary.ok` false.

## Release Gate

`release --task <task>` writes `release.json` after running review, doctor,
shipping, and audit gates.

Required fields:

- `schema`: `repers.release_gate.v1`
- `task`
- `task_dir`
- `generated_at`
- `strict_warnings`
- `update_status`
- `summary`
- `gates`
- `doctor`
- `review`
- `shipping`
- `audit`

`summary.ok` is false when review, doctor, shipping, or audit fails. Use
`--strict-warnings` to make audit warnings fail the release gate. Use
`--installed-target` to include installed bundle manifest evidence in the
shipping section. The top-level `gates.shipping` summary includes
`installed_manifest_verify_ok` when an installed target was checked.

## Release Evidence

`release-evidence --json` writes `dist/repers-release-evidence.json`.
Use `--package --verify-roundtrip` to regenerate the package and include
round-trip evidence in the same artifact.

Required top-level command fields:

- `release_evidence`
- `path`

Required `release_evidence` fields:

- `schema`: `repers.release_evidence.v1`
- `ok`
- `publish_ready`
- `generated_at`
- `workspace_root`
- `install_root`
- `missing_for_publish`
- `git`
- `governance`
- `capability_registry`
- `package`

`ok=true` means the evidence was generated and local package/governance/registry
checks passed. `publish_ready=true` additionally requires a Git HEAD, named
branch, clean working tree, configured remote, and package readiness.

## Publish Handoff

`publish-handoff --json` writes `dist/repers-publish-handoff.json` and
`dist/repers-publish-handoff.md`. It is intentionally non-destructive: it
generates remote, push, and draft PR commands without executing them.

Required top-level command fields:

- `publish_handoff`
- `path`
- `markdown_path`

Required `publish_handoff` fields:

- `schema`: `repers.publish_handoff.v1`
- `ok`
- `release_evidence_ok`
- `publish_ready`
- `generated_at`
- `workspace_root`
- `install_root`
- `output_dir`
- `release_evidence_path`
- `missing_for_publish`
- `remote`
- `pull_request`
- `git`
- `package`
- `actions`
- `safety`

`actions` is an ordered list of command records. Each record includes `id`,
`title`, `command`, `status`, and `reason`. `safety` must record that the
command does not mutate Git remotes, push branches, or open pull requests.
`ok=true` means the handoff artifact was generated. Use
`release_evidence_ok` and `publish_ready` to decide whether the repository is
ready to execute the generated commands.

## Remote Bootstrap

`remote-bootstrap --json` writes `dist/repers-remote-bootstrap.json` and
`dist/repers-remote-bootstrap.md`. By default it is non-destructive: it
generates remote setup and publication commands, then regenerates publish
handoff evidence. Pass `--apply --remote-url <url>` to run `git remote add`;
the command refuses to overwrite an existing named remote with a different URL.

Required top-level command fields:

- `remote_bootstrap`
- `path`
- `markdown_path`

Required `remote_bootstrap` fields:

- `schema`: `repers.remote_bootstrap.v1`
- `ok`
- `generated_at`
- `workspace_root`
- `install_root`
- `output_dir`
- `remote`
- `git`
- `applied`
- `publish_handoff`
- `actions`
- `safety`

`applied.requested=false` means no Git remote mutation was attempted. Safety
must record that the command does not push branches or open pull requests, and
that remote mutation requires `--apply`.

## Remote Bootstrap Fixture

`remote-bootstrap-fixture --json` writes
`dist/repers-remote-bootstrap-fixture.json`. It proves the `--apply` path
without using a hosted Git provider by creating a temporary target repository,
installing RePERS there, creating a local bare remote, running
`remote-bootstrap --apply`, and pushing to that bare remote.

Required top-level command fields:

- `remote_bootstrap_fixture`
- `path`

Required `remote_bootstrap_fixture` fields:

- `schema`: `repers.remote_bootstrap_apply_fixture.v1`
- `ok`
- `generated_at`
- `workspace_root`
- `install_root`
- `output_dir`
- `steps`
- `checks`
- `errors`

The fixture passes only when `remote_bootstrap_apply`, `remote_url`,
`local_push`, and `bare_remote_refs` checks succeed.

## Objective Audit

`objective-audit --json` writes `dist/repers-objective-audit.json`. Use
`--deep` to run package, receiver, publish handoff, remote bootstrap, remote
bootstrap fixture, and smoke checks before auditing.

Required top-level command fields:

- `objective_audit`
- `path`

Required `objective_audit` fields:

- `schema`: `repers.objective_audit.v1`
- `ok`
- `objective_complete`
- `generated_at`
- `workspace_root`
- `install_root`
- `output_dir`
- `objective`
- `deep`
- `requirements`
- `blocking_incomplete`
- `continuation`
- `continuation_markdown_path`
- `commands`

Each requirement includes `id`, `title`, `status`, `passed`,
`blocks_completion`, and `evidence`. `objective_complete=false` means at least
one blocking requirement is still unproven or incomplete.

`continuation` uses schema `repers.objective_continuation.v1` and turns the
audit into a resumable control artifact. It includes:

- `status`: `complete`, `local_work_available`, or `blocked_external`
- `blocking_incomplete`
- `requirement_status`
- `local_actions`
- `external_actions`
- `handoff_action_ids`
- `bootstrap_action_ids`

`local_actions` are commands another agent can run in the current repository.
`external_actions` name required external state, such as a hosted Git remote or
provider-authenticated pull request creation. `repers-continuation.md` renders
the same action plan for humans.

## Continuation Runner

`continue --json` regenerates the objective audit, reads
`repers.objective_continuation.v1`, and emits a resumable action report. It is a
dry-run by default. Pass `--apply` to execute only selected local continuation
actions whose status is `ready`; external actions are never executed by this
command. Use repeatable `--action-id <id>` to limit local action selection.

Required top-level fields:

- `schema`: `repers.continuation_run.v1`
- `ok`
- `generated_at`
- `workspace_root`
- `install_root`
- `output_dir`
- `mode`: `dry-run` or `apply`
- `audit_path`
- `objective_complete`
- `blocking_incomplete`
- `continuation_status`
- `selected_action_ids`
- `ready_action_ids`
- `deferred_action_ids`
- `external_action_ids`
- `local_actions`
- `external_actions`
- `executions`
- `errors`

`executions` is empty in dry-run mode. In apply mode, each execution includes
the action id, title, command result, return code, stdout/stderr tails, and
parsed JSON when available. `ok=false` means at least one executed local action
failed.

## State Report

`state --json` writes `dist/repers-state.json` and `dist/repers-state.md`. It
regenerates objective audit evidence and composes the current repository state
from objective, release, package, Git, test, capability, and continuation
records. Use `--deep` when the state report must include fresh package,
receiver, fixture, and smoke evidence.

Required top-level command fields:

- `state`
- `path`
- `markdown_path`

Required `state` fields:

- `schema`: `repers.state_report.v1`
- `ok`
- `generated_at`
- `workspace_root`
- `install_root`
- `output_dir`
- `audit_path`
- `deep`
- `status`
- `objective`
- `git`
- `package`
- `capabilities`
- `tests`
- `continuation`
- `next`
- `artifacts`

`status` mirrors objective completion or continuation status. `next` gives the
first ready local action and first external publication action, if present.
`artifacts` records the JSON and Markdown state paths plus the underlying audit,
continuation, and release evidence files.

## Verify All

`verify-all --json` writes `dist/repers-verify-all.json` and
`dist/repers-verify-all.md`. It runs local gates sequentially and gives each
artifact-writing gate its own temporary output directory. This is the preferred
single command for agents that need race-safe local proof before publication.

Required top-level command fields:

- `verify_all`
- `path`
- `markdown_path`

Required `verify_all` fields:

- `schema`: `repers.verify_all.v1`
- `ok`
- `generated_at`
- `workspace_root`
- `install_root`
- `output_dir`
- `temp_root`
- `status`
- `gates`
- `state`
- `next`
- `errors`

`ok=true` means every local gate passed and any remaining objective blocker is
external-only, currently `publication_ready`. `status=blocked_external` is a
successful local verification state when no hosted Git remote is configured.

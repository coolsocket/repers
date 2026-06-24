# Repository Metadata

Use this as the source of truth for the public GitHub settings that are not
fully represented by files.

## Description

```text
Local-first agent workflow harness: preflight, DAG planning, worker review,
hooks, and verifiable release packs for repository tasks.
```

## Topics

```text
agentic-ai
ai-agents
agent-workflows
automation
code-review
developer-tools
dag
hooks
preflight
release-engineering
repository-automation
workflow-engine
```

## Website

Use the repository URL until a docs site exists:

```text
https://github.com/coolsocket/repers
```

## Suggested GitHub Release Title

```text
RePERS v0.1.0 - local-first agent workflow harness
```

## Suggested Release Notes

````markdown
RePERS v0.1.0 packages the local-first agent workflow harness:

- preflight capability discovery with optional CodeGraph evidence;
- task DAG, dispatch, review, package, and release surfaces;
- deterministic orchestration fixture for supervisor/worker/join contracts;
- conservative pre-commit hook;
- receiver, clone, source-install, remote-bootstrap, and release-pack fixtures;
- transferable release pack with state, handoff, benchmark, and continuation artifacts.

Verify after download:

```powershell
python3 .repers/scripts\repers.py release-pack-verify --archive dist\repers-release-pack.zip --json
python3 .repers/scripts\repers.py verify-all --json
```
````

## CLI Fallback

If GitHub CLI is available, the metadata can be applied with:

```powershell
gh repo edit coolsocket/repers `
  --description "Local-first agent workflow harness: preflight, DAG planning, worker review, hooks, and verifiable release packs for repository tasks." `
  --homepage "https://github.com/coolsocket/repers" `
  --add-topic agentic-ai `
  --add-topic ai-agents `
  --add-topic agent-workflows `
  --add-topic automation `
  --add-topic code-review `
  --add-topic developer-tools `
  --add-topic dag `
  --add-topic hooks `
  --add-topic preflight `
  --add-topic release-engineering `
  --add-topic repository-automation `
  --add-topic workflow-engine
```

This repository currently keeps metadata in this file as a durable handoff when
the active automation surface cannot mutate repository settings directly.

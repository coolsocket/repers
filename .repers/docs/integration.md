# RePERS Codex & SelfEvo Tooling Integration Guide

RePERS is designed to seamlessly integrate with local Windows developer tools, the OpenAI Codex CLI ecosystem, and the `self-evolving` task-orchestration engine. This guide explains how to leverage these tools across the RePERS stages.

---

## 🔍 1. Research (R): Preflight Anti-Repetition Checking

Before writing a plan, we must check if a capability or design pattern has already been implemented in the active workspace or globally.

### Local Preflight Execution
If working inside a workspace supporting `selfevo` or `codops`, execute:
```bash
# Inside self-evolving repository
uv run codops preflight --query "<capability_name>"
```
Or for general files and global Codex skills, search both local and global paths:
* **Global Codex Skills Path**: `C:/Users/Administrator/.codex/skills/`
* **Local Workspace Skills**: `workspace-skills/`

### Integration into RePERS
Our helper script (`repers.py`) integrates a preflight query function that scans:
1. Installed modules and libraries in the Python environment.
2. Global Codex skills to match against standard practices.
3. Local workspace files for similar tokens.

---

## 📝 2. Plan (P): Parameterized and Repeatable Specifications

Rather than drafting long natural-language plans that require high cognitive effort to parse, planning documents should adopt a standardized, machine-readable layout.
* **Traceable Gates**: Every item in `plan.md` has a concrete `Verification Command` (e.g. `pytest` or a lint invocation) and an expected outcome.
* **Gated Sessions**: Always bind Codex to a workspace-gated `.codex_session` to avoid context leakage between different plans.

---

## 💻 3. Execute (E): Gated Execution with Codex

* **Automation Flags**: Always run Codex CLI with non-interactive flags (`--dangerously-bypass-approvals-and-sandbox` or `--full-auto`) during headless programmatic executions.
* **Atomic Patches**: Avoid rewriting complete files; prioritize targeted search-and-replace (`patch`) edit patterns to keep Git histories readable.

---

## 👁️ 4. Review (R): LSP Guard & Headless Verification

Verification must be backed by real tool results, not natural-language guarantees.

### Global LSP Guard
After editing JavaScript, TypeScript, or Python files, run the active workspace syntax guard:
```bash
C:\Users\Administrator\AppData\Local\CodexAgentTools\lsp-guard\agent-lsp-guard.cmd .
```
This runs `pyright` for Python files and `eslint` for JS/TS. Treat LSP Guard diagnostic failures as **blocking failures** that must be resolved before moving to the Shipping stage.

### Headless Visual Checks
For visual features:
1. Capture headless screenshots or open the test environment via local browsers on remote debugging port `9222`.
2. Inspect visually via `browser_vision`.

---

## 📦 5. Shipping (S): Rich HTML Workspace Dashboards

To make deliverables accessible and interactive (e.g., readable on a mobile device or a remote browser without terminal access):

### Local Workspace Rendering
Compile changed files and Markdown reports into high-fidelity, responsive HTML files:
```bash
python C:/Users/Administrator/AppData/Local/hermes/scripts/render_workspace.py
```
This generates `workspace_index.html` with syntax highlighting (Pygments).

### Remote Service Expose
Expose the report dashboard via a local server and secure localtunnel link:
```bash
python C:/Users/Administrator/AppData/Local/hermes/scripts/start_workspace_server.py
```
This launches a server on port `8000` and creates a localtunnel, providing a public URL for review.

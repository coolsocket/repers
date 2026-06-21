# RePERS Stage Specification

This document details the inputs, outputs, and Definition of Done (DoD) for each of the five stages of the RePERS framework.

---

## 🔍 1. Research (R)

### Input
* Raw user requirement or bug description.
* Active project files, dependencies, and execution logs.
* System capabilities, local libraries, and environment specs.

### Activities
* Run deep file-level searches and content reads (`search_files`, `read_file`).
* Verify dependencies (e.g., scan `package.json`, `requirements.txt`, `Cargo.toml`).
* Inspect pre-existing logic to avoid duplicating features (e.g., run preflight checks).
* Assess constraints (network permissions, OS-specific terminal differences on Windows).

### Output
* **Research Log / Summary**: A compilation of files inspected, dependencies verified, and API patterns identified.
* **Pitfalls List**: Known environment/language traps and security boundaries.

### Definition of Done (DoD)
1. No assumptions are made about existing file contents or paths.
2. All relevant files listed in the task description have been read.
3. Package/module dependency availability is verified.
4. Any potential duplicate logic in the workspace has been identified and referenced.

---

## 📝 2. Plan (P)

### Input
* Verified Research Summary.
* User preferences (e.g., "品类对齐第一", non-interactive flags, silent modes).

### Activities
* Decompose the task into discrete, logical, and incremental steps.
* Formulate testing and verification strategies for each step (TDD).
* Structure the output report design.

### Output
* **`plan.md` (saved in `.hermes/` or project root)**: A structured markdown document detailing steps, targeted files, and verification commands.

### Definition of Done (DoD)
1. Every step has a clear, measurable outcome.
2. Test cases or verification steps are defined *before* execution starts.
3. Core architectural rules (e.g. avoiding project-id gating) are explicitly listed as constraints.
4. The plan is committed to the workspace before code execution begins.

---

## 💻 3. Execute (E)

### Input
* Approved `plan.md`.
* Workspace files.

### Activities
* Code implementation and modification via `patch` or `write_file` (preferring targeted patch edits).
* Run tests continuously during development (RED-GREEN-REFACTOR loop).
* Resolve compilation and syntax errors.

### Output
* Modified or newly created code files.
* Local test results/outputs.

### Definition of Done (DoD)
1. All files mentioned in `plan.md` are created or updated.
2. Code builds/compiles without syntax or runtime errors.
3. Intermediate test cases pass successfully.
4. No temporary debug comments or commented-out code blocks are left in the final files.

---

## 👁️ 4. Review (R)

### Input
* Executed changes.
* Defined verification suite (tests, browser links, CLI scripts).

### Activities
* Run full regression test suites.
* Execute static analysis, linting, and quality checks.
* Run visual and keyboard-interactive tests in a headless or remote browser if UI changes were made.
* Run automated CLI code review tools (e.g., `codex review`).

### Output
* **Review Checklist / Audit Report**: Verification logs, test outputs, and optional screenshot references.

### Definition of Done (DoD)
1. All regression and feature-specific tests pass 100%.
2. Visual interface is verified via screenshots/browser analysis and matches specifications.
3. No security issues (hardcoded keys, injection vulnerabilities) are found.
4. Compliance with coding style guidelines is verified.

---

## 📦 5. Shipping (S)

### Input
* Verified changes.
* Review audit reports.

### Activities
* Clean up workspace (remove `.codex_session`, temporary prompts, debug logs).
* Compile documentation, user guides, or release notes.
* Create clean Git commits, format PR titles, or package assets.
* Write double-clickable desktop batch scripts (`.bat`) for easy local service launching.

### Output
* Clean Git commits or Pull Requests.
* Release documentation or updated README files.
* Double-clickable batch files or startup scripts.
* Final deployment report.

### Definition of Done (DoD)
1. Staged and unstaged workspaces are clean (all temporary files deleted or added to `.gitignore`).
2. Code is committed with a clear, descriptive message (or PR created).
3. Public documentation is updated to reflect the new feature or changes.
4. The user is provided with a concise, actionable summary of what was delivered and how to verify/run it.

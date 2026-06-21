# RePERS Agentic Workflows & Permutations

In the RePERS framework, AI agent behavior is modeled as a composition or sequence of the five states. Different task sizes, types, and complexities require different state sequences (permutations).

---

## 🔄 Core Workflows

```
┌────────────────────────────────────────────────────────┐
│           R-P-E-R-S (End-to-End Autonomous)           │
│  [Research] ──> [Plan] ──> [Execute] ──> [Review] ──> [Shipping]
└────────────────────────────────────────────────────────┘

┌───────────────────────────────────┐     ┌───────────────────────────────────┐
│     R-P (Scoping & Discovery)     │     │     E-R (Implementation Loop)     │
│       [Research] ──> [Plan]       │     │       [Execute] <──> [Review]     │
└───────────────────────────────────┘     └───────────────────────────────────┘

┌───────────────────────────────────┐     ┌───────────────────────────────────┐
│     R-E-R (Hotfix & Debugging)    │     │       R-S (Audit & Release)       │
│    [Research] ──> [Execute] ──> [Review]│     │       [Review] ──> [Shipping]     │
└───────────────────────────────────┘     └───────────────────────────────────┘
```

### 1. The Full Lifecycle: R-P-E-R-S
* **Best For**: Feature requests, new module development, or large refactoring tasks.
* **Flow**:
  1. **Research**: Scan the project, dependencies, and capability preflights.
  2. **Plan**: Formulate the blueprint file `plan.md` detailing the code changes.
  3. **Execute**: Develop code, run incremental tests.
  4. **Review**: Run full unit, regression, static analysis, and visual checks.
  5. **Shipping**: Commit changes, remove temporary files, update user docs, and build `.bat` launch scripts.

### Deterministic Orchestration Proof

Before using optional external agent backends, run:

```powershell
python .repers\scripts\repers.py fixture --action prove --json
```

The fixture creates a large-task DAG with three worker lanes and one join lane.
Two worker lanes intentionally target the same file, so the dispatch manifest
must place them in different batches while still running independent work in
parallel. The join step validates worker outputs and result contracts.

### 2. Scoping & Discovery: R-P
* **Best For**: Ambiguous specifications, architectural design tasks, or feasibility assessments.
* **Flow**:
  1. **Research**: Explore code patterns, APIs, and document potential architectural strategies.
  2. **Plan**: Draft alternative plans, weigh trade-offs, and lay out the execution steps.
  3. *Note*: This loop stops before writing production code to seek alignment and human-in-the-loop validation.

### 3. Implementation Loop: E-R
* **Best For**: Code modifications where the plan is already defined or trivial.
* **Flow**:
  1. **Execute**: Apply localized patches, create files.
  2. **Review**: Check syntax, run tests.
  3. **Loop**: If any test fails, transition back to *Execute* with the stack trace/error logs. Loop until all reviews pass.

### 4. Hotfix & Debugging: R-E-R
* **Best For**: Fixing urgent runtime errors, isolated crashes, or high-priority bugs.
* **Flow**:
  1. **Research**: Analyze error logs, find the root cause, verify surrounding context.
  2. **Execute**: Apply targeted, minimal patches immediately without a long-form plan.
  3. **Review**: Verify the fix via specific regression tests and linter outputs.

### 5. Audit & Release: R-S (Review -> Shipping)
* **Best For**: Reviewing pull requests, compliance audits, or preparing a codebase for deployment.
* **Flow**:
  1. **Review**: Check incoming code, run lints, perform security audits.
  2. **Shipping**: Generate changelogs, write deployment scripts, tag versions, and push to production.

---

## 🚦 Decision Matrix for State Transitions

| Task Complexity | Input State | Recommended Path | Execution Pattern |
| :--- | :--- | :--- | :--- |
| **High** (New Feature) | Raw prompt | **R-P-E-R-S** | Full workflow with plan validation and separate commits. |
| **Medium** (Refactor / Optimization) | Target modules | **R-P-E-R-S** | Prioritize regression testing in Review and audit in Shipping. |
| **Low** (Bug Fix / Hotfix) | Stack trace | **R-E-R** | Quick root cause analysis, immediate fix, regression check. |
| **Scoping Only** (Feasibility Study) | Idea draft | **R-P** | Delivery of plan.md and architectural diagrams. |
| **Release Prep** (Final Delivery) | Finished code | **R-S** | Clean, document, build batch files, push to master. |

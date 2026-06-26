# Cross-repo and cross-team handoff primitives

> Long-form companion to the [README](../README.md). For a Series-A startup
> with one repo, these primitives look like over-engineering. For a
> Fortune-500 with 12 services and 4 teams using 3 different AI vendors,
> they're the only thing that lets the audit + handoff actually work
> without "trust me, my agent did the right thing."

Most agent harnesses assume one repo + one agent + one team. Real
engineering work at scale doesn't. RePERS already ships the cross-repo
handoff primitives:

| Cross-repo flow | RePERS primitive | What it proves |
|---|---|---|
| Team A produces a release artifact; Team B's CI must consume + audit | `release-pack.zip` (transferable archive — install + readiness + evidence + bootstrap + benchmark + state) | A single signed zip moves between repos / orgs / clouds without losing audit context |
| Team B receives the pack; their AI/CI needs to verify it independently | `release-pack-verify --archive <pack> --json` | Receiver re-verifies checksums + manifest + embedded evidence **without trusting** the sender's vendor or JSON |
| A fresh repo wants to adopt the harness from a pack | `receiver-fixture --json` / `source-install-fixture --json` | Fresh `git init` + 1 command → working `.repers/` runtime; both contracts proven in CI |
| Two repos cooperate via a temporary bare remote (e.g., an air-gapped review) | `publish-clone-fixture --json` | Source pushes to bare remote → clone repo re-verifies → no network deps |
| A different LLM vendor (Codex / Gemini / your own) drives a lane | `dispatch.v1` manifest + `step_result.v1` artifact | Contract is JSON-in / JSON-out; the worker doesn't need to know which vendor the supervisor uses |

> **What this means for evaluation**: if you're evaluating RePERS for a
> small repo, evaluate the **router + naked-agent recommendation** — does
> it correctly tell you not to use the harness? If you're evaluating for a
> large repo or multi-team org, evaluate the **dispatch contract +
> release-pack handoff** — can you make repo A produce a pack repo B can
> re-verify without trusting repo A's vendor? Both are valid, and they're
> different evaluations.

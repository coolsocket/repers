# Where RePERS fits on the codebase maturity curve

> Long-form companion to the [README "When to use"](../README.md#-when-to-use--when-not-to-use) section.

The harness's overhead is **fixed**. The work it coordinates **compounds**.
So whether it earns its keep depends almost entirely on **what shape and
scale of work you're doing** — not what stack you're on. The honest answer
changes as a codebase grows from greenfield to enterprise to cross-org
ecosystem:

| You are… | Repo shape | Should you adopt RePERS? | What you actually need at this stage |
|---|---|---|---|
| **Day 0 — solo, prototype** (<1 k LOC, no tests) | One file or two; you're sketching | **No.** Naked agent in your IDE wins every time. | A chat window. Skip the harness. |
| **Early product** (1–3 devs, 1–10 k LOC, single domain) | A handful of files, light tests, one repo | **Almost always no.** Maybe pin `/repers-route` so the team has the option later. | CI + pre-commit lint. The router will keep telling you "skip". |
| **Growing product** (5–10 devs, 50 k LOC, 2–3 domains: api / web / worker) | Multi-file PRs are now common. Merge conflicts start. People step on each other. | **Selectively.** Adopt for the *big* changes — migrations, deprecation sweeps, refactors of a god-class. Skip for everyday PRs. | Branch protection + structured code review. The router routes most tasks to `R-E-R` and the occasional one to `R-P-E-R`. |
| **Scale-up** (20+ engineers, 200 k+ LOC monorepo, multi-team) | Parallel feature work daily. **Multiple AI agents** are helping multiple engineers. Sometimes you set off two Codex sessions on the same area at once and they clobber. | **Yes — this is the sweet spot.** The router will recommend `R-P-E-R` or `R-P-E-R-S` for most non-trivial tasks. | A contract that **prevents N agents (yours and your teammates') from clobbering each other's lanes.** ← that's what the `target_files` isolation + dispatch contract is. |
| **Big company / regulated** (100+ engineers, multi-service, audit trails required) | Cross-cutting work (security patches, compliance migrations) needs evidence chains. Different teams pick different agents (Claude / Codex / Gemini / in-house fine-tunes). | **Yes — as the lingua franca.** Adopt it across teams. JSON evidence is auditable; release-pack-verify lets a downstream team re-verify another team's claim without trusting their chat log. | A standard contract across agent fleets + a portable audit trail. |
| **Cross-org / OSS ecosystem** (multi-repo dependencies, vendor diversity) | Agent in repo A produces something repo B's CI or maintainer has to consume / verify. You don't trust repo A's vendor or their evidence. | **Yes — for the handoff.** `repers-release-pack.zip` is the transfer protocol; the receiving repo extracts it and **re-verifies independently** without trusting either the sender's vendor or their JSON. | A contract that survives vendor + organizational + trust boundaries. |

**Pattern**: at the small end the overhead dominates; at the large end the
coordination *is* the work, and the absence of a contract is what causes
the pain. RePERS feels cheaper as the codebase gets bigger. The router
exists so a tool that genuinely earns its keep at one end doesn't get
force-fitted onto the other.

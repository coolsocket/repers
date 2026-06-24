# How agent harnesses get evaluated — methodology research

> Playground note: research artifact. Findings from real sources; if any
> methodology is good enough to adopt, distill into `docs/` and tooling.
> Methodology: WebFetch on actual blog/leaderboard/paper URLs. Inline
> quotes attribute the source.

---

## TL;DR — what others measure

| Source | Headline metric | How harness is isolated | What's missing for RePERS |
|---|---|---|---|
| **SWE-bench** | `% resolved` (tests pass after patch) | Leaderboard is **model + scaffold combo**, not isolated | No multi-agent / no parallel / no cross-repo |
| **Aider polyglot** | `% correct` + `$ cost` + `edit format conformance` + `s/case` | Same — combo eval, but architect mode separates planner + editor models | Single-file tasks; no parallelism |
| **METR** | `time horizon` — task length where model is 50% reliable | Doesn't isolate; calls everything "frontier model agents" | No harness-specific eval, no router/honesty metric |
| **Anthropic "Building Effective Agents"** | Qualitative — "complexity only when it demonstrably improves outcomes" | Taxonomy of patterns; no formal metric | Says "start simple, add agentic only when simpler fails" — **same philosophy as RePERS router** |

**Key takeaway**: nobody isolates harness from model. The de-facto unit-of-evaluation is **`(model × harness × benchmark)` triple**. RePERS evaluation should follow this norm — pair RePERS with a fixed model, run on a fixed benchmark, compare against baseline.

---

## What each source actually measures (with quotes)

### 1. SWE-bench / SWE-bench Verified (Princeton)

What the benchmark contains:
> "2,294 software engineering problems drawn from real GitHub issues and corresponding pull requests across 12 popular Python repositories"

How a submission gets scored: each instance ships a `test_patch` (failing tests) + `gold patch` (what fix should look like) + `FAIL_TO_PASS` (tests that should flip from fail to pass) + `PASS_TO_PASS` (tests that should stay passing). A submission's patch is applied, the test patch is applied, then the test sets run. Resolved = all FAIL_TO_PASS now pass AND all PASS_TO_PASS still pass. **Eval is dockerized for reproducibility.**

Leaderboard composition — confirmed via filter UI:
- `Agent` selector: `mini-SWE-agent v2`, `mini-SWE-agent v0-v2`, `All OSS agents`, `All agents`
- `Models` selector: `All`, `Open source only`, `Proprietary only`
- → **Leaderboard entries are (agent, model) pairs.** Not isolated.

Variants:
- **SWE-bench Full** — 2,294 instances
- **SWE-bench Lite** — ~300 instances, easier subset
- **SWE-bench Verified** — 500 instances, "engineer-confirmed solvable problems" (Aug 2024)
- **SWE-bench Multilingual** — non-Python
- **SWE-bench Multimodal** — with screenshots

### 2. Aider's polyglot leaderboard

> "Aider's polyglot benchmark tests LLMs on 225 challenging Exercism coding exercises across C++, Go, Java, JavaScript, Python, and Rust."

Per-row metrics they report:
- `Percent correct` (headline)
- `Cost` (total dollars)
- `Command` (exact aider invocation — so harness configuration is visible)
- `Edit Format` (diff / diff-fenced / whole / architect)
- `Correct edit format %` (proxy for "did the model conform to harness's expected output shape")
- `Num malformed responses`
- `Prompt tokens` + `Completion tokens` + `Exhausted context windows`
- `Seconds per case`

Notable: **Architect mode** entries pair a **planner model** with a separate **Editor model** (e.g., "o3 (high) + gpt-4.1", "DeepSeek R1 + claude-3-5-sonnet-20241022"). This is the closest the public ecosystem gets to RePERS's stage separation.

### 3. METR — "Measuring AI Ability to Complete Long Tasks"

The "time horizon" metric (verbatim):
> "the length (for humans) of tasks that the model can successfully complete with x% probability"

Method: fit a logistic curve to "model success probability using human task length" → read off where it crosses 50%. Tasks drawn from "a diverse set of multi-step software and reasoning tasks" plus HCAST and RE-Bench, with replication on SWE-Bench Verified.

Empirical cliff:
> "current models have almost 100% success rate on tasks taking humans less than 4 minutes, but succeed <10% of the time on tasks taking more than around 4 hours."

Doesn't isolate harness. Doesn't address parallelism. **But** the time-horizon framing gives RePERS a natural niche: **the harness's job is to extend the time horizon by decomposing long tasks into shorter, parallel-able lanes**. RePERS's value-prop should be measured as "how much longer-horizon task can model+RePERS handle vs model alone?"

### 4. Anthropic — "Building Effective Agents" (canonical taxonomy)

Patterns described (verbatim summary):

- **Augmented LLM** — base unit (retrieval + tools + memory)
- **Prompt chaining** — sequential subtasks with optional gates
- **Routing** — classify input, dispatch to specialized follow-up
- **Parallelization** — *sectioning* (independent subtasks) or *voting* (same task N times)
- **Orchestrator-workers** — central LLM "dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes their results"
- **Evaluator-optimizer** — generator + critic loop
- **Agents** — LLM in a loop with tools + env feedback

Quoted alignment with RePERS philosophy:
> "complexity should only be added when it demonstrably improves outcomes"
> "Start with simple prompts, optimize them with comprehensive evaluation, and add multi-step agentic systems only when simpler solutions fall short"

This is **verbatim the router's philosophy**. RePERS's `route → "skip"` operationalizes this Anthropic principle.

Eval recommendation from the article (light, qualitative):
> "extensive testing in sandboxed environments, along with the appropriate guardrails"

For coding specifically: lean on automated tests (SWE-bench Verified) plus human review.

**The article does NOT address multi-agent collision handling or cross-repo handoff.** This is the gap RePERS occupies.

---

## How this maps onto RePERS's stages

| RePERS stage | Anthropic pattern name | Notes |
|---|---|---|
| `route` (router) | **Routing** | Maps task → permutation enum. RePERS adds the *skip* option, which Anthropic implicitly endorses but doesn't formalize. |
| `preflight` | (none directly — closest is retrieval) | Registry as shared memory across agents — Anthropic doesn't have a name for this. |
| `plan` | **Prompt chaining** (deferred — the plan defines the chain) | Plan.md = the chain as an artifact. |
| `dispatch` | **Parallelization** (sectioning) + **Orchestrator-workers** | RePERS's `target_files` isolation is what makes the sectioning safe — Anthropic doesn't address this. |
| `review` | **Evaluator-optimizer** | Schema-validator is a deterministic evaluator. |
| `shipping` / `release-pack` | (none — Anthropic stops at single-session agents) | Cross-trust-boundary handoff is the novel layer. |

**Useful framing**: RePERS is "Anthropic's patterns wired into a fixed workflow + a router that picks which patterns fire + the cross-session/cross-repo handoff layer Anthropic doesn't cover."

---

## What RePERS should measure (concrete proposal)

### Adopt the existing norm: `(model × harness × benchmark)` triple

Pair RePERS with a fixed model (Claude Sonnet 4.5 is the natural default; switchable via `REPERS_PLUGIN_DISPATCH=<vendor>`). Run on existing benchmarks. Compare:

- **Baseline 1**: model alone (zero harness) — closest possible naked agent
- **Baseline 2**: model + aider (industry-standard harness)
- **Baseline 3**: model + SWE-agent (or mini-SWE-agent — the canonical SWE-bench scaffold)
- **Treatment**: model + RePERS (router-on)
- **Ablation**: model + RePERS (router forced to R-P-E-R-S — to isolate router contribution)

Headline metrics (match existing leaderboards so numbers are comparable):

| Metric | Source | Why |
|---|---|---|
| `% resolved` | SWE-bench | Industry standard. Required for credibility. |
| `$ cost / instance` | Aider | Real-world adoption gate. |
| `s/instance` wall-clock | Aider + METR cliff | Where RePERS's parallel claim gets tested. |
| `n_llm_calls` | (custom) | Distinguish "1 powerful call" from "many cheap calls" |

### RePERS-unique metrics (these are the actual moat)

If RePERS just matches SWE-bench numbers, we lose on every dimension to bigger harnesses. The unique value is in these:

| Metric | What it measures | Why it's unique |
|---|---|---|
| `router_correctness` | Of N tasks, what fraction did the router route correctly? Ground truth: human label or post-hoc — was the recommended permutation actually optimal? | Nobody else has a router-with-skip; we need to demonstrate it works |
| `router_skip_rate` | Of N tasks, how many did the router route to `skip` / `naked_loop`? | The *honesty* metric. A harness that recommends itself 100% of the time is suspect. |
| `parallel_speedup` | Wall-clock(R-P-E-R-S) / Wall-clock(R-E-R) on same task | Tests the dispatch claim |
| `collision_incidents` | Number of file-level write conflicts across parallel workers | RePERS should be 0 by contract; competitors should be >0 |
| `handoff_reverify_success` | After repo A produces release-pack, repo B's `release-pack-verify` returns ok? | The cross-trust-boundary claim |
| `time_horizon_extension` | METR-style: what's the max human-time task model+RePERS handles at 50% vs model alone? | The "we extend agent autonomy" claim |

### Benchmark suites to use

| Benchmark | Why | Caveat |
|---|---|---|
| **SWE-bench Verified** (500 instances) | Industry standard; matches what everyone else reports | Single-repo, single-file mostly → router will mostly route to `R-E-R`. Tests that the router doesn't over-engineer. |
| **SWE-bench Multimodal** | Tests UI bugs requiring screenshots | RePERS doesn't directly help here; included for completeness |
| **METR HCAST** | Long-horizon tasks (4hr+) | This is where RePERS *should* shine — if it doesn't extend the horizon, our story falls apart |
| **Custom multi-file refactor suite** | We define it; targets RePERS's claimed niche (cross-domain, multi-agent) | Risk: we mark our own homework. Mitigation: publish suite + reference impl, invite competitors |
| **Cross-repo handoff scenario** | Custom: agent A in repo A → release-pack → agent B in repo B re-verifies | Unique to RePERS; no peer comparison exists |

---

## Recommended next concrete actions

1. **Stand up SWE-bench Verified locally** (3-5 instances first, full 500 later). Get **baseline numbers** for `model alone` and `model + aider`.
2. **Add a Sonnet-driven plugin to `.repers/plugins/dispatch/`** — `dispatch/anthropic-sonnet.py` — so RePERS+Sonnet is a runnable triple. (This is also the **agent-fixture** v0.3 item.)
3. **Run RePERS+Sonnet on the same 3-5 SWE-bench Verified instances** as the baselines. Collect `% resolved`, `cost`, `wall-clock`, plus the RePERS-unique metrics (router decision, collision incidents).
4. **Publish results in `docs/benchmarks.md`** with full reproducibility (versions, seeds, prompts, commands). Even if numbers look bad on `% resolved`, the unique metrics tell our story.
5. **Don't fake**: if baseline harness wins on most SWE-bench instances (likely — they're optimized for single-repo single-file fixes), report it honestly and lean into the cross-trust-boundary story instead.

---

## What this implies for positioning

The Anthropic framing **lands directly in our hand**:

> "Start simple, add multi-step agentic systems only when simpler solutions fall short" → **this IS RePERS's router.**

We can position RePERS as **"the harness that operationalizes Anthropic's 'simple first' principle"** — and back it with the empirical `router_skip_rate` metric. No other harness in the ecosystem makes this commitment.

The cross-trust-boundary story (release-pack-verify) **has no peer benchmark today**. We can either:
- (a) define one ourselves (risk: marking our own homework)
- (b) wait for the industry to need it (risk: someone else gets to define the standard first)

I'd lean (a) — define a small `cross-repo-handoff-bench` suite (e.g., "team A ships, team B re-verifies, audit log holds across vendor swap"), publish methodology, invite others to attempt it.

---

## Open questions

1. Should we **build the dispatch/anthropic-sonnet plugin first** (so RePERS+Sonnet is runnable for benchmarking)? That's the **agent-fixture** v0.3 item anyway.
2. Should we **commit to 3-5 SWE-bench Verified instances this week** for a real number? Even a "RePERS loses on simple tasks, wins router-skip metric" result is more credible than rhetoric.
3. **`router_skip_rate` as a marketing claim** — is this defensible? E.g., "RePERS skipped its own harness on 73% of SWE-bench Verified tasks because the router correctly routed them to naked_loop." That's a *unique* number nobody else can quote.

---

## Sources used

- https://www.swebench.com/ (landing) — UI confirmed agent+model leaderboard composition
- https://www.swebench.com/SWE-bench/ (docs landing)
- https://aider.chat/docs/leaderboards/ — polyglot methodology + architect-mode evidence
- https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/ — time-horizon metric, 4min/4hr cliff
- https://www.anthropic.com/engineering/building-effective-agents — patterns taxonomy
- https://arxiv.org/abs/2310.06770 — SWE-bench paper abstract (full PDF would have more)
- (Sources accessed 2026-06-24)

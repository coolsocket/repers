---
name: repers-route
description: Decide whether (and which slice of) the RePERS R-P-E-R-S pipeline fits a task before running anything. Use BEFORE invoking /repers-bug-hunt or any other R-P-E-R-S workflow — the router will tell you to skip the harness entirely for tasks too small to earn its overhead. Returns one of skip / R-only / R-S / R-E-R / R-P-E-R / R-P-E-R-S plus a single-line reason and a recommendation.
---

# repers-route

> **Layer**: 🧭 **Router** (gate before R) — picks WHICH of R/P/E/R/S layers should run for this specific task. The only skill an agent should call **unconditionally** on first contact.

The router is the **first thing** to call when a user asks for "help me fix X"
or "I want to work on Y". For tasks at the small end (single-file bug, test
pins the answer), RePERS's coordination overhead costs more than it saves —
the router exists so the harness is invoked only when its overhead actually
pays off.

## When to invoke

- The user gives you a task description ("fix the L060 description bug",
  "migrate pkg_resources callers", "add OpenTelemetry to the API tier").
- BEFORE running any of: `/repers-init`, `/repers-bug-hunt`,
  `/repers-release-pack`.
- Whenever you're tempted to "just run the full pipeline" without first asking
  whether it fits.

## Procedure

1. Get a short task description from the user (or extract from the request).
   If you can estimate how many files the task will touch, pass it via
   `--est-files`; otherwise let the router auto-detect repo signals.

2. Run the router:

   ```bash
   python3 .repers/scripts/repers.py route \
     --task "<short description>" \
     --est-files <N>  # optional
     --json
   ```

3. Read the `permutation` field and follow the `recommendation`:

   | `permutation` | What to do next |
   |---|---|
   | `skip`       | **Do not invoke RePERS skills.** Use your IDE + agent loop. Tell the user the router routed away from the harness and why. |
   | `R-only`     | Run `preflight --query "..." --refresh --json`, write a research note, stop. Decide BEFORE building. |
   | `R-S`        | Preflight, then `shipping --task <t> --json`. Skip plan / execute / dispatch. |
   | `R-E-R`      | Naked loop: read, edit, verify with focused tests. The harness ceremony costs more than it saves. |
   | `R-P-E-R`    | Run `init` → `preflight` → fill `plan.md` → `plan` → `dispatch` → workers → `review`. Skip heavyweight `shipping` / handoff. |
   | `R-P-E-R-S`  | Full pipeline: `init` → `preflight` → fill `plan.md` → `plan` → `dispatch` → workers → `review` → `run --action local` for any local verifies → `shipping`. |

4. Surface the router's `reasons` array to the user so they understand why a
   particular permutation was picked — never silently route them through more
   ceremony than they asked for.

## When to override the router

- The router is keyword + signal heuristic only — no LLM intent classification.
  When you (the calling agent) have stronger evidence the user is working at
  the cross-cutting / multi-domain end (e.g., they said "small" but the
  preflight returns 12 matching past PRs), tell them, and re-run with
  `--est-files N` reflecting your better estimate.
- The router defaults to the SMALLER permutation when in doubt — the cost
  of under-using the harness is bounded (the user just spends slightly more
  time in their IDE), while the cost of over-using it is real wasted time
  on ceremony that didn't fit the work.

## Done criteria

- A router decision has been produced via `route --json`.
- The user has been told the recommended permutation AND the reason in one
  short sentence (not just the slash command name).
- Subsequent skill invocations align with the recommendation, or you have
  explicitly explained why you're overriding.

## Notes

The router is deterministic, fast (<100 ms), and offline. It never calls an
LLM. A future v0.3 may overlay LLM-based intent classification, but the
deterministic decision tree remains the floor.

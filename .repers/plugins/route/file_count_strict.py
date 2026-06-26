"""file_count_strict — pure file-count routing, no keyword heuristics.

Alternative router for teams that want **deterministic, predictable** routing
based purely on the size of the task. The default plugin scores keywords +
repo signals + file count; this one ignores everything except `est_files`.

Useful in:
  - CI gates that want "harness fires when N files affected, never for less,
    always for more"
  - Teams whose work pattern doesn't match the default's keyword vocabulary
  - Audit contexts where "why did the router pick this?" must be answerable
    with a single integer threshold instead of a scoring function

Thresholds (env-tunable):
  REPERS_FILE_HOTFIX_CAP=3       est_files <= this → R-E-R     (hotfix)
  REPERS_FILE_MULTIFILE_CAP=10   est_files <= this → R-P-E-R   (multi-file)
                                 est_files >  this → R-P-E-R-S (full)
  est_files in {None, 0, 1}      → skip (naked_loop)

Select via:
  REPERS_PLUGIN_ROUTE=file_count_strict repers route \\
    --task "..." --est-files 5 --json

Conforms to repers.router.v1.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

NAME = "file_count_strict"
SCHEMA_VERSION = "repers.router.v1"

HOTFIX_CAP = int(os.environ.get("REPERS_FILE_HOTFIX_CAP", "3"))
MULTIFILE_CAP = int(os.environ.get("REPERS_FILE_MULTIFILE_CAP", "10"))


def _decision(est_files):
    if est_files is None or est_files <= 1:
        return (
            "skip",
            [],
            "naked_loop",
            "<=1 file (or unknown) — harness adds overhead with nothing to coordinate",
            "~1.0x (no harness)",
            None,
            None,
            "Use your own Edit/Read/Bash tools.",
        )
    if est_files <= HOTFIX_CAP:
        return (
            "R-E-R",
            ["R", "E", "R"],
            "invoke_bug_hunt_no_ship",
            f"{est_files} files — hotfix shape (preflight + edit + review, no parallel dispatch)",
            "~0.7-0.9x (modest, may add ceremony)",
            "repers preflight --query '...' --json  # then edit  # then review",
            "/repers-bug-hunt",
            "Invoke /repers-bug-hunt with the small-task path (no parallel dispatch).",
        )
    if est_files <= MULTIFILE_CAP:
        return (
            "R-P-E-R",
            ["R", "P", "E", "R"],
            "invoke_bug_hunt_no_ship",
            f"{est_files} files — multi-file (plan + parallel dispatch + review, skip shipping)",
            "~1.5-2.5x (parallelism helps)",
            "repers init --task <name>  # then preflight + plan + dispatch + review",
            "/repers-bug-hunt",
            "Invoke /repers-bug-hunt full plan→dispatch→review (no shipping).",
        )
    return (
        "R-P-E-R-S",
        ["R", "P", "E", "R", "S"],
        "invoke_bug_hunt_full",
        f"{est_files} files — full pipeline (every layer pays at this scale)",
        "~2.0-3.0x (parallel + handoff + evidence chain all pay)",
        "repers init --task <name>  # then full pipeline through shipping",
        "/repers-bug-hunt",
        "Full pipeline. Invoke /repers-bug-hunt end-to-end including shipping.",
    )


def route(task: str, repo_root, est_files=None, **kwargs) -> dict[str, Any]:
    perm, stages, action, summary, speedup, command, skill, next_summary = _decision(est_files)
    return {
        "schema": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": True,
        "task": task,
        "repo_root": str(repo_root),
        "signals": {
            "repo_file_count": None,
            "domain_count": None,
            "estimated_task_files": est_files,
        },
        "permutation": perm,
        "stages": stages,
        "permutation_summary": summary,
        "estimated_speedup_vs_naked": speedup,
        "reasons": [
            f"file_count_strict: est_files={est_files}, hotfix_cap={HOTFIX_CAP}, multifile_cap={MULTIFILE_CAP}",
        ],
        "recommendation": summary,
        "next_step": {
            "action": action,
            "command": command,
            "skill": skill,
            "summary": next_summary,
        },
        "errors": [],
        "_plugin": NAME,
    }


def format_human(payload: dict[str, Any]) -> str:
    return (
        f"[file_count_strict] {payload['permutation']} — {payload['recommendation']}\n"
        f"  next_step.action={payload['next_step']['action']}\n"
        f"  reason: {payload['reasons'][0]}"
    )

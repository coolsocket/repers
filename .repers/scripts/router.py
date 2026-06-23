"""RePERS task router.

Given a task description and repository signals, recommend which R-P-E-R-S
permutation to run (R-E-R hotfix · R-P-E-R multi-file · R-P-E-R-S full ·
R-S docs-only · R-only spike) and explain why.

The router is intentionally a keyword + lightweight-signal decision tree —
no LLM call, no extra dependencies. It is wrong on purpose in the right
direction: when in doubt, recommend the smaller permutation so the user
doesn't waste a 5.8× wall-clock overhead on a bug that didn't need it
(see docs/e2e-walkthrough.md + the sqlfluff benchmark in FAQ).

A skill or wrapper that has an LLM available is encouraged to overlay
intent classification on top — but the deterministic router should remain
the fallback so the CLI works offline and without any AI provider configured.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROUTER_SCHEMA = "repers.router.v1"

# Permutation catalog. Order is loosely "smallest to fullest".
PERMUTATIONS = {
    "skip": {
        "stages": [],
        "summary": "Skip the harness entirely. Just edit + test in your IDE.",
        "estimated_speedup_vs_naked": "0.2x (harness is overhead here)",
    },
    "R-only": {
        "stages": ["R"],
        "summary": "Write a research note, then stop. Decide before building.",
        "estimated_speedup_vs_naked": "n/a (different mode — preserves context, no execution)",
    },
    "R-S": {
        "stages": ["R", "S"],
        "summary": "Docs/config-only change — no execute, just review and ship.",
        "estimated_speedup_vs_naked": "~1.0x (lightweight, mostly the same)",
    },
    "R-E-R": {
        "stages": ["R", "E", "R"],
        "summary": "Hotfix shape — single-file or small patch where the failing test pins the answer.",
        "estimated_speedup_vs_naked": "~0.5-0.8x (harness adds modest ceremony)",
    },
    "R-P-E-R": {
        "stages": ["R", "P", "E", "R"],
        "summary": "Multi-file in one domain — plan + parallel dispatch wins; light ship.",
        "estimated_speedup_vs_naked": "~1.5-2.0x (parallel lanes carry the speedup)",
    },
    "R-P-E-R-S": {
        "stages": ["R", "P", "E", "R", "S"],
        "summary": "Full pipeline — multi-domain, multi-day, multi-agent work. The sweet spot.",
        "estimated_speedup_vs_naked": "~2.0-3.0x (parallel + handoff + evidence chain all pay)",
    },
}


# Keyword sets the heuristic looks for.
DOCS_KEYWORDS = (
    "docs",
    "readme",
    "changelog",
    "comment",
    "docstring",
    "typo",
    "wording",
)
SPIKE_KEYWORDS = (
    "spike",
    "explore",
    "investigate",
    "research only",
    "scope out",
    "decide whether",
)
CROSS_CUTTING_KEYWORDS = (
    "migrate",
    "migration",
    "deprecate",
    "deprecation",
    "rollout",
    "sweep",
    "audit",
    "rename across",
    "refactor across",
    "instrument",
    "standardize",
    "upgrade",
    "replace all",
)
ONE_LINER_KEYWORDS = (
    "one-line",
    "one line",
    "single line",
    "trivial",
    "small fix",
    "tiny",
    "typo fix",
)
FEATURE_KEYWORDS = (
    "implement",
    "add feature",
    "new feature",
    "build",
    "introduce",
)


def _git_ls_files_count(repo_root: Path) -> int | None:
    """Cheap repo-size signal. Returns None when not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return sum(1 for line in result.stdout.splitlines() if line.strip())


def _count_top_level_code_dirs(repo_root: Path) -> int:
    """Rough domain-count signal: count top-level dirs that look like code."""
    candidates = {
        "src",
        "lib",
        "app",
        "apps",
        "services",
        "packages",
        "cmd",
        "internal",
        "pkg",
        "components",
        "modules",
    }
    count = 0
    try:
        for entry in os.scandir(repo_root):
            if not entry.is_dir():
                continue
            name = entry.name
            if name.startswith("."):
                continue
            if name in candidates:
                # Treat as domain root; count its subdirs if any.
                subdirs = [
                    sub
                    for sub in os.scandir(entry.path)
                    if sub.is_dir() and not sub.name.startswith(("_", "."))
                ]
                # services/api, services/worker → 2 domains
                count += max(1, len(subdirs)) if subdirs else 1
            elif _looks_like_a_module(entry.path):
                count += 1
    except FileNotFoundError:
        return 0
    return count


def _looks_like_a_module(path: str) -> bool:
    """Top-level dir that itself ships code (__init__.py, package.json, etc.)."""
    markers = ("__init__.py", "package.json", "Cargo.toml", "go.mod", "pyproject.toml")
    try:
        for marker in markers:
            if os.path.exists(os.path.join(path, marker)):
                return True
    except OSError:
        pass
    return False


def _contains_any(text: str, keywords: tuple) -> str | None:
    """Return the FIRST keyword in `keywords` found in `text` (lowercased), or None."""
    low = text.lower()
    for kw in keywords:
        if kw in low:
            return kw
    return None


def _classify(task: str, est_files: int | None, domain_count: int) -> tuple[str, list[str]]:
    """Pure decision tree. Returns (permutation_id, reasons[])."""
    reasons: list[str] = []

    docs_hit = _contains_any(task, DOCS_KEYWORDS)
    spike_hit = _contains_any(task, SPIKE_KEYWORDS)
    cross_hit = _contains_any(task, CROSS_CUTTING_KEYWORDS)
    oneliner_hit = _contains_any(task, ONE_LINER_KEYWORDS)
    feature_hit = _contains_any(task, FEATURE_KEYWORDS)

    if spike_hit:
        reasons.append(f"task description contains spike keyword '{spike_hit}'")
        return "R-only", reasons

    if docs_hit and not feature_hit and not cross_hit:
        reasons.append(f"task description contains docs keyword '{docs_hit}'")
        return "R-S", reasons

    if cross_hit:
        reasons.append(f"cross-cutting keyword '{cross_hit}' — typically multi-file across domains")
        return "R-P-E-R-S", reasons

    if est_files is not None and est_files >= 3:
        if domain_count >= 2 or feature_hit:
            reason_parts = [f"estimated {est_files} files"]
            if domain_count >= 2:
                reason_parts.append(f"{domain_count} code domains detected")
            if feature_hit:
                reason_parts.append(f"feature keyword '{feature_hit}'")
            reasons.append("multi-file + multi-domain shape: " + ", ".join(reason_parts))
            return "R-P-E-R-S", reasons
        reasons.append(f"estimated {est_files} files in a single domain — plan + parallel dispatch pays")
        return "R-P-E-R", reasons

    if oneliner_hit:
        reasons.append(f"task description contains one-liner keyword '{oneliner_hit}'")
        return "skip", reasons

    if est_files is not None and est_files <= 1:
        reasons.append(f"estimated {est_files} file(s) — naked agent is faster")
        return "R-E-R", reasons

    # Default: when we don't have enough signal to justify the harness's
    # overhead, route to R-E-R (the small permutation). The user can always
    # override.
    reasons.append("no positive signal for multi-lane work; defaulting to small permutation")
    return "R-E-R", reasons


def route_task(
    task: str,
    repo_root: Path | str,
    est_files: int | None = None,
    repo_file_count: int | None = None,
    domain_count: int | None = None,
) -> dict:
    """Build the router decision payload for a task description."""
    repo_root_path = Path(repo_root).resolve()

    # Auto-detect signals when caller didn't override.
    if repo_file_count is None:
        repo_file_count = _git_ls_files_count(repo_root_path)
    if domain_count is None:
        domain_count = _count_top_level_code_dirs(repo_root_path)

    permutation_id, reasons = _classify(task, est_files, domain_count)
    permutation = PERMUTATIONS[permutation_id]

    return {
        "schema": ROUTER_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": True,
        "task": task,
        "repo_root": str(repo_root_path),
        "signals": {
            "repo_file_count": repo_file_count,
            "domain_count": domain_count,
            "estimated_task_files": est_files,
        },
        "permutation": permutation_id,
        "stages": permutation["stages"],
        "permutation_summary": permutation["summary"],
        "estimated_speedup_vs_naked": permutation["estimated_speedup_vs_naked"],
        "reasons": reasons,
        "recommendation": _recommendation_text(permutation_id, reasons),
        "errors": [],
    }


def _recommendation_text(permutation_id: str, reasons: list[str]) -> str:
    """Human-readable single line summarizing what to do next."""
    if permutation_id == "skip":
        return "Skip the harness for this task. Edit + test in your IDE; you'll be done faster."
    if permutation_id == "R-only":
        return "Run preflight + write a research note. Decide whether to build BEFORE planning."
    if permutation_id == "R-S":
        return "Preflight + ship. Skip plan, execute, and parallel dispatch."
    if permutation_id == "R-E-R":
        return "Naked agent loop is fine: read, edit, verify. The harness ceremony will cost more than it saves."
    if permutation_id == "R-P-E-R":
        return "Run preflight + plan a DAG + dispatch parallel lanes + review. Skip the heavyweight ship/handoff."
    if permutation_id == "R-P-E-R-S":
        return "Full pipeline. preflight → plan → parallel dispatch → review → shipping evidence."
    return ""


def format_human(payload: dict) -> str:
    """Format the routing decision for terminal display."""
    lines = [
        f"RePERS router decision",
        f"  Task: {payload['task'][:90]}",
        f"  Repo: {payload['repo_root']}",
        f"  Signals: repo_file_count={payload['signals']['repo_file_count']}, "
        f"domain_count={payload['signals']['domain_count']}, "
        f"estimated_task_files={payload['signals']['estimated_task_files']}",
        "",
        f"  -> Permutation: {payload['permutation']}  "
        f"({payload['permutation_summary']})",
        f"     Stages: {' → '.join(payload['stages']) if payload['stages'] else '(none — skip harness)'}",
        f"     Speedup vs naked: {payload['estimated_speedup_vs_naked']}",
        "",
        "  Reasons:",
    ]
    for r in payload["reasons"]:
        lines.append(f"    - {r}")
    lines.append("")
    lines.append(f"  Recommendation: {payload['recommendation']}")
    return "\n".join(lines)

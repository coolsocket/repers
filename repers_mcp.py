"""repers-mcp — MCP server exposing RePERS tools to MCP-aware agents.

Any agent supporting the Model Context Protocol (Claude Code, Cursor,
OpenCode, Continue, Goose, etc.) can drop a single config line and get
RePERS as native callable tools — no need to know about `uvx` / git URLs /
the underlying CLI.

## Install in an MCP-aware agent

Add to the client's MCP config (claude_desktop_config.json / .cursor/mcp.json /
~/.config/...):

    {
      "mcpServers": {
        "repers": {
          "command": "uvx",
          "args": [
            "--from",
            "git+https://github.com/coolsocket/repers.git[mcp]",
            "repers-mcp"
          ]
        }
      }
    }

## Tools exposed

- `repers_route(task, est_files?)` — should I bother with RePERS for this task?
- `repers_capabilities_search(query)` — search the 20-entry capability registry
- `repers_capabilities_list()` — list all capabilities
- `repers_fixture_prove()` — run the deterministic orchestration fixture (proves
  collision-safe dispatch contracts without spawning real agents)
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise SystemExit(
        "repers-mcp requires the `mcp` package. Install with the [mcp] extra:\n"
        "  uvx --from 'git+https://github.com/coolsocket/repers.git[mcp]' repers-mcp\n"
        "or  pipx install 'git+https://github.com/coolsocket/repers.git[mcp]'"
    ) from exc


mcp = FastMCP(
    "repers",
    instructions=(
        "RePERS is the operating layer for multi-agent repository work. "
        "Before doing anything with the harness, call `repers_route` with the "
        "user's task. The router will tell you whether to use RePERS at all "
        "(`skip_harness` / `naked_loop` → don't), or which slice of the "
        "pipeline fits. Branch on `next_step.action`, not on prose."
    ),
)


def _run_repers(args: list[str], timeout_s: int = 30) -> dict[str, Any]:
    """Invoke the `repers` console script and parse its JSON output."""
    try:
        result = subprocess.run(
            ["repers", *args],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "error": (
                "`repers` not found on PATH. The MCP server expects it to be "
                "installed alongside repers-mcp. If you launched via uvx, "
                "check that the package built correctly."
            ),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"`repers {' '.join(args[:1])}` timed out after {timeout_s}s"}

    if result.returncode != 0:
        return {
            "ok": False,
            "error": result.stderr.strip()[:500] or f"repers exited {result.returncode}",
            "stdout_tail": result.stdout[-500:],
        }
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "error": f"`repers {' '.join(args[:1])}` did not emit valid JSON: {exc}",
            "raw_stdout": result.stdout[:1000],
        }


@mcp.tool()
def repers_route(task: str, est_files: Optional[int] = None) -> dict[str, Any]:
    """Decide which R-P-E-R-S permutation fits a task — BEFORE using the harness.

    The router is deterministic (no LLM call, <100 ms) and tells you whether
    RePERS is the right tool for the task at all. Branch on `next_step.action`:

    - `skip_harness` / `naked_loop`  → don't use RePERS, use your own tools
    - `research_only` / `docs_only_ship` → use a single RePERS stage, then stop
    - `invoke_bug_hunt_no_ship` / `invoke_bug_hunt_full` → full pipeline

    Always call this FIRST when a user mentions a coding task; if it says skip,
    don't mention RePERS again to the user.

    Args:
        task: The user's actual task in one sentence (e.g. "fix a typo in README"
              or "refactor the auth middleware across api and worker")
        est_files: Optional estimate of how many files the task will touch
    """
    args = ["route", "--task", task, "--json"]
    if est_files is not None:
        args.extend(["--est-files", str(est_files)])
    return _run_repers(args)


@mcp.tool()
def repers_capabilities_search(query: str) -> dict[str, Any]:
    """Search the 20-entry RePERS capability registry before building new tooling.

    Use this when you might be about to build something that already exists.
    Matches against capability id, summary, and paths.

    Args:
        query: Search string (case-insensitive substring match)
    """
    return _run_repers(["capabilities", "--action", "search", "--query", query, "--json"])


@mcp.tool()
def repers_capabilities_list() -> dict[str, Any]:
    """List all 20 RePERS capabilities with their kind and summary."""
    return _run_repers(["capabilities", "--action", "list", "--json"])


@mcp.tool()
def repers_fixture_prove() -> dict[str, Any]:
    """Run the deterministic orchestration fixture.

    Proves the file-level collision contract (target_files isolation) holds
    on a synthetic multi-lane workload — no LLMs spawned, fully offline.
    Use as a smoke test of the harness's correctness contract before relying
    on it for live multi-agent dispatch.
    """
    return _run_repers(["fixture", "--action", "prove", "--json"], timeout_s=60)


def main() -> None:
    """Entry point — runs FastMCP on stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()

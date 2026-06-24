"""Default route plugin — wraps the in-tree router.py keyword+signal decision tree.

Conforms to .repers/contracts/router.v1.json.

To replace this with your own implementation, drop a new file alongside
(e.g. `plugins/route/llm.py`) exporting the same `route()` + `format_human()`
signature, and select it via `REPERS_PLUGIN_ROUTE=llm`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The default plugin reuses the existing router.py implementation so that
# v0.1.x behavior is preserved exactly — this commit is plumbing only,
# no behavior change.
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from router import route_task as _route_task, format_human as _format_human  # noqa: E402

NAME = "default"
SCHEMA_VERSION = "repers.router.v1"


def route(task: str, repo_root, est_files=None, **kwargs):
    """Return a dict conforming to repers.router.v1."""
    return _route_task(task=task, repo_root=repo_root, est_files=est_files)


def format_human(payload: dict) -> str:
    return _format_human(payload)

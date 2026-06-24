"""Default dispatch plugin — wraps plan_runner.dispatch_ready.

Enforces target_files isolation: no two workers in the same batch write the
same file. Conforms to .repers/contracts/dispatch.v1.json.

Swap by writing plugins/dispatch/<your-name>.py and exporting `dispatch(...)`.
Examples of future plugins: cost-aware.py (rank by token budget per lane),
priority.py (respect plan-declared lane priority).
"""

from __future__ import annotations
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from plan_runner import dispatch_ready  # noqa: E402

NAME = "default"
SCHEMA_VERSION = "repers.dispatch.v1"


def dispatch(plan, task_dir, backend="codex", max_workers=4, **kwargs):
    """Return (manifest_dict, manifest_path)."""
    return dispatch_ready(plan, task_dir, backend=backend, max_workers=max_workers)

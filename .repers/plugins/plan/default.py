"""Default plan plugin — wraps plan_runner.build_plan_json (markdown parser).

Conforms to .repers/contracts/plan.v1.json (forthcoming).
Swap by writing plugins/plan/<your-name>.py (e.g. yaml.py, mermaid.py) and
exporting `plan(...)`.
"""

from __future__ import annotations
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from plan_runner import build_plan_json, build_plan_proposal  # noqa: E402

NAME = "default"
SCHEMA_VERSION = "repers.plan.v1"


def plan(task, task_dir, plan_path, **kwargs):
    """Return (plan_dict, output_path)."""
    return build_plan_json(task, task_dir, plan_path)


def propose(task, task_dir, objective="", max_steps=6, **kwargs):
    """Generate a plan proposal from research.json + objective."""
    return build_plan_proposal(task, task_dir, objective=objective, max_steps=max_steps)

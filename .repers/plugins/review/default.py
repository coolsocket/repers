"""Default review plugin — wraps reviewer.review_task (step_result.v1 schema validator).

Conforms to .repers/contracts/review.v1.json.
Swap by writing plugins/review/<your-name>.py and exporting `review(...)`.
Future plugin candidate: semantic.py (LLM-based deeper verification beyond
schema-shape checks).
"""

from __future__ import annotations
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reviewer import review_task  # noqa: E402

NAME = "default"
SCHEMA_VERSION = "repers.review.v1"


def review(task_dir, update_status=False, **kwargs):
    """Return the review summary dict."""
    return review_task(task_dir, update_status=update_status)

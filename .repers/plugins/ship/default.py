"""Default ship plugin — wraps shipping.create_shipping_report.

Conforms to .repers/contracts/shipping.v1.json (forthcoming).
Swap by writing plugins/ship/<your-name>.py and exporting `ship(...)`.
Future plugin candidates: slsa.py (SLSA-provenance shaped output),
sbom.py (SBOM-embedded delivery evidence), minimal.py (slim evidence
for low-stakes ships).
"""

from __future__ import annotations
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from shipping import create_shipping_report  # noqa: E402

NAME = "default"
SCHEMA_VERSION = "repers.shipping.v1"


def ship(task, task_dir, repo_root, doctor_result, installed_target=None, **kwargs):
    """Return (shipping_report_dict, output_path)."""
    return create_shipping_report(
        task, task_dir, repo_root, doctor_result, installed_target=installed_target
    )

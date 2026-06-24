"""Default preflight plugin — wraps research_index.build_research_artifact.

Conforms to .repers/contracts/preflight.v1.json (forthcoming).
Swap by writing plugins/preflight/<your-name>.py and exporting `preflight(...)`.
"""

from __future__ import annotations
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from research_index import build_research_artifact, refresh  # noqa: E402

NAME = "default"
SCHEMA_VERSION = "repers.preflight.v1"


def preflight(query, index_db_path, repo_root, skills_dir, refresh_index=False, **kwargs):
    """Build the preflight research artifact. Caller handles --codegraph overlay."""
    if refresh_index:
        refresh(index_db_path, repo_root, skills_dir)
    return build_research_artifact(index_db_path, query, repo_root, skills_dir)

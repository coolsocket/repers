"""Console-script entry point — makes `repers ...` invokable after install.

The actual CLI lives at `.repers/scripts/repers.py` (load-bearing path; it's
also what gets copied into receiver repos by `repers install`). This wrapper
locates that script regardless of how the package was installed and runs it.

Lookup precedence:
    1. $REPERS_RUNTIME_ROOT (explicit override; expects scripts/repers.py inside)
    2. .repers/ next to this file (dev checkout)
    3. .repers/ in cwd (agent ran from their own repo root)
    4. _repers_runtime/dot_repers/ inside installed package (uvx / pip / pipx)
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def _candidate_runtimes() -> list[Path]:
    here = Path(__file__).resolve().parent
    candidates: list[Path] = []

    env = os.environ.get("REPERS_RUNTIME_ROOT")
    if env:
        candidates.append(Path(env).expanduser().resolve())

    candidates.extend([
        here / ".repers",
        Path.cwd() / ".repers",
        here / "_repers_runtime" / "dot_repers",
    ])
    return candidates


def _find_runtime() -> Path:
    for candidate in _candidate_runtimes():
        if (candidate / "scripts" / "repers.py").is_file():
            return candidate
    tried = "\n  ".join(str(c) for c in _candidate_runtimes())
    sys.exit(
        "repers: cannot locate the RePERS runtime (.repers/scripts/repers.py).\n"
        f"Looked under:\n  {tried}\n"
        "Set $REPERS_RUNTIME_ROOT to override."
    )


def main() -> None:
    runtime = _find_runtime()
    script = runtime / "scripts" / "repers.py"

    # Default the workspace root to cwd so commands operate on the user's repo,
    # not on the package install dir. The script itself respects this env var.
    os.environ.setdefault("REPERS_WORKSPACE_ROOT", str(Path.cwd()))

    # Run repers.py as if it were invoked directly (preserves argparse, argv,
    # __name__ == "__main__" semantics). sys.argv[1:] already carries the
    # user's args because we're the console-script that received them.
    sys.argv[0] = str(script)
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()

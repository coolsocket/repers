"""Plugin loader — discover and import per-verb implementations from .repers/plugins/.

Lookup precedence:
  1. Env var REPERS_PLUGIN_<VERB> (uppercase). Highest.
  2. .repers/plugins/<verb>/default.py (the shipped baseline).
  3. None — caller is expected to fall back to the legacy in-tree implementation.

The loader is intentionally minimal: it imports the module file and returns
it. The CLI dispatcher in repers.py calls the function whose name matches
the verb (e.g., `route` for the `route` verb) and is responsible for
contract-conformance checks if it wants them.

Backwards compatibility: if a verb has no plugin folder yet, this loader
returns None and the CLI keeps calling the legacy implementation.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Optional


PLUGINS_ROOT = Path(__file__).resolve().parent.parent / "plugins"


def resolve_plugin_name(verb: str) -> str:
    """Returns the plugin name to load for `verb`, honoring env var."""
    env_var = f"REPERS_PLUGIN_{verb.upper()}"
    return os.environ.get(env_var, "default")


def load_plugin(verb: str, name: Optional[str] = None):
    """Load and return the plugin module for `verb`.

    Returns None when no plugin is found (caller should fall back to legacy).
    Raises FileNotFoundError ONLY when the user explicitly set the env var
    to a name that doesn't exist (so silent fallback never masks an
    intentional override).
    """
    explicit = name is not None or os.environ.get(f"REPERS_PLUGIN_{verb.upper()}") is not None
    name = name or resolve_plugin_name(verb)
    path = PLUGINS_ROOT / verb / f"{name}.py"
    if not path.exists():
        if explicit:
            raise FileNotFoundError(
                f"REPERS_PLUGIN_{verb.upper()}={name} requested but no plugin at {path}"
            )
        return None
    spec = importlib.util.spec_from_file_location(
        f"repers_plugin_{verb}_{name}", path
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

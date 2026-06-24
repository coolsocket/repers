# `.repers/plugins/` — swappable verb implementations

Each pipeline verb (route, preflight, plan, dispatch, review, ship) has a
folder here containing one or more **plugins** — independent
implementations that emit the same JSON contract (see `.repers/contracts/`).

```
plugins/
├── route/
│   ├── default.py        # ships with the harness; the keyword+signal decision tree
│   └── (your_impl.py)    # e.g. llm.py — LLM-based intent classifier you write
├── preflight/
│   ├── default.py        # registry + workspace grep
│   └── codegraph.py      # the optional CodeGraph adapter
├── plan/
│   └── markdown.py       # parses plan.md
├── dispatch/
│   └── collision-safe.py # target_files isolation
├── review/
│   └── schema-validator.py
└── ship/
    └── release-pack.py
```

## Plugin contract — what every plugin must export

Each plugin module under `plugins/<verb>/<name>.py` must export a single
function whose name matches the verb. Example for `route`:

```python
# plugins/route/<name>.py
NAME = "your-name-here"
SCHEMA_VERSION = "repers.router.v1"   # the contract you emit

def route(task: str, repo_root: str, est_files: int | None, **kwargs) -> dict:
    """Return a dict conforming to .repers/contracts/router.v1.json."""
    ...

def format_human(payload: dict) -> str:
    """Optional: pretty-print for non-JSON CLI output."""
    ...
```

The contract is your responsibility — drift from
`.repers/contracts/<verb>.v<N>.json` will break downstream stages that
read your output.

## Selecting a plugin at runtime

Two ways to override the default plugin name:

1. **Per-invocation env var** (highest precedence):
   ```bash
   REPERS_PLUGIN_ROUTE=llm python3 .repers/scripts/repers.py route --task "..."
   ```

2. **Default fallback**: any plugin module named `default.py` under the
   verb's folder. (Future: `.repers/config.yaml` will let you pin a
   non-`default` plugin per verb.)

If no plugin is found, the CLI falls back to the legacy in-tree
implementation (`router.py`, `plan_runner.py`, etc.) so v0.1.x receivers
keep working.

## Why this exists

v0.2 separates **the contract** (stable JSON schemas) from **the
implementation** (the Python that produces conforming JSON). Adding an
LLM-based router, a YAML plan parser, a cost-aware dispatcher, or a
SLSA-shaped release-pack format becomes "add one file to `plugins/`",
not "fork the harness".

The contracts are versioned (`*.v1.json`); a v2 plugin can coexist with
a v1 plugin during deprecation.

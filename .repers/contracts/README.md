# `.repers/contracts/` — versioned stage contracts

One JSON Schema per pipeline stage. These are the **stable JSON shapes**
that flow between R-P-E-R-S stages. Each lives at a versioned filename
(`<name>.v<N>.json`) so a new schema version can ship alongside the old
during deprecation.

The schemas serve three purposes:

1. **Discoverable documentation** — an agent (or human) can `cat` a file
   here to know what the next stage will read or write, without grepping
   `repers.py` for `"schema":` literals.
2. **Plugin contract** — any plugin in `.repers/plugins/<verb>/*.py` MUST
   emit data conforming to the matching contract schema. Plugins that
   drift from this break interoperability.
3. **Future runtime validation** — v0.3+ may wire `jsonschema` to validate
   plugin outputs at the boundary. v0.2 ships the schemas as
   reference-only.

## Current contracts

| File | Stage | Emitted by |
|---|---|---|
| `router.v1.json` | 🧭 Route | `route` CLI / plugins/route/* |
| `preflight.v1.json` | 🧠 R | `preflight` CLI / plugins/preflight/* |
| `plan.v1.json` | ⚡ P | `plan` CLI / plugins/plan/* |
| `dispatch.v1.json` | ⚡ E (supervisor) | `dispatch` CLI / plugins/dispatch/* |
| `step_result.v1.json` | ⚡ E (worker) | Worker writes (`WORKER.md` is the prose spec) |
| `review.v1.json` | 🔗 R | `review` CLI / plugins/review/* |
| `shipping.v1.json` | 🔗 S | `shipping` CLI / plugins/ship/* |

## Adding a new schema version

When you need a v2 of any schema:

1. **Don't delete v1.** Ship `<name>.v2.json` alongside.
2. Update the relevant plugin to emit v2 (and bump the `schema` string).
3. Mark v1 deprecated in this README; remove after one minor release.

## Are these strictly enforced today?

No. As of v0.2 the schemas are reference contracts; the runtime still
trusts well-formed strings emitted by plugins. v0.3 will add an opt-in
`REPERS_VALIDATE_CONTRACTS=1` env var that runs every plugin output
through `jsonschema` before passing it downstream.

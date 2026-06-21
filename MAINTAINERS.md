# Maintainers

RePERS maintainers are responsible for keeping the packaged workflow small,
installable, and verifiable.

Maintainer duties:

- Keep `.repers/scripts/repers.py` and `.repers/scripts/install_repers.py`
  compatible with the smoke tests.
- Run `bundle-status --package --verify-roundtrip --json` before publishing a
  package.
- Update `CHANGELOG.md` for user-visible behavior, package format, hook, or
  readiness changes.
- Keep `ROADMAP.md` focused on near-term reusable workflow improvements.
- Prefer extending preflight and existing package readiness checks before adding
  unrelated scripts.

Release gate:

```powershell
python .repers\scripts\repers.py bundle-status --package --verify-roundtrip --json
python .repers\scripts\repers.py fixture --action prove --json
python .repers\scripts\repers.py receiver-fixture --json
python .repers\scripts\repers.py release-evidence --package --verify-roundtrip --json
python tests\smoke_repers.py
```

# RePERS Verify All

- Generated: `2026-06-21T15:40:44.084077+00:00`
- OK: `True`
- Status: `blocked_external`
- Objective complete: `False`
- Objective blockers: `publication_ready`

## Gates

- `verify_install`: `True`
- `capabilities_validate`: `True`
- `capabilities_search_state`: `True`
- `bundle_status_package_roundtrip`: `True`
- `receiver_fixture`: `True`
- `remote_bootstrap_fixture`: `True`
- `publish_clone_fixture`: `True`
- `smoke_tests`: `True`
- `state_deep`: `True`

## Next

- External action: `configure_hosted_remote`

```powershell
python -B .repers/scripts/repers.py remote-bootstrap --remote-url <hosted-git-url> --apply --json
```

# RePERS Continuation

- Generated: `2026-06-21T14:50:22.252655+00:00`
- Status: `local_work_available`
- Objective complete: `False`

## Blocking Requirements

- `publication_ready`

## Local Actions

### commit_or_clean_worktree: Commit or intentionally exclude working tree changes

- Status: `ready`
- Reason: Publication readiness requires a clean committed branch before configuring or pushing a remote.

```powershell
git status --short
```

### verify_after_publication_setup: Re-run deep audit after remote setup

- Status: `after_remote`
- Reason: Confirms clean tree, package gates, and publish readiness after the external remote is configured.

```powershell
python -B .repers/scripts/repers.py objective-audit --deep --output dist --json
```

## External Actions

### configure_hosted_remote: Configure hosted Git remote

- Status: `needs_remote_url`
- Reason: Requires a real hosted repository URL; local fixture already proves the apply and push mechanics.

```powershell
python -B .repers/scripts/repers.py remote-bootstrap --remote-url <hosted-git-url> --apply --json
```

### push_branch: Push committed branch

- Status: `after_remote`
- Reason: Requires the hosted remote to exist and be configured.

```powershell
git push -u origin <branch>
```

### open_draft_pr: Open draft pull request

- Status: `after_push`
- Reason: Requires GitHub CLI authentication or an equivalent provider API.

```powershell
gh pr create --draft --base main --head <branch> --title "Publish RePERS" --body-file dist/repers-publish-handoff.md
```

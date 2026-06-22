# RePERS Publish Handoff

- Generated: `2026-06-22T01:23:46.310660+00:00`
- Branch: `codex/repers-initial-package`
- Commit: `d9aaf9c54be31ed18925d0e41e65f2b7ecfb0873`
- Clean tree: `False`
- Publish ready: `False`

## Remaining Blockers

- commit or intentionally exclude working tree changes
- configure a Git remote before opening a PR

## Commands

### add_remote: Configure Git remote

- Status: `ready`
- Reason: Remote URL was provided.

```powershell
git remote add origin https://example.invalid/repers.git
```

### push_branch: Push release branch

- Status: `blocked`
- Reason: Commit or intentionally exclude working tree changes first.

```powershell
git push -u origin codex/repers-initial-package
```

### open_draft_pr: Open draft pull request

- Status: `blocked`
- Reason: Requires GitHub CLI authentication and pushed branch.

```powershell
gh pr create --draft --base main --head codex/repers-initial-package --title "Add publish clone verification fixture" --body-file <handoff-md>
```

## Package

- Archive: `C:\Users\Administrator\Documents\RePERS\dist\repers-0.1.0.zip`
- SHA-256: `bd143e336b47c2a9a8a8b80414234e80c156187a34eac93f4b93b868ca75bb9f`
- Round trip: `True`

This handoff is intentionally non-destructive. It records the commands
needed by a human or future agent, but it does not add remotes, push,
or open pull requests.

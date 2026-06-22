# RePERS Publish Handoff

- Generated: `2026-06-22T02:40:52.830385+00:00`
- Branch: `codex/repers-initial-package`
- Commit: `34b187e25d33799dd1914b982ed7749544ea9338`
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
gh pr create --draft --base main --head codex/repers-initial-package --title "Add snapshot freshness gate" --body-file <handoff-md>
```

## Package

- Archive: `C:\Users\Administrator\Documents\RePERS\dist\repers-0.1.0.zip`
- SHA-256: `70f3fa4053878df7992a3e7219ccc879d42099cd795ab9f4ee470e17debe1bda`
- Round trip: `True`

This handoff is intentionally non-destructive. It records the commands
needed by a human or future agent, but it does not add remotes, push,
or open pull requests.

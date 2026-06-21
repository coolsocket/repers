# RePERS Remote Bootstrap

- Generated: `2026-06-21T14:37:51.258140+00:00`
- Remote name: `origin`
- Remote URL provided: `https://example.invalid/repers.git`
- Apply requested: `False`
- Apply changed remote: `False`
- OK: `True`

## Safety

- No branch push is executed by this command.
- No pull request is opened by this command.
- Git remotes are changed only when `--apply --remote-url <url>` is passed.
- Existing remotes with different URLs are not overwritten.

## Actions

### inspect_remotes: Inspect current Git remotes

- Status: `done`
- Reason: Remote state was inspected before generating this bootstrap artifact.

```powershell
git remote -v
```

### add_remote: Configure publication remote

- Status: `ready`
- Reason: Remote URL was provided.

```powershell
git remote add origin https://example.invalid/repers.git
```

### publish_handoff: Regenerate publish handoff evidence

- Status: `ready`
- Reason: Handoff path: C:\Users\Administrator\Documents\RePERS\dist\repers-publish-handoff.md

```powershell
python .repers/scripts/repers.py publish-handoff --remote-name origin --remote-url https://example.invalid/repers.git --base-branch main --pr-title "Add RePERS autonomous continuation runner" --json
```

### verify_publish_ready: Verify objective audit after remote setup

- Status: `ready`
- Reason: Run after the remote is configured and publish handoff is refreshed.

```powershell
python .repers/scripts/repers.py objective-audit --deep --json
```

### push_branch: Push release branch

- Status: `blocked`
- Reason: Commit or intentionally exclude working tree changes first.

```powershell
git push -u origin codex/repers-initial-package
```

### open_draft_pr: Open draft pull request

- Status: `blocked`
- Reason: Requires GitHub CLI authentication and a pushed branch.

```powershell
gh pr create --draft --base main --head codex/repers-initial-package --title "Add RePERS autonomous continuation runner" --body-file C:\Users\Administrator\Documents\RePERS\dist\repers-publish-handoff.md
```

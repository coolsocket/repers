# RePERS Remote Bootstrap

- Generated: `2026-06-24T07:42:12.951852+00:00`
- Remote name: `origin`
- Remote URL provided: `None`
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

- Status: `done`
- Reason: Named remote already exists.

```powershell
git remote add origin <remote-url>
```

### publish_handoff: Regenerate publish handoff evidence

- Status: `ready`
- Reason: Handoff path: /home/sa_114486498687979675637/repers/dist/repers-publish-handoff.md

```powershell
python .repers/scripts/repers.py publish-handoff --remote-name origin --remote-url <remote-url> --base-branch main --pr-title "v0.2 Phase B+C all 6 verbs plugin loaded+all 7 contracts extracted" --json
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
git push -u origin main
```

### open_draft_pr: Open draft pull request

- Status: `blocked`
- Reason: Requires GitHub CLI authentication and a pushed branch.

```powershell
gh pr create --draft --base main --head main --title "v0.2 Phase B+C all 6 verbs plugin loaded+all 7 contracts extracted" --body-file /home/sa_114486498687979675637/repers/dist/repers-publish-handoff.md
```

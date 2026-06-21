# Basic RePERS Task Example

This example shows the smallest local workflow a receiver can run after
installing RePERS into a Git repository.

```powershell
python .repers\scripts\repers.py init --task "basic task"
python .repers\scripts\repers.py preflight --query "basic task workflow" --refresh --json
python .repers\scripts\repers.py plan --task basic_task --json
python .repers\scripts\repers.py run --task basic_task --action dry-run --json
python .repers\scripts\repers.py bundle-status --json
```

The important rule is that Markdown is the human surface and JSON is the
machine contract. Another agent should be able to inspect the generated task
folder without relying on chat history.

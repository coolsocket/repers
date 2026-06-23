# Security Policy

RePERS is a local-first repository harness. It does not run a network service
or publish to a package registry. The threat surface is the installer, the
pre-commit hook, the capability scripts, and the templates copied into
receiver repos.

## Reporting a vulnerability

**Don't open a public issue.** Use GitHub's private channel:

> https://github.com/coolsocket/repers/security/advisories/new

If that's unavailable, contact the maintainer via the email in `git log`
(most recent maintainer commit's `Author:`). Do not include secrets, private
repository contents, or full local paths unless required to reproduce.

## What to include

- Affected file path + RePERS version (from `.codex-plugin/plugin.json`).
- Clear description of the vulnerability + proof-of-concept (if you have one).
- Your assessment of severity (local code execution? privilege boundary
  crossing? install-time tampering? evidence forgery?).

## What to expect

- Initial acknowledgment within **72 hours**.
- Coordinated disclosure — patched release ships before the advisory becomes public.
- Public credit unless you ask to remain anonymous.

---

## Threat-modeled surfaces

These deserve the closest review by anyone auditing this code:

- **`.repers/scripts/install_repers.py`** — runs at receiver install time. Writes
  files into the receiver's working tree and optionally registers a Git
  pre-commit hook. Pay attention to:
  - Path traversal in `--target` argument.
  - Symlink races during extraction.
  - Hook-policy default (`warn`, not `strict`) — opt-in escalation only.

- **`.repers/hooks/pre-commit`** — runs in the receiver's repo before every
  commit if installed. Must not assume hostile-free working tree. Avoid:
  - Untrusted command construction from staged file paths.
  - Long-running operations that block commits indefinitely.

- **`.repers/scripts/repers.py` subcommands** — each runs locally with the
  invoking user's privileges. The `dispatch` and `run` subcommands shell out
  for worker-command execution. Pay attention to:
  - Argument quoting in subprocess calls.
  - Target-file boundary enforcement (a worker writing outside its declared
    `target_files` is the orchestration-safety bug we explicitly guard against).

- **`.repers/capabilities/registry.json`** — paths and commands here are
  surfaced verbatim by `preflight`. A malicious registry entry is a malicious
  command suggestion. Treat any PR touching this file as security-sensitive.

- **`.repers/templates/**`** — copied verbatim into receiver projects by the
  installer. A malicious template = malicious code in every receiver.

- **`dist/repers-release-pack.zip`** — the transferable handoff. Any receiver
  verifying a pack trusts the embedded `repers-verify-all.json`. The
  `release-pack-verify` gate must re-execute verification against the
  extracted contents rather than trusting the embedded JSON verbatim.

## Out of scope

- Vulnerabilities in receiver projects that adopt RePERS — those belong to
  the receiver.
- Issues in tools RePERS shells out to (`git`, `python`, optional `codegraph`).
- Cosmetic markdown / docs issues (use a regular issue).

## Verification

Run the receiver status gate after install:

```bash
python .repers/scripts/repers.py bundle-status --json
```

Run the full package gate before sharing a bundle:

```bash
python .repers/scripts/repers.py bundle-status --package --verify-roundtrip --json
```

Thank you for keeping RePERS users safe.

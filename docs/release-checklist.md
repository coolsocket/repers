# Release Checklist

Use this checklist before publishing a RePERS release or handing the package to
another repository.

## Build

```powershell
python .repers\scripts\repers.py package --output dist --verify-roundtrip --json
python .repers\scripts\repers.py release-pack --json
python .repers\scripts\repers.py release-pack-verify --archive dist\repers-release-pack.zip --json
```

Required local assets:

- `dist/repers-0.1.0.zip`
- `dist/repers-0.1.0-readiness.json`
- `dist/repers-release-pack.zip`
- `dist/repers-release-pack.json`
- `dist/repers-release-pack.md`
- `dist/repers-state.json`
- `dist/repers-state.md`

## Verify

```powershell
python .repers\scripts\repers.py verify-all --json
python .repers\scripts\repers.py receiver-fixture --json
python .repers\scripts\repers.py source-install-fixture --json
python .repers\scripts\repers.py publish-clone-fixture --json
```

Minimum evidence:

- package readiness reports `ok=true`;
- release pack verification reports `ok=true`;
- receiver fixture proves install, doctor, bundle status, capabilities, and
  deterministic fixture from a fresh target;
- source install fixture proves one-command bootstrap from a checkout;
- publish clone fixture proves clone-side verification from a bare remote.

## Publish

GitHub Release assets:

- `repers-0.1.0.zip`
- `repers-release-pack.zip`
- `repers-release-pack.json`
- `repers-release-pack.md`

Release notes should include:

- one-line value statement;
- install command;
- verification command;
- known limits;
- checksums or a pointer to the release-pack manifest.

## After Publish

Run:

```powershell
python .repers\scripts\repers.py state --deep --json
python .repers\scripts\repers.py snapshot-freshness --json
```

Then confirm:

- the public repository has description, topics, and license visible;
- README first screen has install and demo links;
- the release asset can be downloaded and verified;
- `dist/repers-state.md` reflects current Git remote and branch state.

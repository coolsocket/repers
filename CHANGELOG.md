# Changelog

All notable RePERS bundle changes are tracked here.

## 0.1.0 - 2026-06-21

- Added an installable `.repers/` runtime with preflight, doctor, audit,
  install-hook, verify-install, package, and bundle-status commands.
- Added package manifests, package readiness sidecars, and round-trip archive
  verification.
- Added receiver smoke tests and GitHub Actions workflow coverage.
- Added open-source onboarding and governance files for contributors,
  maintainers, support, security, roadmap, and examples.
- Added a deterministic orchestration fixture that proves conflict-safe worker
  dispatch, worker-command execution, local join verification, and review
  evidence.
- Added `capabilities/registry.json` plus a `capabilities` CLI command, and
  indexed registry entries in preflight as `source=local_capability`.
- Added `release-evidence` to generate publish-readiness JSON with package,
  governance, capability registry, and Git branch/commit/remote state.
- Added `receiver-fixture` to install the package into a fresh Git repository
  and prove receiver-side commands after installation.

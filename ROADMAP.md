# Roadmap

The RePERS roadmap is organized around making the bundle easier to trust,
install, and extend.

## Current

- Package an installed `.repers/` runtime into a reusable zip archive.
- Verify the archive with manifest checks and round-trip installation.
- Reuse preflight before planning new reusable capabilities.
- Ship receiver-facing docs, examples, smoke tests, and CI.
- Prove conflict-safe worker-command orchestration with a deterministic
  large-task fixture.
- Publish a canonical JSON registry for reusable local workflows, scripts,
  hooks, templates, and gates.
- Generate release evidence that separates package validity from final Git
  publish readiness.
- Prove installed receiver usage in a fresh Git repository.

## Next

- Add richer DAG planning artifacts that can be shared with subagents.
- Add branch/PR automation once the repository has a remote and committed base.

## Later

- Integrate optional external code graph providers behind the existing
  preflight interface.
- Add signed or provenance-rich release artifacts.
- Add install profiles for different repository sizes and risk levels.

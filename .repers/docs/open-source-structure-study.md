# Open Source Structure Study

This study sampled 10 popular open-source repositories through the GitHub
contents API on 2026-06-20. The purpose is not to clone their internals, but to
extract packaging, promotion, governance, and contributor-experience patterns
that RePERS should adopt.

## Sampled Repositories

| Repository | Root Structure Signals Observed |
|---|---|
| `kubernetes/kubernetes` | `.github`, `AGENTS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSES`, `Makefile`, `OWNERS`, `SECURITY_CONTACTS`, `SUPPORT.md`, `api`, `build`, `cmd`, `docs`, `go.mod` |
| `microsoft/vscode` | `.agents`, `.devcontainer`, `.github`, `.vscode`, `AGENTS.md`, `CONTRIBUTING.md`, `CodeQL.yml`, `LICENSE.txt`, `README.md`, `SECURITY.md` |
| `facebook/react` | `.github`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `LICENSE`, `MAINTAINERS`, `README.md`, `SECURITY.md`, package/build config files |
| `vercel/next.js` | `.agents`, `.devcontainer`, `.github`, `.husky`, `AGENTS.md`, config files, package/tooling roots |
| `rust-lang/rust` | `.github`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `Cargo.toml`, `INSTALL.md`, `LICENSES`, `README.md`, `RELEASES.md`, `compiler`, `library`, `src`, `tests` |
| `python/cpython` | `.github`, `.pre-commit-config.yaml`, `Doc`, `Grammar`, `Include`, `InternalDocs`, `Lib`, `Makefile.pre.in`, `Misc`, `Modules`, `Objects`, `Tools` |
| `hashicorp/terraform` | `.changes`, `.github`, `.release`, `BUGPROCESS.md`, `BUILDING.md`, `CHANGELOG.md`, `CODEOWNERS`, `Makefile`, `docs`, `go.mod` |
| `moby/moby` | `.github`, `AGENTS.md`, `CONTRIBUTING.md`, `Dockerfile`, `MAINTAINERS`, `ROADMAP.md`, `SECURITY.md`, `TESTING.md`, `api` |
| `homebrew/brew` | `.codex`, `.github`, `.vscode`, `AGENTS.md`, `CODEOWNERS`, `CONTRIBUTING.md`, `Dockerfile`, `Library`, `README.md`, `bin` |
| `fastapi/fastapi` | `.github`, `.pre-commit-config.yaml`, `CITATION.cff`, `LICENSE`, `README.md`, `docs`, `docs_src`, `fastapi`, `pyproject.toml`, `scripts`, `tests` |

## Patterns To Adopt

1. **Root-level onboarding**: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and install docs should be visible at the top level.
2. **Automation is visible**: `.github`, hooks, scripts, and CI/test entrypoints are discoverable, not hidden in prose.
3. **Governance is explicit**: ownership, maintainers, security, release, roadmap, and support files are common in mature repos.
4. **Generated/runtime state is separated**: source docs and runtime caches should not mix.
5. **Examples/tests are first-class**: serious projects include sample apps, fixture tasks, and repeatable test entrypoints.
6. **Contributor agents are documented**: several modern repos now include `AGENTS.md`, `.agents`, `.codex`, or `CLAUDE.md`.
7. **Packaging is boring and repeatable**: install/build/test commands live in scripts, Makefiles, package config, or docs.

## RePERS Repo Implications

RePERS should grow toward this structure:

```text
README.md
CONTRIBUTING.md
SECURITY.md
docs/
  architecture.md
  contracts.md
  installation.md
  open-source-structure-study.md
  packaging.md
hooks/
scripts/
templates/
tests/
examples/
repers_tasks/
.github/
.gitattributes
.gitignore
```

The immediate implementation path is to keep the local-first `.repers` bundle,
but make the source repository look like a mature installable project.

## Source URLs

- https://api.github.com/repos/kubernetes/kubernetes/contents
- https://api.github.com/repos/microsoft/vscode/contents
- https://api.github.com/repos/facebook/react/contents
- https://api.github.com/repos/vercel/next.js/contents
- https://api.github.com/repos/rust-lang/rust/contents
- https://api.github.com/repos/python/cpython/contents
- https://api.github.com/repos/hashicorp/terraform/contents
- https://api.github.com/repos/moby/moby/contents
- https://api.github.com/repos/homebrew/brew/contents
- https://api.github.com/repos/fastapi/fastapi/contents

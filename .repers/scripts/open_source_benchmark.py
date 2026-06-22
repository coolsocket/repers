import json
from datetime import datetime, timezone
from pathlib import Path


OPEN_SOURCE_BENCHMARK_SCHEMA = "repers.open_source_benchmark.v1"
OPEN_SOURCE_BENCHMARK_RESULT_SCHEMA = "repers.open_source_benchmark_result.v1"


def load_benchmark(install_root):
    path = Path(install_root) / "docs" / "open-source-benchmark.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def file_record(root, rel):
    path = Path(root) / rel
    return {
        "path": rel,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def verify_open_source_benchmark(workspace_root, install_root):
    workspace = Path(workspace_root).resolve()
    install = Path(install_root).resolve()
    benchmark_path, benchmark = load_benchmark(install)

    repositories = benchmark.get("repositories", [])
    patterns = benchmark.get("patterns", [])
    adoption = benchmark.get("repers_adoption", {})
    source_required = adoption.get("source_required_paths", [])
    installed_required = adoption.get("installed_required_paths", [])

    source_files = [file_record(workspace, path) for path in source_required]
    installed_files = [file_record(workspace, path) for path in installed_required]
    missing_source = [item["path"] for item in source_files if not item["exists"]]
    missing_installed = [item["path"] for item in installed_files if not item["exists"]]
    source_surface_applicable = any(item["exists"] for item in source_files)
    missing_repo_fields = [
        item.get("repo", "<unknown>")
        for item in repositories
        if not item.get("repo") or not item.get("source_url") or not item.get("root_signals") or not item.get("promotion_signals")
    ]

    errors = []
    if benchmark.get("schema") != OPEN_SOURCE_BENCHMARK_SCHEMA:
        errors.append("benchmark schema mismatch")
    if len(repositories) < 10:
        errors.append("benchmark has fewer than 10 repositories")
    if len({item.get("source_url") for item in repositories if item.get("source_url")}) < 10:
        errors.append("benchmark has fewer than 10 source URLs")
    if len(patterns) < 6:
        errors.append("benchmark has too few reusable patterns")
    if missing_repo_fields:
        errors.append("one or more repositories are missing required evidence fields")
    if source_surface_applicable and missing_source:
        errors.append("source repo is missing adopted open-source structure files")
    if missing_installed:
        errors.append("installed runtime is missing benchmark or reuse surfaces")

    return {
        "schema": OPEN_SOURCE_BENCHMARK_RESULT_SCHEMA,
        "ok": not errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "install_root": str(install),
        "benchmark_path": str(benchmark_path.resolve()),
        "benchmark_schema": benchmark.get("schema"),
        "last_refreshed": benchmark.get("last_refreshed"),
        "repository_count": len(repositories),
        "source_url_count": len({item.get("source_url") for item in repositories if item.get("source_url")}),
        "pattern_count": len(patterns),
        "source_files": source_files,
        "source_surface_applicable": source_surface_applicable,
        "installed_files": installed_files,
        "missing_source_paths": missing_source,
        "missing_installed_paths": missing_installed,
        "missing_repository_fields": missing_repo_fields,
        "errors": errors,
    }


def write_open_source_benchmark_report(result, output_dir):
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "repers-open-source-benchmark.json"
    markdown_path = output / "repers-open-source-benchmark.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# RePERS Open Source Benchmark",
        "",
        f"- Generated: `{result['generated_at']}`",
        f"- OK: `{result['ok']}`",
        f"- Repositories: `{result['repository_count']}`",
        f"- Source URLs: `{result['source_url_count']}`",
        f"- Patterns: `{result['pattern_count']}`",
        f"- Benchmark: `{result['benchmark_path']}`",
        "",
        "## Missing Source Paths",
        "",
    ]
    lines.extend(f"- `{path}`" for path in result["missing_source_paths"]) or lines.append("- None")
    lines.extend(["", "## Missing Installed Paths", ""])
    lines.extend(f"- `{path}`" for path in result["missing_installed_paths"]) or lines.append("- None")
    if result["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in result["errors"])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path

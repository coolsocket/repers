import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


SOURCE_ROOT = Path(__file__).resolve().parents[1]
GIT_STATE_ROOT = SOURCE_ROOT.parent if SOURCE_ROOT.name == ".repers" else SOURCE_ROOT
REPERS_VERSION = "0.1.0"
PACKAGE_SCHEMA = "repers.package_manifest.v1"
READINESS_SCHEMA = "repers.package_readiness.v1"
PACKAGE_DIR_PREFIX = f"repers-{REPERS_VERSION}"
PACKAGE_MANIFEST_NAME = "repers-package-manifest.json"
PACKAGE_READINESS_NAME = "repers-package-readiness.json"
PACKAGE_INCLUDE_PATHS = [
    ".gitattributes",
    "README.md",
    "capabilities",
    "docs",
    "hooks",
    "scripts",
    "templates",
    "tests",
]
INSTALLED_BUNDLE_PARENT_INCLUDE_PATHS = [
    ".github",
    ".gitattributes",
    ".gitignore",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "MAINTAINERS.md",
    "README.md",
    "ROADMAP.md",
    "SECURITY.md",
    "SUPPORT.md",
    "docs",
    "examples",
    "tests",
]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_source_state():
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=GIT_STATE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=GIT_STATE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        return {"ok": True, "commit": commit, "dirty": bool(status), "status_count": len(status)}
    except Exception as exc:
        return {"ok": False, "commit": None, "dirty": None, "status_count": 0, "error": str(exc)}


def package_excluded(relative):
    rel = str(relative).replace("\\", "/")
    parts = PurePosixPath(rel).parts
    return (
        not rel
        or rel.startswith(".git/")
        or rel.startswith(".repers/")
        or rel.startswith(".codegraph/")
        or rel.startswith("repers_tasks/")
        or rel.startswith("dist/")
        or ".goal-machine" in parts
        or "__pycache__" in parts
        or rel.endswith(".pyc")
    )


def iter_package_files(source_root=SOURCE_ROOT):
    root = Path(source_root)
    emitted = set()
    if root.name == ".repers":
        parent = root.parent
        for include in INSTALLED_BUNDLE_PARENT_INCLUDE_PATHS:
            start = parent / include
            if not start.exists():
                continue
            if start.is_file():
                candidates = [start]
            else:
                candidates = sorted(path for path in start.rglob("*") if path.is_file())
            for path in candidates:
                relative = path.relative_to(parent).as_posix()
                if not package_excluded(relative) and relative not in emitted:
                    emitted.add(relative)
                    yield path, relative

    for include in PACKAGE_INCLUDE_PATHS:
        start = root / include
        if not start.exists():
            continue
        if start.is_file():
            candidates = [start]
        else:
            candidates = sorted(path for path in start.rglob("*") if path.is_file())
        for path in candidates:
            relative = path.relative_to(root).as_posix()
            if not package_excluded(relative) and relative not in emitted:
                emitted.add(relative)
                yield path, relative


def package_surface(file_records):
    paths = {record["path"] for record in file_records}
    return {
        "has_top_level_readme": "README.md" in paths,
        "has_changelog": "CHANGELOG.md" in paths,
        "has_contributing": "CONTRIBUTING.md" in paths,
        "has_maintainers": "MAINTAINERS.md" in paths,
        "has_roadmap": "ROADMAP.md" in paths,
        "has_security": "SECURITY.md" in paths,
        "has_support": "SUPPORT.md" in paths,
        "has_ci": any(path.startswith(".github/workflows/") for path in paths),
        "has_capability_registry": "capabilities/registry.json" in paths,
        "has_docs": any(path.startswith("docs/") for path in paths),
        "has_examples": any(path.startswith("examples/") for path in paths),
        "has_hooks": any(path.startswith("hooks/") for path in paths),
        "has_scripts": any(path.startswith("scripts/") for path in paths),
        "has_templates": any(path.startswith("templates/") for path in paths),
        "has_tests": any(path.startswith("tests/") for path in paths),
        "has_install_script": "scripts/install_repers.py" in paths,
        "has_cli": "scripts/repers.py" in paths,
    }


def source_shape():
    return "installed_bundle" if SOURCE_ROOT.name == ".repers" else "source_tree"


def build_readiness_manifest(archive_path, archive_sha256, file_records):
    surface = package_surface(file_records)
    warnings = []
    if not surface["has_top_level_readme"]:
        warnings.append("package archive has no top-level README.md")
    if not surface["has_changelog"]:
        warnings.append("package archive has no CHANGELOG.md")
    if not surface["has_contributing"]:
        warnings.append("package archive has no CONTRIBUTING.md")
    if not surface["has_maintainers"]:
        warnings.append("package archive has no MAINTAINERS.md")
    if not surface["has_roadmap"]:
        warnings.append("package archive has no ROADMAP.md")
    if not surface["has_security"]:
        warnings.append("package archive has no SECURITY.md")
    if not surface["has_support"]:
        warnings.append("package archive has no SUPPORT.md")
    if not surface["has_ci"]:
        warnings.append("package archive has no visible CI workflow")
    if not surface["has_capability_registry"]:
        warnings.append("package archive has no capabilities/registry.json")
    if not surface["has_examples"]:
        warnings.append("package archive has no examples")
    if not surface["has_tests"]:
        warnings.append("package archive has no packaged tests")
    if not surface["has_install_script"]:
        warnings.append("package archive has no scripts/install_repers.py")

    archive_root = PACKAGE_DIR_PREFIX
    return {
        "schema": READINESS_SCHEMA,
        "version": REPERS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_shape": source_shape(),
        "archive_path": str(archive_path),
        "archive_sha256": archive_sha256,
        "archive_sha256_scope": "final_sidecar" if archive_sha256 else "external_package_output",
        "archive_root": archive_root,
        "package_manifest": f"{archive_root}/{PACKAGE_MANIFEST_NAME}",
        "package_readiness": f"{archive_root}/{PACKAGE_READINESS_NAME}",
        "surface": surface,
        "receiver_commands": {
            "extract": f"Expand-Archive {archive_path.name} -DestinationPath .",
            "install": f"python {archive_root}/scripts/install_repers.py --target <target-repo>",
            "verify": "python <target-repo>/.repers/scripts/repers.py verify-install --json",
            "doctor": "python <target-repo>/.repers/scripts/repers.py doctor --json",
            "capabilities": "python <target-repo>/.repers/scripts/repers.py capabilities --action search --query \"capability query\" --json",
            "preflight": "python <target-repo>/.repers/scripts/repers.py preflight --query \"capability query\" --refresh --json",
            "fixture_prove": "python <target-repo>/.repers/scripts/repers.py fixture --action prove --json",
            "receiver_fixture": f"python {archive_root}/scripts/repers.py receiver-fixture --json",
            "publish_handoff": "python <target-repo>/.repers/scripts/repers.py publish-handoff --json",
            "remote_bootstrap": "python <target-repo>/.repers/scripts/repers.py remote-bootstrap --remote-url <remote-url> --json",
            "remote_bootstrap_fixture": "python <target-repo>/.repers/scripts/repers.py remote-bootstrap-fixture --json",
            "objective_audit": "python <target-repo>/.repers/scripts/repers.py objective-audit --json",
            "package_again": "python <target-repo>/.repers/scripts/repers.py package --output dist --json",
        },
        "acceptance": [
            "archive exists and SHA-256 matches the command output or sidecar readiness file",
            "repers-package-manifest.json is present under archive_root",
            "scripts/install_repers.py is present",
            "scripts/repers.py is present",
            "verify-install returns ok=true after installing into a target repository",
        ],
        "warnings": warnings,
        "ok": (
            surface["has_top_level_readme"]
            and surface["has_changelog"]
            and surface["has_contributing"]
            and surface["has_maintainers"]
            and surface["has_roadmap"]
            and surface["has_security"]
            and surface["has_support"]
            and surface["has_ci"]
            and surface["has_capability_registry"]
            and surface["has_examples"]
            and surface["has_tests"]
            and surface["has_install_script"]
            and surface["has_cli"]
            and surface["has_templates"]
        ),
    }


def run_roundtrip_verification(archive_path, archive_root):
    result = {
        "schema": "repers.package_roundtrip.v1",
        "ok": False,
        "archive_path": str(Path(archive_path).resolve()),
        "archive_root": archive_root,
        "steps": [],
        "verify": None,
        "errors": [],
    }
    try:
        with tempfile.TemporaryDirectory(prefix="repers-package-roundtrip-") as temp_dir:
            temp_root = Path(temp_dir)
            extract_root = temp_root / "extract"
            target_root = temp_root / "target"
            extract_root.mkdir()
            target_root.mkdir()

            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(extract_root)
            result["steps"].append({"name": "extract", "ok": True, "path": str(extract_root)})

            git_init = subprocess.run(
                ["git", "init"],
                cwd=target_root,
                capture_output=True,
                text=True,
            )
            result["steps"].append(
                {
                    "name": "git_init",
                    "ok": git_init.returncode == 0,
                    "returncode": git_init.returncode,
                    "stdout_tail": git_init.stdout[-1000:],
                    "stderr_tail": git_init.stderr[-1000:],
                }
            )
            if git_init.returncode != 0:
                result["errors"].append("git init failed")
                return result

            package_root = extract_root / archive_root
            installer = package_root / "scripts" / "install_repers.py"
            install = subprocess.run(
                [sys.executable, str(installer), "--target", str(target_root), "--no-hook"],
                cwd=package_root,
                capture_output=True,
                text=True,
            )
            result["steps"].append(
                {
                    "name": "install",
                    "ok": install.returncode == 0,
                    "returncode": install.returncode,
                    "stdout_tail": install.stdout[-1000:],
                    "stderr_tail": install.stderr[-1000:],
                }
            )
            if install.returncode != 0:
                result["errors"].append("archive install failed")
                return result

            verify = subprocess.run(
                [
                    sys.executable,
                    str(target_root / ".repers" / "scripts" / "repers.py"),
                    "verify-install",
                    "--json",
                ],
                cwd=target_root,
                capture_output=True,
                text=True,
            )
            verify_json = None
            if verify.stdout.strip():
                try:
                    verify_json = json.loads(verify.stdout)
                except json.JSONDecodeError as exc:
                    result["errors"].append(f"verify-install output was not JSON: {exc}")
            result["steps"].append(
                {
                    "name": "verify_install",
                    "ok": verify.returncode == 0 and bool(verify_json and verify_json.get("ok") is True),
                    "returncode": verify.returncode,
                    "stdout_tail": verify.stdout[-1000:],
                    "stderr_tail": verify.stderr[-1000:],
                }
            )
            result["verify"] = verify_json
            if verify.returncode != 0 or not verify_json or verify_json.get("ok") is not True:
                result["errors"].append("roundtrip verify-install failed")
                return result

            result["ok"] = True
            return result
    except Exception as exc:
        result["errors"].append(str(exc))
        return result


def create_package(output_dir, verify_roundtrip=False):
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    archive_path = output_root / f"{PACKAGE_DIR_PREFIX}.zip"
    if archive_path.exists():
        archive_path.unlink()

    file_records = []
    for path, relative in iter_package_files(SOURCE_ROOT):
        file_records.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest = {
        "schema": PACKAGE_SCHEMA,
        "version": REPERS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(SOURCE_ROOT.resolve()),
        "source_git_root": str(GIT_STATE_ROOT.resolve()),
        "archive_path": str(archive_path),
        "archive_root": PACKAGE_DIR_PREFIX,
        "source_git": git_source_state(),
        "files": file_records,
        "file_count": len(file_records),
    }

    embedded_readiness = build_readiness_manifest(archive_path, None, file_records)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, relative in iter_package_files(SOURCE_ROOT):
            zf.write(path, f"{PACKAGE_DIR_PREFIX}/{relative}")
        zf.writestr(
            f"{PACKAGE_DIR_PREFIX}/{PACKAGE_MANIFEST_NAME}",
            json.dumps(manifest, indent=2, ensure_ascii=False),
        )
        zf.writestr(
            f"{PACKAGE_DIR_PREFIX}/{PACKAGE_READINESS_NAME}",
            json.dumps(embedded_readiness, indent=2, ensure_ascii=False),
        )

    archive_sha256 = sha256_file(archive_path)
    readiness = build_readiness_manifest(archive_path, archive_sha256, file_records)
    readiness_path = output_root / f"{PACKAGE_DIR_PREFIX}-readiness.json"
    readiness["archive_sha256"] = archive_sha256
    readiness_path.write_text(json.dumps(readiness, indent=2, ensure_ascii=False), encoding="utf-8")

    result = {
        "schema": "repers.package.v1",
        "ok": True and readiness["ok"],
        "archive_path": str(archive_path),
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_sha256": archive_sha256,
        "readiness_path": str(readiness_path),
        "readiness": readiness,
        "manifest": manifest,
    }
    if verify_roundtrip:
        roundtrip = run_roundtrip_verification(archive_path, PACKAGE_DIR_PREFIX)
        result["roundtrip"] = roundtrip
        result["ok"] = result["ok"] and roundtrip["ok"]
    return result


def clean_package(output_dir):
    output_root = Path(output_dir).resolve()
    if output_root.exists():
        shutil.rmtree(output_root)

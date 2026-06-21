import json
import os
import re
import sqlite3
from pathlib import Path


TEXT_SUFFIXES = {".md", ".py", ".js", ".mjs", ".ts", ".tsx", ".json", ".toml", ".yaml", ".yml", ".sh", ".ps1"}
DEFAULT_EXCLUDED_DIRS = {".git", ".repers", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}


def has_excluded_part(path, excluded_dirs=DEFAULT_EXCLUDED_DIRS):
    parts = {part.lower() for part in Path(path).parts}
    return any(part.lower() in parts for part in excluded_dirs)


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def classify_path(path, root):
    rel = Path(path).relative_to(root).as_posix()
    name = Path(path).name.lower()
    parts = set(Path(rel).parts)
    if name in {"readme.md", "contributing.md", "security.md", "code_of_conduct.md"}:
        return "governance_doc"
    if rel.startswith("scripts/") or rel.startswith("bin/"):
        return "script"
    if rel.startswith("hooks/") or ".git/hooks" in rel:
        return "hook"
    if rel.startswith("docs/"):
        return "doc"
    if rel.startswith("templates/"):
        return "template"
    if "repers_tasks" in parts:
        return "task_artifact"
    if name.endswith(".py"):
        return "python_code"
    return "workspace_file"


def extract_summary(text):
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#!"):
            return stripped[:240]
    return ""


def extract_cli_commands(text):
    commands = []
    for match in re.finditer(r"add_parser\(\s*['\"]([^'\"]+)['\"](?:,\s*help=['\"]([^'\"]+)['\"])?", text):
        commands.append({"name": match.group(1), "help": match.group(2) or ""})
    return commands


def iter_documents(root, source, excluded_dirs=DEFAULT_EXCLUDED_DIRS):
    root = Path(root).resolve()
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_dir() or has_excluded_part(path, excluded_dirs):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = read_text(path)
        if not text:
            continue
        kind = classify_path(path, root)
        metadata = {}
        if kind in {"script", "python_code"} and path.suffix.lower() == ".py":
            commands = extract_cli_commands(text)
            if commands:
                metadata["cli_commands"] = commands
        yield {
            "source": source,
            "kind": kind,
            "path": path.relative_to(root).as_posix(),
            "title": path.name,
            "summary": extract_summary(text),
            "text": text,
            "metadata": metadata,
        }


def iter_skill_documents(skills_root):
    skills_path = Path(skills_root).resolve()
    if not skills_path.exists():
        return
    for path in skills_path.rglob("*.md"):
        if has_excluded_part(path):
            continue
        text = read_text(path)
        if not text:
            continue
        skill_name = path.parent.name
        yield {
            "source": "global_skill",
            "kind": "skill_doc",
            "path": path.relative_to(skills_path).as_posix(),
            "title": skill_name,
            "summary": extract_summary(text),
            "text": text,
            "metadata": {"skill": skill_name},
        }


def iter_capability_documents(workspace_root):
    capabilities_path = Path(workspace_root).resolve() / ".repers" / "capabilities" / "registry.json"
    if not capabilities_path.exists():
        return
    try:
        from capability_registry import capability_documents

        yield from capability_documents(capabilities_path)
    except Exception:
        return


def connect(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(conn):
    conn.execute("DROP TABLE IF EXISTS documents")
    conn.execute("DROP TABLE IF EXISTS documents_fts")
    conn.execute(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            text TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE documents_fts USING fts5(
            title,
            summary,
            text,
            content='documents',
            content_rowid='id'
        )
        """
    )


def refresh(db_path, workspace_root, skills_root=None):
    docs = list(iter_documents(workspace_root, "workspace"))
    docs.extend(iter_capability_documents(workspace_root))
    if skills_root:
        docs.extend(iter_skill_documents(skills_root))

    with connect(db_path) as conn:
        init_db(conn)
        for doc in docs:
            cursor = conn.execute(
                """
                INSERT INTO documents(source, kind, path, title, summary, text, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc["source"],
                    doc["kind"],
                    doc["path"],
                    doc["title"],
                    doc["summary"],
                    doc["text"],
                    json.dumps(doc["metadata"], ensure_ascii=False, sort_keys=True),
                ),
            )
            rowid = cursor.lastrowid
            conn.execute(
                "INSERT INTO documents_fts(rowid, title, summary, text) VALUES (?, ?, ?, ?)",
                (rowid, doc["title"], doc["summary"], doc["text"]),
            )
        conn.commit()
    return {"documents_indexed": len(docs), "db_path": str(Path(db_path).resolve())}


def search(db_path, query, limit=20):
    if not Path(db_path).exists():
        return []
    fts_query = build_fts_query(query)
    with connect(db_path) as conn:
        try:
            rows = conn.execute(
                """
                SELECT d.source, d.kind, d.path, d.title, d.summary, d.metadata_json,
                       bm25(documents_fts) AS score
                FROM documents_fts
                JOIN documents d ON d.id = documents_fts.rowid
                WHERE documents_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (fts_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            like_query = f"%{query}%"
            rows = conn.execute(
                """
                SELECT source, kind, path, title, summary, metadata_json, 0.0 AS score
                FROM documents
                WHERE title LIKE ? OR summary LIKE ? OR text LIKE ?
                LIMIT ?
                """,
                (like_query, like_query, like_query, limit),
            ).fetchall()
    results = []
    for source, kind, path, title, summary, metadata_json, score in rows:
        results.append(
            {
                "source": source,
                "kind": kind,
                "path": path,
                "title": title,
                "summary": summary,
                "metadata": json.loads(metadata_json),
                "score": score,
            }
        )
    return results


def build_fts_query(query):
    terms = re.findall(r"[A-Za-z0-9_./-]+", query)
    if not terms:
        return query
    return " OR ".join(f'"{term}"' for term in terms)


def build_research_artifact(db_path, query, workspace_root, skills_root=None, limit=20):
    if not Path(db_path).exists():
        refresh(db_path, workspace_root, skills_root)
    results = search(db_path, query, limit=limit)
    workspace_hits = [r for r in results if r["source"] == "workspace"]
    capability_hits = [r for r in results if r["source"] == "local_capability"]
    skill_hits = [r for r in results if r["source"] == "global_skill"]
    decision = "create"
    if workspace_hits:
        decision = "extend"
    elif capability_hits:
        decision = "reuse"
    elif skill_hits:
        decision = "reuse"
    return {
        "query": query,
        "workspace_root": str(Path(workspace_root).resolve()),
        "index_db": str(Path(db_path).resolve()),
        "counts": {
            "results": len(results),
            "workspace_hits": len(workspace_hits),
            "capability_hits": len(capability_hits),
            "skill_hits": len(skill_hits),
        },
        "results": results,
        "recommendation": {
            "decision": decision,
            "reason": "Workspace matches exist" if workspace_hits else "Reusable local capability matches exist" if capability_hits else "Reusable skill matches exist" if skill_hits else "No matching local capability found",
            "evidence_refs": [f"{r['source']}:{r['path']}" for r in results[:5]],
        },
    }

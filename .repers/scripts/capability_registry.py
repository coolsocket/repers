import json
import re
from pathlib import Path


REGISTRY_SCHEMA = "repers.capability_registry.v1"
QUERY_SCHEMA = "repers.capability_query.v1"
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "capabilities" / "registry.json"
REQUIRED_ENTRY_FIELDS = {"id", "kind", "name", "summary", "tags", "commands", "paths", "verification"}


def load_registry(path=DEFAULT_REGISTRY_PATH):
    registry_path = Path(path)
    if not registry_path.exists():
        return {
            "schema": REGISTRY_SCHEMA,
            "version": "0.1.0",
            "entries": [],
            "_path": str(registry_path.resolve()),
        }
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["_path"] = str(registry_path.resolve())
    return registry


def validate_registry(registry):
    errors = []
    if not isinstance(registry, dict):
        return ["registry root is not an object"]
    if registry.get("schema") != REGISTRY_SCHEMA:
        errors.append(f"unsupported registry schema: {registry.get('schema')}")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        errors.append("entries is not a list")
        return errors
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry {index} is not an object")
            continue
        missing = sorted(REQUIRED_ENTRY_FIELDS - set(entry))
        if missing:
            errors.append(f"entry {index} missing fields: {', '.join(missing)}")
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id:
            errors.append(f"entry {index} id is not a non-empty string")
        elif entry_id in seen:
            errors.append(f"duplicate entry id: {entry_id}")
        else:
            seen.add(entry_id)
        for field in ["tags", "commands", "paths", "verification"]:
            if field in entry and not isinstance(entry[field], list):
                errors.append(f"entry {entry_id or index} field {field} is not a list")
    return errors


def registry_text(entry):
    parts = [
        entry.get("id", ""),
        entry.get("kind", ""),
        entry.get("name", ""),
        entry.get("summary", ""),
        " ".join(entry.get("tags", [])),
        " ".join(entry.get("commands", [])),
        " ".join(entry.get("paths", [])),
        " ".join(entry.get("verification", [])),
    ]
    return "\n".join(part for part in parts if part)


def tokenize(text):
    return [token.lower() for token in re.findall(r"[A-Za-z0-9_.:/-]+", text or "")]


def score_entry(entry, query):
    terms = tokenize(query)
    if not terms:
        return 0
    entry_text = registry_text(entry).lower()
    score = 0
    tags = {tag.lower() for tag in entry.get("tags", [])}
    name = entry.get("name", "").lower()
    entry_id = entry.get("id", "").lower()
    commands = " ".join(entry.get("commands", [])).lower()
    paths = " ".join(entry.get("paths", [])).lower()
    for term in terms:
        if term == entry_id:
            score += 10
        if term in tags:
            score += 8
        if term in name:
            score += 5
        if term in commands:
            score += 4
        if term in paths:
            score += 3
        if term in entry_text:
            score += 1
    return score


def search_registry(query, limit=20, path=DEFAULT_REGISTRY_PATH):
    registry = load_registry(path)
    errors = validate_registry(registry)
    entries = []
    if not errors:
        for entry in registry.get("entries", []):
            score = score_entry(entry, query)
            if score > 0 or not query:
                item = dict(entry)
                item["score"] = score
                entries.append(item)
        entries.sort(key=lambda item: (-item["score"], item["id"]))
        entries = entries[: max(1, int(limit))]
    return {
        "schema": QUERY_SCHEMA,
        "ok": not errors,
        "registry_path": registry.get("_path"),
        "query": query,
        "count": len(entries),
        "errors": errors,
        "entries": entries,
    }


def capability_documents(path=DEFAULT_REGISTRY_PATH):
    registry = load_registry(path)
    if validate_registry(registry):
        return []
    docs = []
    for entry in registry.get("entries", []):
        docs.append(
            {
                "source": "local_capability",
                "kind": entry.get("kind", "capability"),
                "path": f"capabilities/registry.json#{entry.get('id')}",
                "title": entry.get("name") or entry.get("id"),
                "summary": entry.get("summary", ""),
                "text": registry_text(entry),
                "metadata": {
                    "capability_id": entry.get("id"),
                    "tags": entry.get("tags", []),
                    "commands": entry.get("commands", []),
                    "paths": entry.get("paths", []),
                    "verification": entry.get("verification", []),
                },
            }
        )
    return docs


def validate_command(path=DEFAULT_REGISTRY_PATH):
    registry = load_registry(path)
    errors = validate_registry(registry)
    return {
        "schema": "repers.capability_registry_validation.v1",
        "ok": not errors,
        "registry_path": registry.get("_path"),
        "entry_count": len(registry.get("entries", [])) if isinstance(registry, dict) else 0,
        "errors": errors,
    }

"""Repository-wide validation for Mythopraxis content."""

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from mythopraxis.interventions import InterventionError, load_intervention


REQUIRED_SCHEMA_FILES = {
    "intervention.schema.json",
    "library-entry.schema.json",
    "claim.schema.json",
    "eval-result.schema.json",
}


def validate_instance(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Return stable JSON Schema errors for an in-memory instance."""
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path))]


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def find_broken_local_links(markdown_path: Path, root: Path) -> list[str]:
    """Return repository-relative Markdown and HTML links that do not exist."""
    text = markdown_path.read_text(encoding="utf-8")
    targets = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text)
    targets.extend(re.findall(r"(?:src|href)=\"([^\"]+)\"", text))
    broken: list[str] = []
    for raw_target in targets:
        target = raw_target.strip().split()[0]
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        local = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if local and not (root / local).exists():
            broken.append(target)
    return sorted(set(broken))


def validate_repository(root: Path) -> list[str]:
    """Return human-readable contract errors, or an empty list when valid."""
    errors: list[str] = []
    skill = root / "skills" / "mythopraxis" / "SKILL.md"
    if not skill.exists():
        errors.append("missing skills/mythopraxis/SKILL.md")
    elif "TODO" in skill.read_text(encoding="utf-8"):
        errors.append("skills/mythopraxis/SKILL.md contains a placeholder")
    schema_dir = root / "schemas"
    found_schemas = {path.name for path in schema_dir.glob("*.json")} if schema_dir.exists() else set()
    for missing in sorted(REQUIRED_SCHEMA_FILES - found_schemas):
        errors.append(f"missing schemas/{missing}")
    exemplar_dir = root / "skills" / "mythopraxis" / "references" / "exemplars"
    exemplars = sorted(exemplar_dir.glob("*.yaml")) if exemplar_dir.exists() else []
    if len(exemplars) != 6:
        errors.append(f"expected 6 exemplars, found {len(exemplars)}")
    schemas: dict[str, dict[str, Any]] = {}
    for name in sorted(found_schemas):
        try:
            schemas[name] = json.loads((schema_dir / name).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            errors.append(f"schemas/{name}: {error}")

    exemplar_documents: list[tuple[Path, dict[str, Any]]] = []
    for path in exemplars:
        try:
            document = load_intervention(path)
            exemplar_documents.append((path, document))
            for error in validate_instance(document, schemas.get("intervention.schema.json", {})):
                errors.append(f"{path.relative_to(root)}: {error}")
        except (InterventionError, yaml.YAMLError) as error:
            errors.append(f"{path.relative_to(root)}: {error}")

    corpus_dir = root / "skills" / "mythopraxis" / "references" / "corpus"
    corpus_ids: set[str] = set()
    for path in sorted(corpus_dir.glob("*.yaml")) if corpus_dir.exists() else []:
        try:
            document = _load_yaml(path)
            for error in validate_instance(document, schemas.get("library-entry.schema.json", {})):
                errors.append(f"{path.relative_to(root)}: {error}")
            if isinstance(document, dict) and document.get("id"):
                if document["id"] in corpus_ids:
                    errors.append(f"duplicate corpus id: {document['id']}")
                corpus_ids.add(document["id"])
        except yaml.YAMLError as error:
            errors.append(f"{path.relative_to(root)}: {error}")

    claims_dir = root / "research" / "claims"
    claim_ids: set[str] = set()
    for path in sorted(claims_dir.glob("*.yaml")) if claims_dir.exists() else []:
        try:
            document = _load_yaml(path)
            for error in validate_instance(document, schemas.get("claim.schema.json", {})):
                errors.append(f"{path.relative_to(root)}: {error}")
            if isinstance(document, dict) and document.get("id"):
                if document["id"] in claim_ids:
                    errors.append(f"duplicate claim id: {document['id']}")
                claim_ids.add(document["id"])
        except yaml.YAMLError as error:
            errors.append(f"{path.relative_to(root)}: {error}")

    for path, document in exemplar_documents:
        for source_id in document.get("sources", []):
            if source_id not in corpus_ids:
                errors.append(f"{path.relative_to(root)}: unknown source {source_id}")
        for claim_id in document.get("claims", []):
            if claim_id not in claim_ids:
                errors.append(f"{path.relative_to(root)}: unknown claim {claim_id}")
    readme = root / "README.md"
    if not readme.exists():
        errors.append("missing README.md")
    elif "\u2014" in readme.read_text(encoding="utf-8"):
        errors.append("README.md contains an em dash")
    else:
        for target in find_broken_local_links(readme, root):
            errors.append(f"README.md has a broken local link: {target}")
    return errors

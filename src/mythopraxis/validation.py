"""Validate repository content against trusted, offline contracts."""
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from mythopraxis.contracts import load_contract, validate_instance
from mythopraxis.cases import load_case
from mythopraxis.inputs import content_path, load_yaml, read_text
from mythopraxis.interventions import load_intervention

REQUIRED_SCHEMA_FILES = {
    "intervention.schema.json", "library-entry.schema.json",
    "claim.schema.json", "eval-result.schema.json", "case.schema.json",
}


def find_broken_local_links(markdown_path: Path, root: Path) -> list[str]:
    text = read_text(markdown_path)
    targets = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text)
    targets.extend(re.findall(r'(?:src|href)="([^"]+)"', text))
    broken = []
    for raw in targets:
        parts = raw.strip().split()
        if not parts:
            continue
        target = parts[0]
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        local = unquote(target.split("#", 1)[0].split("?", 1)[0])
        try:
            if local and not content_path(root, Path(local)).exists():
                broken.append(target)
        except ValueError:
            broken.append(target)
    return sorted(set(broken))


def validate_repository(root: Path) -> list[str]:
    """Check supplied files without trusting schemas from the supplied tree."""
    root = root.resolve()
    errors = []
    try:
        skill = content_path(root, Path("skills/mythopraxis/SKILL.md"))
        if "TODO" in read_text(skill):
            errors.append("skills/mythopraxis/SKILL.md contains a placeholder")
    except (OSError, ValueError) as error:
        errors.append(f"skills/mythopraxis/SKILL.md: {error}")

    contracts = {name: load_contract(name) for name in REQUIRED_SCHEMA_FILES}
    for name, contract in sorted(contracts.items()):
        try:
            path = content_path(root, Path("schemas") / name)
            if json.loads(read_text(path)) != contract:
                errors.append(f"schemas/{name}: differs from the trusted packaged contract")
        except (OSError, ValueError) as error:
            errors.append(f"schemas/{name}: {error}")

    groups = (
        ("skills/mythopraxis/references/exemplars", "intervention.schema.json"),
        ("skills/mythopraxis/references/corpus", "library-entry.schema.json"),
        ("research/claims", "claim.schema.json"),
    )
    documents: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    ids: dict[str, set[str]] = {}
    for directory, schema_name in groups:
        documents[schema_name] = []
        ids[schema_name] = set()
        try:
            folder = content_path(root, Path(directory))
            paths = sorted(folder.glob("*.yaml"))
            if schema_name == "intervention.schema.json" and len(paths) != 6:
                errors.append(f"expected 6 exemplars, found {len(paths)}")
        except (OSError, ValueError) as error:
            errors.append(f"{directory}: {error}")
            continue
        for path in paths:
            relative = Path(directory) / path.name
            try:
                safe_path = content_path(root, relative)
                document = load_intervention(safe_path) if schema_name == "intervention.schema.json" else load_yaml(safe_path)
                issues = validate_instance(document, contracts[schema_name])
                errors.extend(f"{relative}: {issue}" for issue in issues)
                if issues:
                    continue
                identifier = document["id"]
                if identifier in ids[schema_name]:
                    errors.append(f"{relative}: duplicate id {identifier}")
                ids[schema_name].add(identifier)
                documents[schema_name].append((relative, document))
            except (OSError, ValueError) as error:
                errors.append(f"{relative}: {error}")
    for path, document in documents["intervention.schema.json"]:
        for source in document["sources"]:
            if source not in ids["library-entry.schema.json"]:
                errors.append(f"{path}: unknown source {source}")
        for claim in document["claims"]:
            if claim not in ids["claim.schema.json"]:
                errors.append(f"{path}: unknown claim {claim}")
    try:
        examples = content_path(root, Path("cases/examples"))
        for path in sorted(examples.glob("*.yaml")):
            relative = path.relative_to(root)
            try:
                case = load_case(content_path(root, relative))
                errors.extend(
                    f"{relative}: {issue}"
                    for issue in validate_instance(case, contracts["case.schema.json"])
                )
            except (OSError, ValueError) as error:
                errors.append(f"{relative}: {error}")
    except (OSError, ValueError) as error:
        errors.append(f"cases/examples: {error}")
    try:
        readme = content_path(root, Path("README.md"))
        if "\u2014" in read_text(readme):
            errors.append("README.md contains an em dash")
        for target in find_broken_local_links(readme, root):
            errors.append(f"README.md has a broken local link: {target}")
    except (OSError, ValueError) as error:
        errors.append(f"README.md: {error}")
    return errors

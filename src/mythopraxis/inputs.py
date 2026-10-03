"""Bounded local inputs and repository-contained content paths."""
import re
from pathlib import Path
from typing import Any

import yaml

MAX_INPUT_BYTES = 1024 * 1024
MAX_PROMPT_CHARS = 32768
MAX_TOTAL_PROMPT_CHARS = 2_000_000
DEFAULT_MAX_RUNS = 1000
HARD_MAX_RUNS = 10000
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class _BoundedSafeLoader(yaml.SafeLoader):
    """Reject alias expansion and excessive structures before construction."""

    def __init__(self, stream: str):
        super().__init__(stream)
        self.node_count = 0
        self.depth = 0

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ValueError("YAML aliases are not supported")
        self.node_count += 1
        self.depth += 1
        try:
            if self.node_count > 10000 or self.depth > 64:
                raise ValueError("YAML exceeds the node or nesting limit")
            return super().compose_node(parent, index)
        finally:
            self.depth -= 1


def read_text(path: Path) -> str:
    """Read at most one MiB; reject oversized inputs before parsing."""
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    return data.decode("utf-8")


def load_yaml(path: Path) -> Any:
    """Load bounded YAML without aliases, arbitrary tags, or deep nesting."""
    try:
        loader = _BoundedSafeLoader(read_text(path))
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()
    except (yaml.YAMLError, RecursionError) as error:
        raise ValueError("invalid or excessively nested YAML") from error


def content_path(root: Path, relative: Path) -> Path:
    """Reject paths or symlinks resolving outside the supplied repository."""
    base = root.resolve()
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError("content path must remain inside the repository")
    return resolved


def named_yaml(root: Path, directory: str, identifier: str) -> Path:
    """Resolve an identifier within its expected content folder."""
    if not isinstance(identifier, str) or not SLUG.fullmatch(identifier):
        raise ValueError("content identifier must be a lowercase hyphenated slug")
    base = content_path(root, Path(directory))
    path = content_path(root, Path(directory) / f"{identifier}.yaml")
    if not path.is_relative_to(base):
        raise ValueError("content path must remain inside its expected folder")
    return path


def validate_run_limit(max_runs: int) -> None:
    if type(max_runs) is not int or not 1 <= max_runs <= HARD_MAX_RUNS:
        raise ValueError(f"max_runs must be an integer from 1 to {HARD_MAX_RUNS}")


def create_private_parents(path: Path) -> None:
    """Create every missing parent privately; leave existing modes untouched."""
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)

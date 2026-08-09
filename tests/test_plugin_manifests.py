import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_codex_plugin_points_to_portable_skills() -> None:
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "mythopraxis"
    assert manifest["skills"] == "./skills/"
    assert manifest["interface"]["displayName"] == "Mythopraxis"


def test_claude_plugin_has_matching_identity() -> None:
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "mythopraxis"
    assert manifest["version"] == "0.1.0-alpha.1"
    assert manifest["license"] == "MIT"


def test_claude_marketplace_installs_plugin_from_repository_root() -> None:
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert marketplace["name"] == "mythopraxis"
    assert marketplace["plugins"][0]["name"] == "mythopraxis"
    assert marketplace["plugins"][0]["source"] == "./"

import struct
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hero_is_wide_and_under_size_budget() -> None:
    hero = ROOT / "assets" / "readme" / "the-thread-through-the-storm.png"
    with hero.open("rb") as stream:
        assert stream.read(8) == b"\x89PNG\r\n\x1a\n"
        stream.read(8)
        width, height = struct.unpack(">II", stream.read(8))
    assert width / height > 1.7
    assert hero.stat().st_size < 2_500_000


def test_concept_map_has_accessible_metadata() -> None:
    concept_map = ROOT / "assets" / "readme" / "character-under-pressure.svg"
    root = ET.parse(concept_map).getroot()
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    title = root.find("svg:title", namespace)
    description = root.find("svg:desc", namespace)
    assert title is not None and title.text == "A Map of Character Under Pressure"
    assert description is not None and "Assistant anchor" in (description.text or "")

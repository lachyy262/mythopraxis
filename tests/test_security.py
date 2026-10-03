"""Security regressions use temporary fixtures and never make live provider calls."""
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
import yaml

from mythopraxis.cli import main
from mythopraxis.evaluations import expand_matrix
from mythopraxis.interventions import InterventionError, load_intervention
from mythopraxis.prompts import build_prompt
from mythopraxis.providers import call_provider
from mythopraxis.runner import resolve_model_placeholders, run_evaluations
from mythopraxis.validation import validate_instance, validate_repository

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def content_root(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    return root


def test_external_schema_reference_never_opens_a_url(monkeypatch):
    opened = []
    def forbidden_open(*args, **kwargs):
        opened.append(args)
        raise OSError("network must not be used")
    monkeypatch.setattr("urllib.request.urlopen", forbidden_open)
    errors = validate_instance({}, {"$ref": "https://example.invalid/schema"})
    assert errors
    assert opened == []


def test_file_schema_reference_does_not_disclose_local_content(tmp_path):
    private = tmp_path / "private.json"
    private.write_text(json.dumps({"const": "PRIVATE_MARKER"}))
    errors = validate_instance("other", {"$ref": private.as_uri()})
    assert errors
    assert "PRIVATE_MARKER" not in str(errors)


def test_repository_cannot_weaken_trusted_contract(content_root):
    (content_root / "schemas/intervention.schema.json").write_text("{}")
    path = content_root / "skills/mythopraxis/references/exemplars/honest-mirror.yaml"
    data = yaml.safe_load(path.read_text())
    data["assistant_anchor"] = ""
    path.write_text(yaml.safe_dump(data))
    assert validate_repository(content_root)


@pytest.mark.parametrize("kind", ["traversal", "absolute", "symlink"])
def test_scenario_cannot_escape_root(content_root, tmp_path, kind):
    private = tmp_path / "private.yaml"
    private.write_text(yaml.safe_dump({"task": "PRIVATE_MARKER", "pressure": "test", "exemplar": "honest-mirror"}))
    identifier = {"traversal": "../../../private", "absolute": str(private.with_suffix("")), "symlink": "linked"}[kind]
    if kind == "symlink":
        (content_root / "evals/scenarios/linked.yaml").symlink_to(private)
    with pytest.raises(ValueError):
        build_prompt(content_root, {"scenario": identifier, "condition": "plain-instruction"})


def test_exemplar_cannot_escape_root(content_root, tmp_path):
    private = tmp_path / "private.yaml"
    shutil.copy(content_root / "skills/mythopraxis/references/exemplars/honest-mirror.yaml", private)
    scenario = content_root / "evals/scenarios/code-review.yaml"
    data = yaml.safe_load(scenario.read_text()); data["exemplar"] = "../../../../../private"
    scenario.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError):
        build_prompt(content_root, {"scenario": "code-review", "condition": "plain-instruction"})


@pytest.mark.parametrize("field,value", [("assistant_anchor", ""), ("exit_cue", ""), ("postures", [])])
def test_runtime_rejects_incomplete_contract(tmp_path, field, value):
    data = yaml.safe_load((ROOT / "skills/mythopraxis/references/exemplars/honest-mirror.yaml").read_text())
    data[field] = value
    path = tmp_path / "bad.yaml"; path.write_text(yaml.safe_dump(data))
    with pytest.raises(InterventionError):
        load_intervention(path)


@pytest.mark.parametrize("repeats", [10001, True, "3", 1.5])
def test_matrix_rejects_unsafe_repeat_counts(repeats):
    with pytest.raises(ValueError):
        expand_matrix({"models": ["openai:test"], "conditions": ["plain-instruction"], "scenarios": ["code-review"], "repeats": repeats})


def test_matrix_checks_product_before_allocating():
    with pytest.raises(ValueError):
        expand_matrix({"models": ["openai:test"] * 100, "conditions": ["plain-instruction"] * 100, "scenarios": ["code-review"], "repeats": 2})


def test_oversized_yaml_is_rejected(tmp_path):
    path = tmp_path / "large.yaml"; path.write_text("models: [openai:test]\nconditions: [plain-instruction]\nscenarios: [code-review]\nrepeats: 1\n#" + "x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError):
        main(["eval", "--matrix", str(path), "--dry-run"])


def test_only_model_configuration_environment_names_are_allowed(monkeypatch):
    monkeypatch.setenv("FAKE_PRIVATE_VALUE", "openai:private")
    with pytest.raises(ValueError):
        resolve_model_placeholders(["${FAKE_PRIVATE_VALUE}"])


RUN = {"model": "openai:test", "condition": "plain-instruction", "scenario": "code-review", "seed": 1}


def test_all_prompts_are_validated_before_any_provider_call(tmp_path):
    calls = []
    def factory(run):
        if run["seed"] == 2:
            raise ValueError("invalid second fixture")
        return "valid first fixture"
    output = tmp_path / "results.jsonl"
    with pytest.raises(ValueError):
        run_evaluations([RUN, {**RUN, "seed": 2}], factory, lambda *args: calls.append(args), output)
    assert calls == []
    assert not output.exists()


def test_existing_output_survives_invalid_input(tmp_path):
    output = tmp_path / "results.jsonl"; output.write_text("original")
    def factory(run):
        raise ValueError("invalid input")
    with pytest.raises(ValueError):
        run_evaluations([RUN], factory, lambda *args: "response", output)
    assert output.read_text() == "original"


@pytest.mark.parametrize("symlink", [False, True])
def test_existing_output_is_never_overwritten(tmp_path, symlink):
    target = tmp_path / "target"; target.write_text("original")
    output = tmp_path / "results.jsonl"
    if symlink:
        output.symlink_to(target)
    else:
        output.write_text("original")
    calls = []
    with pytest.raises(FileExistsError):
        run_evaluations([RUN], lambda run: "prompt", lambda *args: calls.append(args), output)
    assert calls == []
    assert target.read_text() == "original"
    assert output.read_text() == "original"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
def test_result_file_is_private_even_with_permissive_umask(tmp_path):
    output = tmp_path / "new/results.jsonl"
    previous = os.umask(0)
    try:
        run_evaluations([RUN], lambda run: "prompt", lambda *args: "response", output)
    finally:
        os.umask(previous)
    assert output.stat().st_mode & 0o777 == 0o600
    assert output.parent.stat().st_mode & 0o777 == 0o700


def test_runner_rejects_excessive_prompt_before_call(tmp_path):
    calls = []
    with pytest.raises(ValueError):
        run_evaluations([RUN], lambda run: "x" * 100000, lambda *args: calls.append(args), tmp_path / "out")
    assert calls == []


def test_openai_has_an_output_token_limit(monkeypatch):
    requests = []
    def create(**kwargs):
        requests.append(kwargs); return SimpleNamespace(output_text="ok")
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: client))
    assert call_provider("openai:test", "prompt", 1) == "ok"
    assert 0 < requests[0]["max_output_tokens"] <= 2048


@pytest.mark.parametrize("field", ["condition", "scenario"])
def test_missing_run_metadata_is_rejected_before_call(tmp_path, field):
    run = dict(RUN); del run[field]
    calls = []
    with pytest.raises(ValueError):
        run_evaluations([run], lambda run: "prompt", lambda *args: calls.append(args), tmp_path / "out")
    assert calls == []
    assert not (tmp_path / "out").exists()


def test_runner_stops_reading_over_limit_iterator(tmp_path):
    consumed = []
    def runs():
        for i in range(10000):
            consumed.append(i)
            yield RUN
    with pytest.raises(ValueError):
        run_evaluations(runs(), lambda run: "prompt", lambda *args: "response", tmp_path / "out", max_runs=2)
    assert consumed == [0, 1, 2]
    assert not (tmp_path / "out").exists()


def test_combined_prompt_budget_is_checked_before_call(tmp_path):
    calls = []
    with pytest.raises(ValueError):
        run_evaluations([RUN] * 100, lambda run: "x" * 30000, lambda *args: calls.append(args), tmp_path / "out")
    assert calls == []
    assert not (tmp_path / "out").exists()


def test_yaml_merge_aliases_are_rejected_before_expansion(tmp_path):
    from mythopraxis.inputs import load_yaml
    path = tmp_path / "aliases.yaml"
    path.write_text("a: &a {x: 1}\nb: &b {<<: [*a, *a]}\nc: {<<: [*b, *b]}\n")
    with pytest.raises(ValueError, match="aliases"):
        load_yaml(path)


def test_yaml_nesting_is_bounded(tmp_path):
    from mythopraxis.inputs import load_yaml
    path = tmp_path / "deep.yaml"; path.write_text("[" * 100 + "0" + "]" * 100)
    with pytest.raises(ValueError):
        load_yaml(path)


def test_yaml_node_count_is_bounded(tmp_path):
    from mythopraxis.inputs import load_yaml
    path = tmp_path / "wide.yaml"; path.write_text("- x\n" * 10001)
    with pytest.raises(ValueError):
        load_yaml(path)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
def test_all_new_result_parent_directories_are_private(tmp_path):
    output = tmp_path / "a/b/c/results.jsonl"
    previous = os.umask(0)
    try:
        run_evaluations([RUN], lambda run: "prompt", lambda *args: "response", output)
    finally:
        os.umask(previous)
    for name in ("a", "a/b", "a/b/c"):
        assert (tmp_path / name).stat().st_mode & 0o777 == 0o700

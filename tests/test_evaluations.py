from mythopraxis.evaluations import expand_matrix


def test_expand_matrix_builds_180_pilot_runs() -> None:
    matrix = {
        "conditions": [
            "plain-instruction",
            "generic-expert-persona",
            "sustained-story-persona",
            "anchored-third-person-witness",
            "bounded-first-person-rehearsal",
        ],
        "scenarios": [
            "customer-support",
            "requirements",
            "debugging",
            "code-review",
            "design-critique",
            "incident-response",
        ],
        "models": ["provider-a/model", "provider-b/model"],
        "repeats": 3,
    }

    runs = expand_matrix(matrix)

    assert len(runs) == 180
    assert runs[0]["seed"] == 1
    assert runs[-1]["seed"] == 3
    assert {run["condition"] for run in runs} == set(matrix["conditions"])


def test_expand_matrix_requires_explicit_models() -> None:
    matrix = {"conditions": ["plain"], "scenarios": ["support"], "repeats": 1}

    try:
        expand_matrix(matrix)
    except ValueError as error:
        assert "models" in str(error)
    else:
        raise AssertionError("matrix without explicit models must be rejected")

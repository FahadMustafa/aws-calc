"""Schema + semantic validation of the saveAs body, before it ever hits the network.

A malformed body is accepted by the save endpoint and only fails later, in the
recipient's browser, where nobody can fix it. These tests pin the failure to the
moment we can still do something about it.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "references" / "examples"
SAMPLE = EXAMPLES / "sample-saveas-body.json"
GROUPS = EXAMPLES / "groups-example-body.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.fixture
def sample() -> dict:
    return load(SAMPLE)


@pytest.fixture
def groups() -> dict:
    return load(GROUPS)


def first_service_key(body: dict) -> str:
    return next(iter(body["services"]))


# --- happy path -------------------------------------------------------------


def test_sample_body_validates(sample):
    from validate_body import validate

    assert validate(sample) == []


def test_groups_example_validates(groups):
    from validate_body import validate

    assert validate(groups) == []


def test_group_line_item_without_region_name_is_allowed(sample):
    """Sub-services inside subServices legitimately omit regionName/serviceName."""
    from validate_body import validate

    for item in sample["services"].values():
        for sub in item.get("subServices", []):
            assert "regionName" not in sub or "serviceName" not in sub
    assert validate(sample) == []


# --- schema failures --------------------------------------------------------


def test_sub_services_as_object_is_rejected(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    key = next(k for k, v in body["services"].items() if "subServices" in v)
    body["services"][key]["subServices"] = {"0": body["services"][key]["subServices"][0]}

    errors = validate(body)
    assert errors, "object-shaped subServices must be rejected"
    assert any("array" in e for e in errors), errors


def test_both_component_shapes_is_rejected(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    key = first_service_key(body)
    body["services"][key]["subServices"] = []

    errors = validate(body)
    assert any("exactly one of" in e for e in errors), errors


def test_neither_component_shape_is_rejected(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    key = first_service_key(body)
    del body["services"][key]["calculationComponents"]

    errors = validate(body)
    assert any("exactly one of" in e for e in errors), errors


def test_errors_stay_readable(sample):
    """No error line may dump the whole failing line item."""
    from validate_body import validate

    body = copy.deepcopy(sample)
    key = first_service_key(body)
    body["services"][key]["subServices"] = {"0": {}}

    errors = validate(body)
    assert errors
    assert all(len(e) < 400 for e in errors), errors


def test_missing_estimate_for_is_rejected(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    key = first_service_key(body)
    del body["services"][key]["estimateFor"]

    errors = validate(body)
    assert any("estimateFor" in e for e in errors), errors


def test_missing_top_level_key_is_rejected(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    del body["metaData"]

    errors = validate(body)
    assert any("metaData" in e for e in errors), errors


def test_bad_version_format_is_rejected(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    body["services"][first_service_key(body)]["version"] = "0.68"

    errors = validate(body)
    assert any("version" in e for e in errors), errors


def test_non_numeric_monthly_is_rejected(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    body["services"][first_service_key(body)]["serviceCost"]["monthly"] = "68.62"

    errors = validate(body)
    assert any("monthly" in e for e in errors), errors


def test_upfront_is_optional_on_service_cost(sample):
    """VPC's captured line carries monthly only — that must stay valid."""
    from validate_body import validate

    body = copy.deepcopy(sample)
    body["services"][first_service_key(body)]["serviceCost"].pop("upfront", None)

    assert validate(body) == []


def test_upfront_is_optional_on_group_subtotal(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    body["groupSubtotal"].pop("upfront", None)

    assert validate(body) == []


def test_additional_properties_are_allowed(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    body["someFieldTheSpaAdded"] = {"whatever": True}
    body["services"][first_service_key(body)]["futureField"] = 1

    assert validate(body) == []


def test_errors_include_a_path(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    key = first_service_key(body)
    del body["services"][key]["estimateFor"]

    errors = validate(body)
    assert any(key in e for e in errors), errors


# --- semantic rules ---------------------------------------------------------


def test_service_key_service_code_mismatch_is_rejected(sample):
    from validate_body import validate

    body = copy.deepcopy(sample)
    key = first_service_key(body)
    body["services"]["notTheCode-1234"] = body["services"].pop(key)

    errors = validate(body)
    assert any("serviceCode" in e for e in errors), errors


def test_group_key_name_mismatch_is_rejected(groups):
    from validate_body import validate

    body = copy.deepcopy(groups)
    key = next(iter(body["groups"]))
    body["groups"][key]["name"] = "Renamed"

    errors = validate(body)
    assert any("name" in e for e in errors), errors


# --- CLI --------------------------------------------------------------------


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_body.py"), *args],
        capture_output=True,
        text=True,
    )


def test_cli_help_exits_zero():
    assert run_cli("--help").returncode == 0


def test_cli_accepts_sample_body():
    result = run_cli(str(SAMPLE))
    assert result.returncode == 0, result.stderr


def test_cli_rejects_broken_body(tmp_path, sample):
    body = copy.deepcopy(sample)
    del body["services"][first_service_key(body)]["estimateFor"]
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(body))

    result = run_cli(str(path))
    assert result.returncode == 1
    assert "estimateFor" in (result.stdout + result.stderr)


# --- the pre-POST gate in create_estimate ----------------------------------


def test_create_estimate_exits_2_on_invalid_body(tmp_path, sample, monkeypatch, capsys):
    import create_estimate

    def boom(*a, **kw):  # pragma: no cover - must never run
        raise AssertionError("POST attempted with an invalid body")

    monkeypatch.setattr(create_estimate.requests, "post", boom)

    body = copy.deepcopy(sample)
    del body["services"][first_service_key(body)]["estimateFor"]
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(body))

    assert create_estimate.main(["create_estimate.py", str(path)]) == 2
    assert "estimateFor" in capsys.readouterr().err


def test_create_estimate_no_validate_skips_the_gate(tmp_path, sample, monkeypatch):
    import create_estimate

    posted = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"statusCode": 201, "body": json.dumps({"savedKey": "abc123"})}

    def fake_post(url, json=None, headers=None, timeout=None):
        posted["body"] = json
        return FakeResponse()

    monkeypatch.setattr(create_estimate.requests, "post", fake_post)

    body = copy.deepcopy(sample)
    del body["services"][first_service_key(body)]["estimateFor"]
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(body))

    assert create_estimate.main(["create_estimate.py", "--no-validate", str(path)]) == 0
    assert posted["body"] is not None


def test_create_estimate_help_still_exits_zero():
    import create_estimate

    assert create_estimate.main(["create_estimate.py", "--help"]) == 0


def test_create_estimate_stamps_created_on_before_validating(tmp_path, sample, monkeypatch):
    """A body missing metaData.createdOn is stamped by main() before validate()
    runs, so it isn't rejected for a field the script itself would fill in."""
    import create_estimate

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"statusCode": 201, "body": json.dumps({"savedKey": "abc123"})}

    def fake_post(url, json=None, headers=None, timeout=None):
        return FakeResponse()

    monkeypatch.setattr(create_estimate.requests, "post", fake_post)

    body = copy.deepcopy(sample)
    del body["metaData"]["createdOn"]
    path = tmp_path / "no-created-on.json"
    path.write_text(json.dumps(body))

    assert create_estimate.main(["create_estimate.py", str(path)]) == 0

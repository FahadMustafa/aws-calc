"""Every file in references/fixtures/ is a full lineItem, ground-truth-verified.

Fixtures are per-service extracts of the top-level line items already present
in references/examples/*.json (split out for use as a compact ground-truth
reference, distinct from the two full example bodies).
"""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "references" / "fixtures"
SCHEMA_PATH = REPO_ROOT / "scripts" / "body_schema.json"

FIXTURE_PATHS = sorted(FIXTURES_DIR.glob("*.json"))


def load_line_item_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text())
    line_item_schema = {"$ref": "#/$defs/lineItem", "$defs": schema["$defs"]}
    return Draft202012Validator(line_item_schema)


def test_fixtures_directory_is_not_empty():
    assert FIXTURE_PATHS, "references/fixtures/ must contain at least one fixture"


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_fixture_validates_as_a_line_item(path):
    validator = load_line_item_validator()
    body = json.loads(path.read_text())

    errors = sorted(validator.iter_errors(body), key=lambda e: list(e.absolute_path))
    assert not errors, [e.message for e in errors]


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_fixture_filename_matches_its_serviceCode(path):
    body = json.loads(path.read_text())
    code = body["serviceCode"]
    assert path.stem == code or path.stem.startswith(f"{code}-")

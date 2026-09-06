"""compute_totals: bottom-up groupSubtotal / totalCost per references/body-schema.md."""
import copy
import json
from pathlib import Path

import pytest

from body_math import compute_totals

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "references" / "examples"


def _line(monthly, upfront=0):
    return {"serviceCost": {"monthly": monthly, "upfront": upfront}}


@pytest.fixture
def nested_body():
    """One ungrouped line + a group two levels deep."""
    return {
        "services": {
            # 1.234 -> 1.23; unambiguous at 2dp (no .xx5 float tie)
            "ec2Enhancement-flat": _line(1.234, 100.0),
        },
        "groups": {
            "Outer-1111": {
                "name": "Outer",
                "services": {"amazonMQ-outer": _line(2.5, 10.0)},
                "groups": {
                    "Inner-2222": {
                        "name": "Inner",
                        "services": {"amazonS3-inner": _line(3.25, 5.0)},
                        "groups": {},
                    }
                },
            }
        },
    }


def test_group_subtotal_excludes_grouped_lines(nested_body):
    out = compute_totals(nested_body)
    # top-level groupSubtotal counts ONLY body.services, not anything in groups
    assert out["groupSubtotal"]["monthly"] == pytest.approx(1.23)
    # the leaf group's own subtotal covers only its immediate services
    inner = out["groups"]["Outer-1111"]["groups"]["Inner-2222"]
    assert inner["groupSubtotal"]["monthly"] == pytest.approx(3.25)
    outer = out["groups"]["Outer-1111"]
    assert outer["groupSubtotal"]["monthly"] == pytest.approx(2.5)


def test_total_cost_recurses(nested_body):
    out = compute_totals(nested_body)
    inner = out["groups"]["Outer-1111"]["groups"]["Inner-2222"]
    outer = out["groups"]["Outer-1111"]
    assert inner["totalCost"]["monthly"] == pytest.approx(3.25)
    # parent = own subtotal + child totals
    assert outer["totalCost"]["monthly"] == pytest.approx(2.5 + 3.25)
    # body = top-level subtotal + all top-level group totals
    assert out["totalCost"]["monthly"] == pytest.approx(1.23 + 5.75)


def test_upfront_is_summed(nested_body):
    out = compute_totals(nested_body)
    inner = out["groups"]["Outer-1111"]["groups"]["Inner-2222"]
    outer = out["groups"]["Outer-1111"]
    assert inner["totalCost"]["upfront"] == pytest.approx(5.0)
    assert outer["totalCost"]["upfront"] == pytest.approx(15.0)
    assert out["totalCost"]["upfront"] == pytest.approx(115.0)


def test_line_items_rounded_to_2dp(nested_body):
    out = compute_totals(nested_body)
    assert out["services"]["ec2Enhancement-flat"]["serviceCost"]["monthly"] == 1.23


def test_input_body_not_mutated(nested_body):
    before = copy.deepcopy(nested_body)
    compute_totals(nested_body)
    assert nested_body == before


def test_group_service_cost_sums_sub_services():
    body = {
        "services": {
            "amazonSimpleStorageServiceGroup-1": {
                "subServices": [_line(10.004), _line(12.996)],
                "serviceCost": {"monthly": 0, "upfront": 0},
            }
        },
        "groups": {},
    }
    out = compute_totals(body)
    # sub-services round first (10.00 + 13.00), then the parent line sums them
    assert out["services"]["amazonSimpleStorageServiceGroup-1"]["serviceCost"][
        "monthly"
    ] == pytest.approx(23.0)
    assert out["totalCost"]["monthly"] == pytest.approx(23.0)


@pytest.mark.parametrize(
    "fname", ["sample-saveas-body.json", "groups-example-body.json"]
)
def test_captured_examples_reconcile(fname):
    body = json.loads((EXAMPLES / fname).read_text())
    recomputed = compute_totals(body)
    assert recomputed["totalCost"]["monthly"] == pytest.approx(
        body["totalCost"]["monthly"], abs=0.01
    )
    assert recomputed["groupSubtotal"]["monthly"] == pytest.approx(
        body["groupSubtotal"]["monthly"], abs=0.01
    )

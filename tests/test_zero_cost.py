"""warn_zero_cost_lines: flag $0 line items anywhere in the body, groups included."""
from create_estimate import warn_zero_cost_lines


def test_zero_lines_found_at_top_level_and_in_nested_group(capsys):
    body = {
        "services": {
            "ec2Enhancement-paid": {"serviceCost": {"monthly": 68.62, "upfront": 0}},
            "amazonVirtualPrivateCloud-free": {"serviceCost": {"monthly": 0, "upfront": 0}},
        },
        "groups": {
            "Outer-1111": {
                "name": "Outer",
                "services": {},
                "groups": {
                    "Inner-2222": {
                        "name": "Inner",
                        "services": {
                            "amazonS3-zero": {"serviceCost": {"monthly": 0}},
                            "amazonMQ-paid": {"serviceCost": {"monthly": 8167.3}},
                        },
                        "groups": {},
                    }
                },
            }
        },
    }

    zero = warn_zero_cost_lines(body)

    assert sorted(zero) == ["amazonS3-zero", "amazonVirtualPrivateCloud-free"]
    assert "WARNING" in capsys.readouterr().err


def test_no_zero_lines_returns_empty_and_prints_nothing(capsys):
    body = {"services": {"ec2Enhancement-paid": {"serviceCost": {"monthly": 1.0}}}, "groups": {}}
    assert warn_zero_cost_lines(body) == []
    assert capsys.readouterr().err == ""


def test_upfront_only_line_is_not_flagged():
    body = {"services": {"ri-line": {"serviceCost": {"monthly": 0, "upfront": 500.0}}}}
    assert warn_zero_cost_lines(body) == []

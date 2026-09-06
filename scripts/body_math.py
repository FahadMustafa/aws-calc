#!/usr/bin/env python3
"""Recompute a saveAs body's group subtotals and totals bottom-up.

Implements the arithmetic documented in `references/body-schema.md`
("Building a body with groups" and its "Rounding" subsection):

- line-item and sub-service `serviceCost.monthly` / `upfront` are rounded to
  two decimal places;
- a group line item's `serviceCost` is the sum of its rounded sub-services;
- group `groupSubtotal` / `totalCost` and the body totals are raw float sums of
  those rounded values — the SPA uses native JS addition, so `1.02 + 8167.30`
  legitimately serialises as `8168.320000000001` and pre-rounding the totals
  would stop a captured body from reconciling.

Use it as a final pass over an assembled body before POSTing it, or as a check
that a hand-built body's totals agree with its line items.

Usage:
    python3 scripts/body_math.py path/to/body.json      # prints the fixed body
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

MONEY_KEYS = ("monthly", "upfront")


def _round_cost(cost: dict | None) -> dict:
    """Round a serviceCost's money fields to 2dp, preserving which keys exist."""
    out = dict(cost or {})
    for key in MONEY_KEYS:
        if key in out:
            out[key] = round(float(out[key] or 0), 2)
    return out


def _money(cost: dict | None, key: str) -> float:
    return float((cost or {}).get(key) or 0)


def _normalize_line_item(item: dict) -> dict:
    """Round a line item in place; group lines re-sum from their sub-services."""
    subs = item.get("subServices")
    if subs:
        for sub in subs:
            sub["serviceCost"] = _round_cost(sub.get("serviceCost"))
        cost = dict(item.get("serviceCost") or {})
        for key in MONEY_KEYS:
            total = sum(_money(sub.get("serviceCost"), key) for sub in subs)
            if key in cost or total:
                cost[key] = round(total, 2)
        item["serviceCost"] = cost
    else:
        item["serviceCost"] = _round_cost(item.get("serviceCost"))
    return item


def _compute_container(container: dict) -> dict:
    """Set groupSubtotal/totalCost on a group (or the body) and return totalCost."""
    services = container.get("services") or {}
    for item in services.values():
        _normalize_line_item(item)

    subtotal = {
        key: sum(_money(item.get("serviceCost"), key) for item in services.values())
        for key in MONEY_KEYS
    }

    child_totals = [
        _compute_container(group) for group in (container.get("groups") or {}).values()
    ]
    total = {
        key: subtotal[key] + sum(child[key] for child in child_totals)
        for key in MONEY_KEYS
    }

    container["groupSubtotal"] = dict(subtotal)
    container["totalCost"] = dict(total)
    return total


def compute_totals(body: dict) -> dict:
    """Return a copy of `body` with every groupSubtotal and totalCost recomputed."""
    out = copy.deepcopy(body)
    _compute_container(out)
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in {"-h", "--help"}:
        print(__doc__)
        return 0 if len(argv) == 2 else 2
    body = json.loads(Path(argv[1]).read_text())
    json.dump(compute_totals(body), sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

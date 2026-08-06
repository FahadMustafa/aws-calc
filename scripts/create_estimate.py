#!/usr/bin/env python3
"""Replay an AWS Pricing Calculator save without driving the browser.

Reads a JSON file containing the saveAs request body, POSTs it to the public
unauthenticated calculator.aws save endpoint, and prints the share URL.

Usage: python create_estimate.py [path/to/input.json]
       (default: references/examples/sample-saveas-body.json)
Exit 0 on success, non-zero on failure.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

SAVE_API = "https://dnd5zrqcec4or.cloudfront.net/Prod/v2/saveAs"
LOAD_API = "https://d3knqfixx3sbls.cloudfront.net/{}"
SHARE_URL = "https://calculator.aws/#/estimate?id={}"

# Match the SPA's headers — CloudFront/WAF may key off Origin or User-Agent.
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://calculator.aws",
    "Referer": "https://calculator.aws/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    ),
}


def now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _iter_line_items(body: dict):
    """Yield (key, line_item) for every top-level and grouped service line item."""
    def walk_group(container):
        for k, v in (container.get("services") or {}).items():
            yield k, v
        for g in (container.get("groups") or {}).values():
            yield from walk_group(g)
    yield from walk_group(body)


def warn_zero_cost_lines(body: dict) -> None:
    """Backstop for the 'non-zero usage must yield non-zero cost' invariant.

    A $0 line item is usually a silent failure (wrong opaque token, inferred-but-
    wrong cc field name, empty data-transfer destination, or a zero-rate lookup).
    Some lines are legitimately free, so this only warns — it does not block.
    """
    zero = []
    for key, item in _iter_line_items(body):
        cost = item.get("serviceCost") or {}
        monthly = cost.get("monthly") or 0
        upfront = cost.get("upfront") or 0
        # group wrappers carry their own serviceCost summed from subServices; still flag $0
        if not monthly and not upfront:
            zero.append(key)
    if zero:
        print(
            "WARNING: {} line item(s) have serviceCost $0 — verify these are genuinely "
            "free and not a silent miscompute (wrong token / cc field / empty DT "
            "destination):\n  {}".format(len(zero), "\n  ".join(zero)),
            file=sys.stderr,
        )


def create_estimate(body: dict) -> str:
    # Stamp a fresh createdOn so the server doesn't dedupe to a previous save.
    body.setdefault("metaData", {})["createdOn"] = now_iso_z()

    warn_zero_cost_lines(body)

    r = requests.post(SAVE_API, json=body, headers=HEADERS, timeout=30)
    r.raise_for_status()

    envelope = r.json()
    if envelope.get("statusCode") != 201:
        raise RuntimeError(f"unexpected envelope: {envelope}")
    inner = json.loads(envelope["body"])
    return inner["savedKey"]


def main(argv: list[str]) -> int:
    default = Path(__file__).resolve().parent.parent / "references" / "examples" / "sample-saveas-body.json"
    path = Path(argv[1]) if len(argv) > 1 else default
    body = json.loads(path.read_text())
    saved_key = create_estimate(body)
    print(SHARE_URL.format(saved_key))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

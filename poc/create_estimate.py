#!/usr/bin/env python3
"""Replay an AWS Pricing Calculator save without driving the browser.

Reads a JSON file containing the saveAs request body, POSTs it to the public
unauthenticated calculator.aws save endpoint, and prints the share URL.

Usage: python create_estimate.py [path/to/input.json]   (default: sample_input.json)
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


def create_estimate(body: dict) -> str:
    # Stamp a fresh createdOn so the server doesn't dedupe to a previous save.
    body.setdefault("metaData", {})["createdOn"] = now_iso_z()

    r = requests.post(SAVE_API, json=body, headers=HEADERS, timeout=30)
    r.raise_for_status()

    envelope = r.json()
    if envelope.get("statusCode") != 201:
        raise RuntimeError(f"unexpected envelope: {envelope}")
    inner = json.loads(envelope["body"])
    return inner["savedKey"]


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).parent / "sample_input.json"
    body = json.loads(path.read_text())
    saved_key = create_estimate(body)
    print(SHARE_URL.format(saved_key))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

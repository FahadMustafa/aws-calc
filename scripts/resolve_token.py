#!/usr/bin/env python3
"""Resolve the calculator.aws SPA's opaque cc tokens via the public service catalog.

Several service modules use opaque 43-char URL-safe-base64 tokens in their
saveAs `calculationComponents` (e.g. `rabbitmqInstanceTypeClustered`). The SPA
fetches a per-service catalog at runtime that contains the full token mapping
(the token is the catalog's `RegionlessRateCode`). The catalogs are world-
readable, region-independent, and stable.

Catalog URL pattern:
    https://calculator.aws/pricing/2.0/meteredUnitMaps/<service>/USD/current/<service>.json

The catalog shape:
    {
      "manifest": {...},
      "sets":   { "<set-name>": [<sku-string>, ...], ... },   // may be empty for some services
      "regions": {
        "<region display name>": {
          "<key>": {                                          // <key> is one of: SKU rateCode, RegionlessRateCode, or a friendly catalog key
            "rateCode": "...",
            "price": "0.96",
            "RegionlessRateCode": "<43-char token>",
            "Instance Type": "m5.large",                      // service-dependent metadata
            ...
          },
          ...
        },
        ...
      }
    }

For mq.json the `regions[*]` dict has friendly keys like
"RabbitMQ Active Standby mq m5.large" — that's the cheap lookup path. Other
catalogs (e.g. bedrock.json) only key by the opaque code; you have to enumerate
the inner records and match on metadata, or chain through another catalog.

USAGE

    # MQ — friendly lookup
    python3 resolve_token.py mq --friendly "RabbitMQ Active Standby mq m5.large"
        -> 5hcZU6WguRUktrgs8rMw8I50JgkU3TyzOOdhtsRRjXs

    # MQ — dump all friendly→token mappings
    python3 resolve_token.py mq --dump-friendly

    # Generic — fetch + cache the catalog
    python3 resolve_token.py <service>           # downloads to ~/.cache/aws-calc/

The fetched catalog is cached in ~/.cache/aws-calc/<service>.json; pass
--refresh to bypass the cache.
"""
from __future__ import annotations

import argparse
import re
import sys

from catalog import CATALOG_URL, fetch_catalog  # noqa: F401  (re-exported)


def is_friendly_key(key: str) -> bool:
    """Heuristic: friendly catalog keys are human-readable (contain spaces or
    have <40 chars), while SKU keys look like '2W8XN55QZFAE2MMK JRTCKXETXF...'
    and opaque tokens are exactly 43 url-safe-base64 chars."""
    if " " in key and not re.match(r"^[0-9A-Z]{16,17}\s", key):
        return True
    return False


def build_friendly_map(catalog: dict) -> dict[str, str]:
    """Return {friendly_key: RegionlessRateCode}, deduped across regions."""
    mapping: dict[str, str] = {}
    for region_data in (catalog.get("regions") or {}).values():
        if not isinstance(region_data, dict):
            continue
        for key, rec in region_data.items():
            if not isinstance(rec, dict):
                continue
            rrc = rec.get("RegionlessRateCode")
            if not rrc or not is_friendly_key(key):
                continue
            mapping.setdefault(key, rrc)
    return mapping


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("service", help="service slug (e.g. mq, bedrock, bedrockfoundationmodels)")
    p.add_argument("--friendly", help="resolve a friendly catalog key to its token")
    p.add_argument("--dump-friendly", action="store_true", help="print all friendly→token mappings")
    p.add_argument("--refresh", action="store_true", help="ignore cache and re-download")
    args = p.parse_args()

    catalog = fetch_catalog(args.service, refresh=args.refresh)

    if args.dump_friendly:
        mapping = build_friendly_map(catalog)
        print(f"# {len(mapping)} friendly→token mappings for {args.service}", file=sys.stderr)
        for k in sorted(mapping):
            print(f"{k}\t{mapping[k]}")
        return 0

    if args.friendly:
        mapping = build_friendly_map(catalog)
        token = mapping.get(args.friendly)
        if not token:
            print(f"no friendly key matched '{args.friendly}' in {args.service} catalog", file=sys.stderr)
            print(f"closest available keys (substring match):", file=sys.stderr)
            needle = args.friendly.lower()
            for k in sorted(mapping):
                if any(w in k.lower() for w in needle.split()):
                    print(f"  {k}", file=sys.stderr)
            return 2
        print(token)
        return 0

    # default: print a one-line summary
    sets = catalog.get("sets") or {}
    regions = catalog.get("regions") or {}
    n_friendly = len(build_friendly_map(catalog))
    print(f"{args.service}: {len(sets)} sets, {len(regions)} regions, {n_friendly} friendly→token mappings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

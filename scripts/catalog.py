#!/usr/bin/env python3
"""Shared fetch + cache for the calculator.aws public pricing artifacts.

Two artifact families are involved, and they live on different hosts:

1. **Form definitions** — `https://d1qsjq9pzbk1k6.cloudfront.net/data/<serviceCode>/en_US.json`.
   These carry the form `version` and a `mappingDefinitions[]` list whose
   `mappingDefinitionURL` points at the metered unit map(s) the SPA prices that
   form from. The URL contains a literal `[currency]` placeholder to substitute.

2. **Metered unit maps** — `https://calculator.aws/pricing/2.0/meteredUnitMaps/...`.
   Shape: `{"manifest": {...}, "sets": {...}, "regions": {"<display name>": {"<key>": {...}}}}`.
   A record always has `price` (a decimal string); tiered records also carry
   `StartingRange` / `EndingRange` in the map's own unit (GB for data transfer).

Everything here is a read-only GET, gzip-aware, cached under `$AWS_CALC_CACHE`
(default `~/.cache/aws-calc/`) for 24h, keyed on the cache file's mtime. Writes go
through a temp file + `os.replace`, so a crash mid-write cannot leave a truncated
cache behind, and an unreadable cache entry is treated as a miss rather than an
error — the same conventions `check_versions.py` uses. `fetch_json` is the single
network seam — tests monkeypatch it and never touch the network.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
import time
import urllib.request
import zlib
from pathlib import Path

CALCULATOR_HOST = "https://calculator.aws/"
FORM_DEF_URL = "https://d1qsjq9pzbk1k6.cloudfront.net/data/{code}/en_US.json"
CATALOG_URL = "https://calculator.aws/pricing/2.0/meteredUnitMaps/{service}/USD/current/{service}.json"
CURRENCY = "USD"

CACHE_TTL_SECONDS = 24 * 60 * 60


def cache_dir() -> Path:
    """`$AWS_CALC_CACHE`, or `~/.cache/aws-calc`.

    Read at call time, not import time, so tests (and a caller that sets the env
    var late) can point it somewhere else.
    """
    return Path(os.environ.get("AWS_CALC_CACHE") or (Path.home() / ".cache" / "aws-calc"))

# Region code -> catalog region display name. Mirrors references/body-schema.md.
REGION_NAMES = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "ca-central-1": "Canada (Central)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-west-3": "EU (Paris)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-north-1": "EU (Stockholm)",
    "eu-south-1": "EU (Milan)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "sa-east-1": "South America (Sao Paulo)",
    "me-south-1": "Middle East (Bahrain)",
    "me-central-1": "Middle East (UAE)",
    "af-south-1": "Africa (Cape Town)",
    "il-central-1": "Israel (Tel Aviv)",
}


class CatalogError(RuntimeError):
    """A catalog could not be fetched, or does not contain what was asked for."""


def region_display_name(region_code: str) -> str:
    name = REGION_NAMES.get(region_code)
    if not name:
        raise CatalogError(
            f"no catalog display name known for region {region_code!r}; "
            "add it to catalog.REGION_NAMES (see references/body-schema.md)"
        )
    return name


def cache_key_for_url(url: str) -> str:
    """Stable, filesystem-safe cache/fixture filename for an artifact URL.

    Derived from the URL path only (host is fixed per artifact family), so the
    same key names the on-disk cache entry and the committed test fixture.
    """
    path = url.split("://", 1)[-1].split("/", 1)[-1]
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", path)
    return slug.strip("_")


def _read_cache(path: Path) -> dict | None:
    """Cached payload if present and younger than the TTL, else None.

    An unreadable or unparseable file is a miss, not an error: a half-written or
    hand-mangled cache entry must not poison every later run. A future-dated mtime
    (clock skew) is treated as stale for the same reason.
    """
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return None
    if not 0 <= age < CACHE_TTL_SECONDS:
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _write_cache(path: Path, data: dict) -> None:
    """Write via a temp file + os.replace; a cache we cannot write is not an error."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)  # atomic: a crash mid-write cannot truncate the cache
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def fetch_json(url: str, *, refresh: bool = False, cache_name: str | None = None) -> dict:
    """GET `url`, decode gzip/deflate, parse JSON, cache under $AWS_CALC_CACHE for 24h.

    This is the only function in the skill that reaches the network for pricing
    artifacts. Tests monkeypatch it.
    """
    cache_path = cache_dir() / (cache_name or cache_key_for_url(url))
    if not refresh:
        cached = _read_cache(cache_path)
        if cached is not None:
            return cached
    print(f"fetching {url}", file=sys.stderr)
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        enc = resp.headers.get("Content-Encoding", "")
    if enc == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    elif enc == "deflate":
        raw = zlib.decompress(raw)
    data = json.loads(raw.decode("utf-8"))
    _write_cache(cache_path, data)
    return data


def fetch_catalog(service: str, *, refresh: bool = False) -> dict:
    """Fetch the `<service>/USD/current/<service>.json` metered unit map.

    Kept on the legacy `~/.cache/aws-calc/<service>.json` cache filename that
    `resolve_token.py` has always used.
    """
    return fetch_json(
        CATALOG_URL.format(service=service),
        refresh=refresh,
        cache_name=f"{service}.json",
    )


def fetch_form_definition(service_code: str, *, refresh: bool = False) -> dict:
    """Fetch a service's form definition (carries `version` + `mappingDefinitions`)."""
    return fetch_json(FORM_DEF_URL.format(code=service_code), refresh=refresh)


def mapping_definition_urls(form_def: dict) -> dict[str, str]:
    """`{mappingDefinitionName: absolute USD URL}` from a form definition.

    `mappingDefinitionURL` is relative to calculator.aws and contains a literal
    `[currency]` segment. A definition without a name is keyed by its filename
    stem so it is still reachable.
    """
    urls: dict[str, str] = {}
    for entry in form_def.get("mappingDefinitions") or []:
        raw = entry.get("mappingDefinitionURL")
        if not raw:
            continue
        absolute = CALCULATOR_HOST + raw.lstrip("/").replace("[currency]", CURRENCY)
        name = entry.get("mappingDefinitionName") or Path(raw).stem
        urls[name] = absolute
    return urls


def fetch_mapping(service_code: str, mapping_name: str, *, refresh: bool = False) -> dict:
    """Discover `mapping_name`'s URL from the form definition, then fetch it."""
    form_def = fetch_form_definition(service_code, refresh=refresh)
    urls = mapping_definition_urls(form_def)
    url = urls.get(mapping_name)
    if not url:
        raise CatalogError(
            f"{service_code} form definition has no mappingDefinition {mapping_name!r} "
            f"(has: {sorted(urls)})"
        )
    return fetch_json(url, refresh=refresh)


def region_prices(catalog: dict, region_name: str) -> dict:
    """`catalog['regions'][region_name]`, failing loudly when the region is absent."""
    regions = catalog.get("regions") or {}
    prices = regions.get(region_name)
    if not isinstance(prices, dict):
        raise CatalogError(
            f"catalog has no region {region_name!r} "
            f"({len(regions)} regions available)"
        )
    return prices


def price_of(prices: dict, key: str) -> float:
    """Price for a catalog key, as a float. Missing key is an error, not a 0."""
    record = prices.get(key)
    if not isinstance(record, dict) or "price" not in record:
        raise CatalogError(f"catalog region has no priced key {key!r}")
    return float(record["price"])

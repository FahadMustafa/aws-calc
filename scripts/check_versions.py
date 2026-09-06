#!/usr/bin/env python3
"""Detect form-version drift between the aws-calc service modules and live calculator.aws.

Every service module pins a form `version` (and `serviceCode`) in its header JSON.
calculator.aws ships new form versions over time; when a stored estimate's version is
older than the live form, the SPA flags the line "needs update" and a recompute can
error ("This service in your estimate isn't compatible with your original inputs").

This script parses each module's serviceCode/version pairs and compares them against
the live service definition the SPA fetches at runtime:

    https://d1qsjq9pzbk1k6.cloudfront.net/data/<serviceCode>/en_US.json   ->  .version

Top-level services AND sub-services (e.g. vpnConnectionVpc, publicIpv4Address) each
have their own definition file, so both are checked. Codes with no live definition
(pure UI groupings) are reported as "no-live-def", not as drift.

Exit code: 0 if no drift, 1 if any drift detected, 2 on fetch/parse errors only.

Usage:
    python3 scripts/check_versions.py
    python3 scripts/check_versions.py --modules references/service-modules
    python3 scripts/check_versions.py --json        # machine-readable output
    python3 scripts/check_versions.py --codes ec2Enhancement,s3   # only these codes
    python3 scripts/check_versions.py --refresh     # ignore the 24h live-version cache

Live versions are cached for 24h in $AWS_CALC_CACHE/live-versions.json (default
~/.cache/aws-calc/) so the workflow's per-estimate drift gate costs no fetches.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import glob
import gzip
import json
import os
import re
import sys
import urllib.request
import zlib

DATA_URL = "https://d1qsjq9pzbk1k6.cloudfront.net/data/{service}/en_US.json"
DEFAULT_MODULES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "service-modules",
)
CACHE_FILENAME = "live-versions.json"
CACHE_TTL_SECONDS = 24 * 60 * 60

# serviceCode -> version pairs are extracted from the fenced ```json / ```jsonc
# blocks in each module. A pair is only made when "serviceCode" and "version"
# are keys of the SAME object literal — a group wrapper and its nested
# sub-services each carry their own pair, and prose outside a fence is ignored.
_FENCE_RE = re.compile(r"```(?:json|jsonc)\n(.*?)```", re.DOTALL)
_VERSION_RE = re.compile(r"^[0-9][0-9.]*$")


def _strip_comments(block: str) -> str:
    """Drop `// ...` and `/* ... */` jsonc comments, ignoring both inside strings.

    drs.md uses block comments as sub-service placeholders, and a comment can
    contain braces or a stray quote — leaving them in would desync the object
    scanner and let a commented-out "version" get paired.
    """
    out = []
    in_string = False
    i, n = 0, len(block)
    while i < n:
        ch = block[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(block[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and block[i + 1] == "/":
            while i < n and block[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and block[i + 1] == "*":
            end = block.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _read_string(text: str, i: int) -> tuple[str, int]:
    """Read the string literal starting at text[i] == '\"'. Returns (value, next_i)."""
    i += 1
    chars = []
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            chars.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            return "".join(chars), i + 1
        chars.append(ch)
        i += 1
    return "".join(chars), i  # unterminated — treat the rest as the value


def _iter_object_literals(block: str):
    """Yield {key: string_value} for each object literal's own (non-nested) keys."""
    stack: list[dict[str, str]] = []
    i, n = 0, len(block)
    while i < n:
        ch = block[i]
        if ch == "{":
            stack.append({})
            i += 1
        elif ch == "}":
            if stack:
                yield stack.pop()
            i += 1
        elif ch == '"':
            key, i = _read_string(block, i)
            j = i
            while j < n and block[j].isspace():
                j += 1
            if j < n and block[j] == ":":
                j += 1
                while j < n and block[j].isspace():
                    j += 1
                if j < n and block[j] == '"':
                    value, j = _read_string(block, j)
                    if stack:
                        stack[-1][key] = value
                i = j
        else:
            i += 1


def extract_pairs(modules_dir: str) -> dict[str, set[tuple[str, str]]]:
    """Return {serviceCode: {(version, source_file), ...}}."""
    pairs: dict[str, set[tuple[str, str]]] = {}
    for path in sorted(glob.glob(os.path.join(modules_dir, "*.md"))):
        text = open(path, encoding="utf-8").read()
        fname = os.path.basename(path)
        for block in _FENCE_RE.findall(text):
            for obj in _iter_object_literals(_strip_comments(block)):
                code, version = obj.get("serviceCode"), obj.get("version")
                if code and version and _VERSION_RE.match(version):
                    pairs.setdefault(code, set()).add((version, fname))
    return pairs


def fetch_live_version(code: str) -> tuple[str, str | None, str | None]:
    """Return (code, live_version_or_None, error_or_None)."""
    url = DATA_URL.format(service=code)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip, deflate"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            enc = resp.headers.get("Content-Encoding", "")
        if enc == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        elif enc == "deflate":
            raw = zlib.decompress(raw)
        data = json.loads(raw.decode("utf-8"))
        return code, data.get("version"), None
    except urllib.error.HTTPError as e:
        if e.code == 403 or e.code == 404:
            return code, None, "no-live-def"
        return code, None, f"http {e.code}"
    except Exception as e:  # noqa: BLE001
        return code, None, f"error: {e}"


def cache_path() -> str:
    """$AWS_CALC_CACHE/live-versions.json — same env var resolve_token.py honours.

    Read at call time (not import time) so tests can point it at a tmp dir.
    """
    base = os.environ.get("AWS_CALC_CACHE") or os.path.join(
        os.path.expanduser("~"), ".cache", "aws-calc"
    )
    return os.path.join(base, CACHE_FILENAME)


def _load_cache() -> dict[str, dict]:
    """Return the cache mapping, or {} if it is missing or unreadable."""
    try:
        with open(cache_path(), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache(cache: dict[str, dict]) -> None:
    path = cache_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, indent=2, sort_keys=True)
    except OSError:
        pass  # a cache we cannot write is a slow run, not a failed one


def _is_fresh(entry: object, now: dt.datetime) -> bool:
    if not isinstance(entry, dict) or "version" not in entry:
        return False
    try:
        fetched = dt.datetime.fromisoformat(str(entry.get("fetched")))
    except ValueError:
        return False
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=dt.timezone.utc)
    return (now - fetched).total_seconds() < CACHE_TTL_SECONDS


def resolve_live_versions(
    codes, refresh: bool = False
) -> dict[str, tuple[str | None, str | None]]:
    """Return {code: (live_version_or_None, error_or_None)}, using the 24h cache.

    A cached `null` version means "no live definition" (a pure UI grouping) and is
    honoured like any other hit, so those codes are not refetched every run.
    Transient errors (http 5xx, timeouts) are never cached.
    """
    codes = list(codes)
    now = dt.datetime.now(dt.timezone.utc)
    cache = {} if refresh else _load_cache()

    live: dict[str, tuple[str | None, str | None]] = {}
    to_fetch = []
    for code in codes:
        entry = cache.get(code)
        if _is_fresh(entry, now):
            version = entry["version"]
            live[code] = (version, None if version is not None else "no-live-def")
        else:
            to_fetch.append(code)

    if to_fetch:
        with cf.ThreadPoolExecutor(max_workers=12) as ex:
            results = list(ex.map(lambda c: fetch_live_version(c), to_fetch))
        cache = _load_cache() if refresh else cache
        stamp = now.isoformat()
        for code, version, err in results:
            live[code] = (version, err)
            if err is None or err == "no-live-def":
                cache[code] = {"version": version, "fetched": stamp}
        _save_cache(cache)

    return live


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modules", default=DEFAULT_MODULES, help="path to references/service-modules")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--codes", help="comma-separated serviceCodes to check (default: all)")
    ap.add_argument("--refresh", action="store_true", help="ignore the 24h live-version cache")
    args = ap.parse_args(argv)

    pairs = extract_pairs(args.modules)
    if not pairs:
        print(f"no serviceCode/version pairs found under {args.modules}", file=sys.stderr)
        return 2

    if args.codes:
        wanted = [c.strip() for c in args.codes.split(",") if c.strip()]
        unknown = [c for c in wanted if c not in pairs]
        if unknown:
            print(f"unknown serviceCode(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        pairs = {c: pairs[c] for c in wanted}

    live = resolve_live_versions(pairs, refresh=args.refresh)

    rows = []
    drift = errors = 0
    for code in sorted(pairs):
        skill_versions = sorted({v for v, _ in pairs[code]})
        src = sorted({f for _, f in pairs[code]})
        live_ver, err = live[code]
        if err == "no-live-def":
            status = "no-live-def"
        elif err:
            status = err
            errors += 1
        elif live_ver in skill_versions:
            status = "ok"
        else:
            status = "DRIFT"
            drift += 1
        rows.append({
            "serviceCode": code,
            "skill": skill_versions,
            "live": live_ver,
            "status": status,
            "modules": src,
        })

    stale_modules = sorted({m for r in rows if r["status"] == "DRIFT" for m in r["modules"]})

    if args.json:
        json.dump(
            {"drift": drift, "errors": errors, "rows": rows, "stale_modules": stale_modules},
            sys.stdout,
            indent=2,
        )
        print()
    else:
        print(f"{'serviceCode':42} {'skill':10} {'live':10} status")
        print("-" * 84)
        for r in rows:
            sk = ",".join(r["skill"])
            status = r["status"]
            mark = "*** " if status == "DRIFT" else ""
            print(f"{r['serviceCode']:42} {sk:10} {str(r['live']):10} {mark}{status}")
        print("-" * 84)
        print(f"DRIFT: {drift}   errors: {errors}   checked: {len(rows)}")
        if drift:
            print("\nDrifted modules need their header `version` bumped to the live value, and "
                  "the calculationComponents shape re-checked against the new form "
                  "(fields can be added/renamed across versions — see cloudfront.md 0.0.45->0.0.47).")

    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())

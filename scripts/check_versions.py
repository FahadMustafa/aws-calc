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
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
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

# serviceCode -> version pairs are extracted from the fenced ```json / ```jsonc
# blocks in each module. A pair is only made when "serviceCode" and "version"
# are keys of the SAME object literal — a group wrapper and its nested
# sub-services each carry their own pair, and prose outside a fence is ignored.
_FENCE_RE = re.compile(r"```(?:json|jsonc)\n(.*?)```", re.DOTALL)
_VERSION_RE = re.compile(r"^[0-9][0-9.]*$")


def _strip_line_comments(block: str) -> str:
    """Drop `// ...` jsonc comments without touching `//` inside string literals."""
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
            for obj in _iter_object_literals(_strip_line_comments(block)):
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modules", default=DEFAULT_MODULES, help="path to references/service-modules")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    pairs = extract_pairs(args.modules)
    if not pairs:
        print(f"no serviceCode/version pairs found under {args.modules}", file=sys.stderr)
        return 2

    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        live = dict(
            (code, (ver, err)) for code, ver, err in ex.map(fetch_live_version, pairs)
        )

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

    if args.json:
        json.dump({"drift": drift, "errors": errors, "rows": rows}, sys.stdout, indent=2)
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

#!/usr/bin/env python3
"""Stream a HAR file, extract every POST to /Prod/v2/saveAs, write each body
as a pretty-printed JSON file under an output directory, write an INDEX.json
keyed by serviceCode, and split each service line-item into per-service/<code>.json.

Designed for very large HARs — uses ijson to avoid loading the full file.

Usage:
    extract_saveas.py [HAR_PATH] [OUT_DIR]

Defaults to the most recent HAR convention if no args given.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import os
import sys
import zlib
from pathlib import Path

import ijson

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HAR = REPO_ROOT / "captures" / "calculator.aws.har"
DEFAULT_OUT = REPO_ROOT / "captures" / "saveAs"
SAVEAS_MARKER = "/Prod/v2/saveAs"


def maybe_decode(text: str, encoding: str | None) -> str:
    """Decode a HAR postData.text value. HAR may set encoding to base64."""
    if not text:
        return text
    if encoding == "base64":
        try:
            raw = base64.b64decode(text)
        except Exception:
            return text
        # try gzip / deflate, else assume utf-8 text
        for decoder in (gzip.decompress, zlib.decompress):
            try:
                return decoder(raw).decode("utf-8", errors="replace")
            except Exception:
                pass
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return text
    return text


def safe_json_loads(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some HAR captures wrap the body or include trailing data; try to
        # find the outermost JSON object.
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            try:
                return json.loads(text[first : last + 1])
            except json.JSONDecodeError:
                return None
        return None


def stream_entries(har_path: Path):
    """Yield (entry_index, entry_dict) for every entry in log.entries."""
    with har_path.open("rb") as fh:
        # HAR top-level is { "log": { "entries": [...] } }
        for idx, entry in enumerate(ijson.items(fh, "log.entries.item")):
            yield idx, entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("har_path", nargs="?", type=Path, default=DEFAULT_HAR)
    parser.add_argument("out_dir", nargs="?", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    har_path: Path = args.har_path
    out_dir: Path = args.out_dir
    index_path = out_dir / "INDEX.json"
    per_service_dir = out_dir / "per-service"

    out_dir.mkdir(parents=True, exist_ok=True)
    per_service_dir.mkdir(parents=True, exist_ok=True)

    matches = []  # list of (har_index, body_dict)
    parse_failures = []  # list of (har_index, reason)

    print(f"Streaming HAR: {har_path} ({har_path.stat().st_size:,} bytes)", file=sys.stderr)

    for har_idx, entry in stream_entries(har_path):
        request = entry.get("request") or {}
        url = request.get("url") or ""
        method = request.get("method") or ""
        if method != "POST" or SAVEAS_MARKER not in url:
            continue

        post_data = request.get("postData") or {}
        text = post_data.get("text") or ""
        encoding = post_data.get("encoding")
        decoded = maybe_decode(text, encoding)
        body = safe_json_loads(decoded)
        if body is None:
            parse_failures.append((har_idx, "could not parse postData.text as JSON"))
            continue
        matches.append((har_idx, body))

    print(f"Found {len(matches)} saveAs POSTs", file=sys.stderr)

    # write per-POST files and build index
    seq_width = max(2, len(str(len(matches) - 1))) if matches else 2
    index: dict[str, list[dict]] = {}
    file_summary = []

    per_service_files: dict[str, list[str]] = {}

    def walk_services(body_or_group, group_path):
        """Yield (line_item_key, svc_dict, group_path) for every service in this
        node and any nested groups. group_path is a tuple of group names from the
        top-level estimate down to the immediate parent group ('()' = top-level)."""
        for k, svc in (body_or_group.get("services") or {}).items():
            if isinstance(svc, dict):
                yield k, svc, group_path
        for group_key, group in (body_or_group.get("groups") or {}).items():
            if not isinstance(group, dict):
                continue
            child_name = group.get("name") or group_key
            yield from walk_services(group, group_path + (child_name,))

    for seq, (har_idx, body) in enumerate(matches):
        all_services = list(walk_services(body, ()))

        # collect distinct serviceCodes (across top-level + nested groups)
        codes_in_body = []
        for _, svc, _ in all_services:
            code = svc.get("serviceCode")
            if code and code not in codes_in_body:
                codes_in_body.append(code)

        codes_slug = ",".join(codes_in_body) if codes_in_body else "no-services"
        # keep filename sane
        safe_slug = codes_slug.replace("/", "_")
        if len(safe_slug) > 180:
            safe_slug = safe_slug[:180] + "...etc"
        filename = f"{seq:0{seq_width}d}-{safe_slug}.json"
        out_path = out_dir / filename

        with out_path.open("w") as fh:
            json.dump(body, fh, indent=2, sort_keys=True)

        rel_file = out_path.name

        # summarize the groups structure (for the body-level summary)
        def summarize_groups(node):
            return [
                {
                    "key": gk,
                    "name": (g or {}).get("name"),
                    "service_count": len((g or {}).get("services") or {}),
                    "nested_groups": summarize_groups(g or {}),
                    "groupSubtotal": (g or {}).get("groupSubtotal"),
                    "totalCost": (g or {}).get("totalCost"),
                }
                for gk, g in (node.get("groups") or {}).items()
            ]

        body_summary = {
            "file": rel_file,
            "har_entry_index": har_idx,
            "har_path": f"log.entries[{har_idx}]",
            "service_count": len(all_services),
            "top_level_service_count": len(body.get("services") or {}),
            "service_codes": codes_in_body,
            "groups": summarize_groups(body),
            "totalCost": body.get("totalCost"),
            "groupSubtotal": body.get("groupSubtotal"),
            "name": body.get("name"),
        }
        file_summary.append(body_summary)

        for line_item_key, svc, group_path in all_services:
            code = svc.get("serviceCode")
            if not code:
                continue
            entry_summary = {
                "file": rel_file,
                "har_entry_index": har_idx,
                "line_item_key": line_item_key,
                "estimateFor": svc.get("estimateFor"),
                "version": svc.get("version"),
                "region": svc.get("region"),
                "serviceName": svc.get("serviceName"),
                "group_path": list(group_path),     # empty list = top-level (no group)
            }
            index.setdefault(code, []).append(entry_summary)

            # Write the single line item out to per-service/<code>.json.
            # If multiple line items exist for the same service in the capture,
            # disambiguate with a numeric suffix.
            existing = per_service_files.setdefault(code, [])
            suffix = "" if not existing else f"-{len(existing)}"
            per_service_path = per_service_dir / f"{code}{suffix}.json"
            payload = {
                "lineItemKey": line_item_key,
                "service": svc,
                "_source": {
                    "har_entry_index": har_idx,
                    "saveAs_body_file": rel_file,
                    "group_path": list(group_path),
                },
            }
            with per_service_path.open("w") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
            existing.append(per_service_path.name)

    summary = {
        "har_file": str(har_path),
        "saveAs_post_count": len(matches),
        "parse_failures": [
            {"har_entry_index": idx, "reason": reason} for idx, reason in parse_failures
        ],
        "files": file_summary,
        "service_codes": {code: entries for code, entries in sorted(index.items())},
        "per_service_files": {code: files for code, files in sorted(per_service_files.items())},
    }

    with index_path.open("w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)

    print(f"Wrote {len(matches)} body files and INDEX.json to {out_dir}", file=sys.stderr)
    print(f"Wrote {sum(len(v) for v in per_service_files.values())} per-service files to {per_service_dir}", file=sys.stderr)
    print(f"Unique top-level serviceCodes: {len(index)}", file=sys.stderr)
    if parse_failures:
        print(f"Parse failures: {len(parse_failures)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

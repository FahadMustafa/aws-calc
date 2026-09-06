#!/usr/bin/env python3
"""Independently recompute a saveAs body's line-item costs from the SPA's own price data.

`validate_body.py` proves a body is *shaped* right and step 7's load check proves it
was *stored*; neither proves the numbers are right. This does: for every line item
whose `serviceCode` has a registered recomputer, it re-derives
`serviceCost.monthly` from the metered unit maps calculator.aws itself prices from
(`https://calculator.aws/pricing/2.0/meteredUnitMaps/...`) and diffs it against the
stored value.

    python3 scripts/recompute_oracle.py references/examples/sample-saveas-body.json
    python3 scripts/recompute_oracle.py body.json --json

Exit codes: 0 all oracle-covered lines within tolerance, 1 at least one line out of
tolerance (default 1%), 2 the body could not be read.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
An oracle that guesses is worse than no oracle, so anything not derivable from the
maps is reported as a note and either excluded from the recomputed total or reported
as "no oracle" (uncompared, never a silent pass):

- Reserved Instances / Savings Plans — the RI shards exist but the SPA's
  amortisation of upfront vs. hourly is not reproduced here. Reported "no oracle".
- EBS snapshots — the SPA's model is incremental (see ec2.md); snapshot GB is not in
  the body. Excluded from the total with a note when `snapshotFrequency` is non-zero.
- Any `serviceCode` without an entry in `ORACLES`. Reported "no oracle".

MAP DISCOVERY
-------------
Maps are found the way the SPA finds them: read `data/<serviceCode>/en_US.json`,
take `mappingDefinitions[].mappingDefinitionURL`, substitute `[currency]` with USD
(see catalog.py). The one exception is EC2 compute: `ec2Enhancement`'s form
definition does **not** advertise the instance-price map. The SPA's bundle builds
that path itself as
`/ec2/<currency>/current/ec2-calc/<region display name>/<selector values…>/index.json`,
so `EC2_CALC_BASE` below hardcodes that convention (derived from the live bundle
2026-09-06). If EC2 lines start reporting "instance type not found", re-derive it.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import catalog
from catalog import CatalogError
from pricing_client import walk_tiers

DEFAULT_TOLERANCE_PCT = 1.0

GB_PER_TB = 1024
HOURS_PER_MONTH = 730

EC2_CALC_BASE = "https://calculator.aws/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-calc"

# `selectedOS` cc token -> ec2-calc "Operating System" selector value. Tokens are
# the ones ec2.md documents as accepted; an unknown token is an error, not a
# silent fallback to Linux (which is exactly the trap ec2.md warns about).
EC2_OS_SELECTORS = {
    "linux": "Linux",
    "windows": "Windows",
    "rhel": "RHEL",
    "suse": "SUSE",
}
EC2_TENANCY_SELECTORS = {
    "shared": "Shared",
    "dedicatedInstance": "Dedicated",
}

# S3 Standard band edges in GB-month. The s3-standard map names the bands but
# carries no StartingRange/EndingRange, so the widths come from s3.md.
S3_STANDARD_TIERS = [
    ("Standard Storage First 50 TB per GB Mo", 0, 50 * 1024),
    ("Standard Storage Next 450 TB per GB Mo", 50 * 1024, 500 * 1024),
    ("Standard Storage Over 500 TB per GB Mo", 500 * 1024, float("inf")),
]

# SQS request bands in MILLIONS of requests per month (0-100B / 100B-200B / 200B+),
# per sqs.md. Same shape: the map names the tiers but not their edges.
SQS_TIERS = {
    "standard": [
        ("Standard per Requests", 0, 100_000),
        ("Standard per Requests Tier2", 100_000, 200_000),
        ("Standard per Requests Tier3", 200_000, float("inf")),
    ],
    "fifo": [
        ("FIFO first-in first-out per Requests", 0, 100_000),
        ("FIFO first-in first-out per Requests Tier2", 100_000, 200_000),
        ("FIFO first-in first-out per Requests Tier3", 200_000, float("inf")),
    ],
}


@dataclass
class OracleResult:
    """A recomputed monthly cost, or None when no defensible number exists."""

    recomputed: float | None
    notes: list[str] = field(default_factory=list)


def no_oracle(reason: str) -> OracleResult:
    return OracleResult(None, [reason])


# --------------------------------------------------------------------------- #
# cc readers                                                                    #
# --------------------------------------------------------------------------- #


def cc(item: dict) -> dict:
    return item.get("calculationComponents") or {}


def cc_value(item: dict, key: str, default=None):
    entry = cc(item).get(key)
    if not isinstance(entry, dict):
        return default
    return entry.get("value", default)


def as_float(value, default: float = 0.0) -> float:
    """Blank / missing cc values mean 0 to the SPA; garbage is an error."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    return float(text)


def dt_entries(item: dict, field_name: str) -> list[dict]:
    value = cc_value(item, field_name, [])
    return [e for e in value if isinstance(e, dict)] if isinstance(value, list) else []


def dt_gb(entry: dict) -> float:
    """Data-transfer entry volume in GB. `tb_month` is the only captured unit."""
    amount = as_float(entry.get("value"))
    unit = (entry.get("unit") or "").lower()
    if unit in ("tb_month", "tb|month", "tb"):
        return amount * GB_PER_TB
    return amount


# --------------------------------------------------------------------------- #
# shared pieces                                                                 #
# --------------------------------------------------------------------------- #


def tiers_to_dims(prices: dict, tiers: list[tuple[str, float, float]]) -> list[dict]:
    """Adapt named catalog tiers into the `walk_tiers` dimension shape."""
    return [
        {
            "begin_range": begin,
            "end_range": "Inf" if end == float("inf") else end,
            "price_per_unit": catalog.price_of(prices, key),
        }
        for key, begin, end in tiers
    ]


def datatransfer_outbound_dims(prices: dict) -> list[dict]:
    """External-outbound bands straight out of datatransfer-calc's own ranges."""
    dims = []
    for key, record in prices.items():
        if not key.startswith("DataTransfer External Outbound"):
            continue
        if not isinstance(record, dict) or "StartingRange" not in record:
            continue
        dims.append({
            "begin_range": record["StartingRange"],
            "end_range": record.get("EndingRange") or "Inf",
            "price_per_unit": float(record["price"]),
        })
    if not dims:
        raise CatalogError("datatransfer-calc has no External Outbound bands for this region")
    return dims


def outbound_transfer_cost(load_prices, entry: dict) -> tuple[float, list[str]]:
    """Cost of one OUTBOUND data-transfer entry, honouring the empty-destination trap.

    `load_prices` is a zero-argument callable returning the region's
    datatransfer-calc prices; it is only invoked when a charge is actually due, so
    a body full of blank DT entries costs no fetch.
    """
    gb = dt_gb(entry)
    if gb <= 0:
        return 0.0, []
    destination = (entry.get("toRegion") or "").strip()
    if not destination:
        # s3.md's empty-destination $0 trap: the SPA commits no charge without a
        # destination, so $0 is the *correct* recompute, not a modelling gap.
        return 0.0, [f"outbound {gb:g} GB has no destination — SPA prices it at $0"]
    if destination == "External":
        return walk_tiers(gb, datatransfer_outbound_dims(load_prices())), []
    return 0.0, [f"inter-region outbound to {destination!r} not modelled — excluded"]


def dt_price_loader(service_code: str, region_name: str, refresh: bool):
    """Lazy `datatransfer-calc` region-price loader for `outbound_transfer_cost`."""
    def load():
        mapping = catalog.fetch_mapping(service_code, "datatransfer-calc", refresh=refresh)
        return catalog.region_prices(mapping, region_name)
    return load


# --------------------------------------------------------------------------- #
# recomputers                                                                   #
# --------------------------------------------------------------------------- #


def ec2_shard_url(region_name: str, tenancy: str, os_name: str, generation: str) -> str:
    segments = [
        region_name,
        "OnDemand",
        tenancy,
        os_name,
        "NA",                      # Pre Installed S/W
        "No License required",     # License Model
        generation,
        "index.json",
    ]
    return EC2_CALC_BASE + "/" + urllib.parse.quote("/".join(segments), safe="/()")


def recompute_ec2(item: dict, region_name: str, *, refresh: bool = False) -> OracleResult:
    """EC2 On-Demand compute + EBS volume storage, per ec2.md's formula."""
    strategy = cc_value(item, "pricingStrategy", {}) or {}
    option = (strategy.get("selectedOption") or "").lower()
    if option != "on-demand":
        return no_oracle(f"no oracle for pricingStrategy {option or 'unset'!r} (reserved / savings plans)")

    os_token = (cc_value(item, "selectedOS", "linux") or "linux").lower()
    os_name = EC2_OS_SELECTORS.get(os_token)
    if not os_name:
        return no_oracle(f"unknown selectedOS {os_token!r} — not in ec2.md's accepted tokens")
    tenancy_token = cc_value(item, "tenancy", "shared") or "shared"
    tenancy = EC2_TENANCY_SELECTORS.get(tenancy_token)
    if not tenancy:
        return no_oracle(f"no oracle for tenancy {tenancy_token!r}")

    instance_type = cc_value(item, "instanceType")
    if not instance_type:
        return no_oracle("line item has no instanceType")

    notes: list[str] = []
    hourly = None
    for generation in ("Yes", "No"):
        # The map is sharded by "Current Generation"; the body does not say which
        # side the instance is on, so try current first and fall back to previous.
        # A missing shard is a normal outcome here (not every selector combination
        # has both generations), so it moves on rather than aborting the line.
        try:
            shard = catalog.fetch_json(ec2_shard_url(region_name, tenancy, os_name, generation), refresh=refresh)
        except (CatalogError, OSError):
            continue
        for record in catalog.region_prices(shard, region_name).values():
            if not isinstance(record, dict):
                continue
            if record.get("Instance Type") == instance_type and record.get("Unit") == "Hrs":
                hourly = float(record["price"])
                break
        if hourly is not None:
            break
    if hourly is None:
        return no_oracle(f"instance type {instance_type!r} not found in ec2-calc for {os_name}/{tenancy}")

    count = as_float((cc_value(item, "workload", {}) or {}).get("data"), 1.0)
    utilization = as_float(strategy.get("utilizationValue"), 100.0) / 100.0
    total = hourly * HOURS_PER_MONTH * utilization * count

    storage_gb = as_float(cc_value(item, "storageAmount"))
    if storage_gb:
        storage_type = cc_value(item, "storageType")
        if not storage_type:
            return no_oracle("storageAmount is set but storageType is missing")
        ebs = catalog.fetch_mapping("ec2Enhancement", "ebs-calculator", refresh=refresh)
        prices = catalog.region_prices(ebs, region_name)
        total += catalog.price_of(prices, storage_type) * storage_gb * count

    if as_float(cc_value(item, "snapshotFrequency")) > 0:
        # Snapshots are incremental and the changed-GB figure is not in the body
        # (ec2.md). Left out of the total rather than guessed at.
        notes.append("snapshot not modelled (incremental; changed GB not in body) — excluded from total")

    load_dt = dt_price_loader("ec2Enhancement", region_name, refresh)
    for entry in dt_entries(item, "dataTransferForEC2"):
        if entry.get("entryType") == "OUTBOUND":
            cost, dt_notes = outbound_transfer_cost(load_dt, entry)
            total += cost
            notes.extend(dt_notes)
        elif entry.get("entryType") == "INTRA_REGION" and dt_gb(entry) > 0:
            notes.append("intra-region data transfer not modelled — excluded from total")

    if cc_value(item, "detailedMonitoringCheckbox"):
        notes.append("detailed monitoring not modelled — excluded from total")

    return OracleResult(total, notes)


def recompute_s3_standard(item: dict, region_name: str, *, refresh: bool = False) -> OracleResult:
    gb = as_float(cc_value(item, "s3StandardStorageSize"))
    mapping = catalog.fetch_mapping("amazonS3Standard", "s3-standard", refresh=refresh)
    prices = catalog.region_prices(mapping, region_name)
    total = walk_tiers(gb, tiers_to_dims(prices, S3_STANDARD_TIERS))
    notes = []
    method = cc_value(item, "moveToStorageClassMethod", "No movement required")
    if method != "No movement required":
        notes.append(f"lifecycle/manual movement ({method!r}) not modelled — excluded from total")
    return OracleResult(total, notes)


def recompute_s3_data_transfer(item: dict, region_name: str, *, refresh: bool = False) -> OracleResult:
    load_dt = dt_price_loader("awsS3DataTransfer", region_name, refresh)
    total = 0.0
    notes: list[str] = []
    for entry in dt_entries(item, "dataTransfer"):
        if entry.get("entryType") != "OUTBOUND":
            continue  # inbound from the internet is free in the map ($0 rate)
        cost, dt_notes = outbound_transfer_cost(load_dt, entry)
        total += cost
        notes.extend(dt_notes)
    return OracleResult(total, notes)


def recompute_sqs(item: dict, region_name: str, *, refresh: bool = False) -> OracleResult:
    mapping = catalog.fetch_mapping("amazonSimpleQueueService", "queueservice", refresh=refresh)
    prices = catalog.region_prices(mapping, region_name)

    fair_millions = as_float(cc_value(item, "fairQueueRequests"))
    if fair_millions > 0:
        # queueservice.json carries Standard and FIFO tiers only — no Fair SKU.
        return no_oracle(f"fair queue requests ({fair_millions:g}M) have no rate in queueservice.json")

    total = 0.0
    for cc_field, tier_key in (("standardQueueRequests", "standard"), ("fifoQueueRequests", "fifo")):
        millions = as_float(cc_value(item, cc_field))
        if millions <= 0:
            continue
        dims = tiers_to_dims(prices, SQS_TIERS[tier_key])
        # Map prices are per request; the cc value is in millions (conventions.md §3).
        for dim in dims:
            dim["price_per_unit"] *= 1_000_000
        total += walk_tiers(millions, dims)

    notes: list[str] = []
    load_dt = dt_price_loader("amazonSimpleQueueService", region_name, refresh)
    for entry in dt_entries(item, "dataTransfer"):
        if entry.get("entryType") != "OUTBOUND":
            continue
        cost, dt_notes = outbound_transfer_cost(load_dt, entry)
        total += cost
        notes.extend(dt_notes)
    return OracleResult(total, notes)


def recompute_sns_standard(item: dict, region_name: str, *, refresh: bool = False) -> OracleResult:
    """SNS Standard topic, per sns.md's reconciled formula with catalog rates."""
    mapping = catalog.fetch_mapping("standardTopics", "sns", refresh=refresh)
    prices = catalog.region_prices(mapping, region_name)
    notes: list[str] = []

    def millions(key: str) -> float:
        return as_float(cc_value(item, key))

    total = millions("numberOfRequests") * 1e6 * catalog.price_of(prices, "Amazon SNS API Requests")

    # HTTP and email carry their free bands in the map itself (a $0 first tier).
    http = millions("numberOfHTTPNotifications") * 1e6
    total += walk_tiers(http, [
        {"begin_range": 0, "end_range": 100_000, "price_per_unit": catalog.price_of(prices, "HTTP 0 to 100000")},
        {"begin_range": 100_000, "end_range": "Inf", "price_per_unit": catalog.price_of(prices, "HTTP 100000 to Inf")},
    ])
    email = millions("numberOfEmailNotifications") * 1e6
    total += walk_tiers(email, [
        {"begin_range": 0, "end_range": 1000, "price_per_unit": catalog.price_of(prices, "SMTP 0 to 1000")},
        {"begin_range": 1000, "end_range": "Inf", "price_per_unit": catalog.price_of(prices, "SMTP 1000 to Inf")},
    ])

    total += millions("numberOfSQSNotifications") * 1e6 * catalog.price_of(prices, "Amazon SQS Notifications")
    total += millions("aws_Lambda") * 1e6 * catalog.price_of(prices, "AWS Lambda Notifications")
    total += millions("Amazon_Kinesis_Data_Firehose") * 1e6 * catalog.price_of(prices, "Amazon Kinesis Data Firehose Messages")

    push = millions("numberOfMobilePushNotifications")
    if push > 0:
        # The 1M/month free band is NOT in the map (only the "thereafter" rate is),
        # but sns.md reconciled a captured $220.92 with it applied. Mirroring the
        # capture, and saying so.
        notes.append("mobile push: 1M/month free band applied per sns.md's capture — not present in sns.json")
    push_rate = catalog.price_of(prices, "Apple Push Notification Service APNS iOS Notifications")
    total += max(0.0, push - 1.0) * 1e6 * push_rate

    total += as_float(cc_value(item, "publishAndDeliveryMessageScanning")) * catalog.price_of(prices, "Amazon SNS Message Scanning per GB")
    total += as_float(cc_value(item, "auditReporting")) * catalog.price_of(prices, "Amazon SNS Audit Reporting per GB")
    total += as_float(cc_value(item, "The_amount_of_outbound_payload_data_scanned_per_month")) * catalog.price_of(
        prices, "Amazon SNS Standard Payload Scanned Filtered per GB"
    )

    dt_field = next((k for k in cc(item) if k.startswith("simpleNotificationServiceSns_generated_")), None)
    if dt_field:
        load_dt = dt_price_loader("standardTopics", region_name, refresh)
        for entry in dt_entries(item, dt_field):
            if entry.get("entryType") != "OUTBOUND":
                continue
            cost, dt_notes = outbound_transfer_cost(load_dt, entry)
            total += cost
            notes.extend(dt_notes)
    return OracleResult(total, notes)


def recompute_sns_fifo(item: dict, region_name: str, *, refresh: bool = False) -> OracleResult:
    """SNS FIFO topic, per sns.md's reconciled formula with catalog rates."""
    mapping = catalog.fetch_mapping("fifoTopics", "sns", refresh=refresh)
    prices = catalog.region_prices(mapping, region_name)

    requests_m = as_float(cc_value(item, "numberOfRequests"))
    subscriptions = as_float(cc_value(item, "Number_of_subscriptions"), 1.0)
    message_kb = as_float(cc_value(item, "Average_message_size"), 4.0)
    retention_days = as_float(cc_value(item, "retentionperiod"))
    scanned_gb = as_float(cc_value(item, "The_amount_of_outbound_payload_data_scanned_per_month"))

    # Decimal KB->GB (1e6 KB per GB), NOT binary (1,048,576 KB per GiB). sns.md's
    # prose states the binary divisor but its own reconciled capture ($10.28 FIFO)
    # only closes with the decimal one: 10M x 4 KB = 40.0 GB, not 38.1 GiB. The
    # capture is the ground truth; see this module's note in sns.md (2026-09-06).
    published_gb = requests_m * 1e6 * message_kb / 1e6

    total = requests_m * 1e6 * catalog.price_of(prices, "Amazon SNS FIFO API Requests per Requests")
    total += published_gb * catalog.price_of(prices, "SNS FIFO Publish Payload per GB")
    total += requests_m * 1e6 * subscriptions * catalog.price_of(prices, "Amazon SNS FIFO Subscription Messages per Messages")
    total += published_gb * subscriptions * catalog.price_of(prices, "Amazon SNS FIFO Subscription Messages Payload per GB")
    total += published_gb * catalog.price_of(prices, "Amazon SNS FIFO Topics Archive Processing per GB")
    total += published_gb * (retention_days / 30.0) * catalog.price_of(prices, "Amazon SNS FIFO Topics Storage per GB month")
    total += scanned_gb * catalog.price_of(prices, "Amazon SNS Standard Payload Scanned Filtered per GB")
    return OracleResult(total)


ORACLES = {
    "ec2Enhancement": recompute_ec2,
    "amazonS3Standard": recompute_s3_standard,
    "awsS3DataTransfer": recompute_s3_data_transfer,
    "amazonSimpleQueueService": recompute_sqs,
    "standardTopics": recompute_sns_standard,
    "fifoTopics": recompute_sns_fifo,
}


# --------------------------------------------------------------------------- #
# body walk + report                                                            #
# --------------------------------------------------------------------------- #


def iter_line_items(body: dict):
    """Yield `(label, line_item, region_name)` for every priced line in the body.

    Group services (`subServices`) are descended into: each sub-service is matched
    by its own serviceCode, and inherits the group's regionName when it has none.
    """
    for key, item in (body.get("services") or {}).items():
        if not isinstance(item, dict):
            continue
        subs = item.get("subServices")
        if isinstance(subs, list):
            for index, sub in enumerate(subs):
                if not isinstance(sub, dict):
                    continue
                region_name = sub.get("regionName") or item.get("regionName")
                yield f"{key} > [{index}] {sub.get('serviceCode')}", sub, region_name
        else:
            yield key, item, item.get("regionName")


def evaluate(body: dict, *, refresh: bool = False) -> list[dict]:
    rows = []
    for label, item, region_name in iter_line_items(body):
        service_code = item.get("serviceCode") or ""
        stored = (item.get("serviceCost") or {}).get("monthly")
        recomputer = ORACLES.get(service_code)
        if recomputer is None:
            result = no_oracle(f"no oracle for serviceCode {service_code!r}")
        else:
            try:
                if not region_name:
                    region_name = catalog.region_display_name(item.get("region") or "")
                result = recomputer(item, region_name, refresh=refresh)
            except (CatalogError, ValueError, KeyError, OSError) as exc:
                result = no_oracle(f"recompute failed: {type(exc).__name__}: {exc}")

        row = {
            "key": label,
            "serviceCode": service_code,
            "stored": stored,
            "recomputed": result.recomputed,
            "delta": None,
            "delta_pct": None,
            "notes": result.notes,
        }
        if result.recomputed is not None and isinstance(stored, (int, float)):
            row["delta"] = result.recomputed - stored
            if stored:
                row["delta_pct"] = row["delta"] / stored * 100.0
            else:
                row["delta_pct"] = 0.0 if abs(row["delta"]) < 1e-9 else float("inf")
        rows.append(row)
    return rows


def breaches(rows: list[dict], tolerance_pct: float) -> list[dict]:
    return [r for r in rows if r["delta_pct"] is not None and abs(r["delta_pct"]) > tolerance_pct]


def _fmt(value, spec: str = ",.2f") -> str:
    return "—" if value is None else format(value, spec)


def render_table(rows: list[dict], tolerance_pct: float) -> str:
    header = ("line", "stored", "recomputed", "delta", "delta %")
    body = [
        (r["key"], _fmt(r["stored"]), _fmt(r["recomputed"]), _fmt(r["delta"], "+,.2f"),
         "—" if r["delta_pct"] is None else format(r["delta_pct"], "+.3f") + "%")
        for r in rows
    ]
    widths = [max(len(str(c)) for c in col) for col in zip(header, *body)] if body else [len(h) for h in header]
    lines = ["  ".join(h.ljust(w) for h, w in zip(header, widths)).rstrip(),
             "  ".join("-" * w for w in widths)]
    for row, cells in zip(rows, body):
        lines.append("  ".join(
            c.ljust(w) if i == 0 else c.rjust(w) for i, (c, w) in enumerate(zip(cells, widths))
        ).rstrip())
        for note in row["notes"]:
            lines.append(f"    ! {note}")
    failing = breaches(rows, tolerance_pct)
    covered = [r for r in rows if r["recomputed"] is not None]
    lines.append("")
    lines.append(
        f"{len(covered)}/{len(rows)} lines have an oracle; "
        f"{len(failing)} outside ±{tolerance_pct:g}%."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("body", help="path to a saveAs body JSON file")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit the rows as JSON")
    parser.add_argument("--refresh", action="store_true", help="ignore the catalog cache and re-download")
    parser.add_argument(
        "--tolerance", type=float, default=DEFAULT_TOLERANCE_PCT,
        help=f"allowed |delta%%| before exiting 1 (default {DEFAULT_TOLERANCE_PCT})",
    )
    args = parser.parse_args(argv)

    path = Path(args.body)
    try:
        body = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read body {path}: {exc}", file=sys.stderr)
        return 2

    rows = evaluate(body, refresh=args.refresh)
    if args.as_json:
        json.dump({"tolerance_pct": args.tolerance, "rows": rows}, sys.stdout, indent=2)
        print()
    else:
        print(render_table(rows, args.tolerance))
    return 1 if breaches(rows, args.tolerance) else 0


if __name__ == "__main__":
    raise SystemExit(main())

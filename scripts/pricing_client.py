#!/usr/bin/env python3
"""Generic AWS Price List API client for the aws-calc skill.

Returns parsed rate data for any AWS service exposed via the Pricing API.
Output is JSON to stdout — easy for Claude to read in a tool result and
feed back into a serviceCost calculation.

The Pricing API is only exposed in us-east-1 and ap-south-1; this client
always connects to us-east-1 and uses the regionCode filter to query
prices for any region.

Auth: respects the standard boto3 chain. For this project, set
AWS_PROFILE=zaintech-cloudtools (or pass --profile).

Usage:
    # Generic SKU lookup
    python3 pricing_client.py get-products \\
        --service-code AmazonEC2 \\
        --filter instanceType=t3.small \\
        --filter operatingSystem=Windows \\
        --filter regionCode=us-east-2 \\
        --filter tenancy=Shared \\
        --filter preInstalledSw=NA \\
        --filter capacitystatus=Used \\
        --filter licenseModel="No License required"

    # List filterable attributes for a service (helps when you don't know
    # which Field= names to use)
    python3 pricing_client.py describe-attributes --service-code AmazonRDS

    # Show possible values for one attribute
    python3 pricing_client.py get-attribute-values \\
        --service-code AmazonRDS --attribute databaseEngine
"""
import argparse
import json
import sys

import boto3
from botocore.config import Config

PRICING_REGION = "us-east-1"


def _client(profile: str | None):
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    # Bump the read timeout — the Pricing API can be slow on broad queries.
    return session.client("pricing", region_name=PRICING_REGION, config=Config(read_timeout=60))


def _parse_filters(raw: list[str]) -> list[dict]:
    """Turn ["k=v", "k2=v with spaces"] into TERM_MATCH filter dicts."""
    filters = []
    for item in raw:
        if "=" not in item:
            sys.exit(f"--filter must be key=value: got {item!r}")
        k, _, v = item.partition("=")
        filters.append({"Type": "TERM_MATCH", "Field": k.strip(), "Value": v.strip()})
    return filters


def _extract_rates(price_item: dict) -> list[dict]:
    """Pull out each priceDimension as a flat dict with the data Claude needs.

    A single SKU may have multiple OnDemand price dimensions when pricing is
    tiered (e.g. S3 storage: first 50TB, next 450TB, beyond). Reserved terms
    are returned alongside, keyed by lease length and purchase option so a
    caller can pick the relevant one.
    """
    rates = []
    attributes = price_item.get("product", {}).get("attributes", {})

    for term_kind, terms in price_item.get("terms", {}).items():
        for term_data in terms.values():
            term_attrs = term_data.get("termAttributes", {}) or {}
            for dim in term_data.get("priceDimensions", {}).values():
                ppu = dim.get("pricePerUnit", {})
                # USD first, fall back to whatever currency is present.
                price_str = ppu.get("USD") or next(iter(ppu.values()), None)
                if price_str is None:
                    continue
                rates.append({
                    "term_kind": term_kind,            # OnDemand / Reserved
                    "lease_length": term_attrs.get("LeaseContractLength", ""),
                    "purchase_option": term_attrs.get("PurchaseOption", ""),
                    "offering_class": term_attrs.get("OfferingClass", ""),
                    "description": dim.get("description", ""),
                    "unit": dim.get("unit", ""),
                    "begin_range": dim.get("beginRange", ""),
                    "end_range": dim.get("endRange", ""),
                    "price_per_unit": float(price_str),
                    "currency": "USD" if "USD" in ppu else next(iter(ppu)),
                })
    return rates, attributes


def cmd_get_products(args):
    client = _client(args.profile)
    filters = _parse_filters(args.filter or [])
    paginator = client.get_paginator("get_products")
    pages = paginator.paginate(
        ServiceCode=args.service_code,
        Filters=filters,
        PaginationConfig={"MaxItems": args.max_results},
    )

    skus = []
    for page in pages:
        for raw in page.get("PriceList", []):
            item = json.loads(raw)
            rates, attributes = _extract_rates(item)
            skus.append({
                "sku": item.get("product", {}).get("sku"),
                "attributes": attributes,
                "rates": rates,
            })

    json.dump({"service_code": args.service_code, "filters": filters, "skus": skus},
              sys.stdout, indent=2)
    print()


def cmd_describe_services(args):
    """List the attribute names you can filter on for a service."""
    client = _client(args.profile)
    response = client.describe_services(ServiceCode=args.service_code)
    services = response.get("Services", [])
    if not services:
        sys.exit(f"No service found with code {args.service_code!r}")
    json.dump({
        "service_code": services[0]["ServiceCode"],
        "filterable_attributes": services[0].get("AttributeNames", []),
    }, sys.stdout, indent=2)
    print()


def cmd_get_attribute_values(args):
    """Enumerate the valid values for a filterable attribute on a service.

    Useful when you've called describe-services and need to know e.g. what
    valid databaseEngine strings exist for AmazonRDS.
    """
    client = _client(args.profile)
    paginator = client.get_paginator("get_attribute_values")
    values = []
    for page in paginator.paginate(ServiceCode=args.service_code, AttributeName=args.attribute):
        for entry in page.get("AttributeValues", []):
            values.append(entry["Value"])
    json.dump({
        "service_code": args.service_code,
        "attribute": args.attribute,
        "values": values,
    }, sys.stdout, indent=2)
    print()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--profile", help="AWS profile (default: env / boto3 default chain)")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("get-products", help="Look up SKUs and rates")
    g.add_argument("--service-code", required=True, help="e.g. AmazonEC2, AmazonS3, AmazonRDS, AWSLambda")
    g.add_argument("--filter", action="append", help="key=value (repeatable)")
    g.add_argument("--max-results", type=int, default=20)
    g.set_defaults(func=cmd_get_products)

    d = sub.add_parser("describe-attributes", help="List filterable attribute names for a service")
    d.add_argument("--service-code", required=True)
    d.set_defaults(func=cmd_describe_services)

    v = sub.add_parser("get-attribute-values", help="List valid values for one attribute")
    v.add_argument("--service-code", required=True)
    v.add_argument("--attribute", required=True)
    v.set_defaults(func=cmd_get_attribute_values)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

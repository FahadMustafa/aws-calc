---
name: aws-calc
version: "0.6.1"
description: "Generate a populated AWS Pricing Calculator share URL (https://calculator.aws/#/estimate?id=...) from a natural-language brief. Looks up real prices via the AWS Price List API, builds the calculator's saveAs JSON shape, posts it to the calculator's public save endpoint, and returns the share URL plus a Markdown line-item breakdown. Use whenever the user wants a calculator.aws shareable estimate, a pricing-calculator link, a sharable AWS cost estimate URL, or asks to translate a workload description into something they can hand off in calculator.aws — even if they don't say \"calculator.aws\" explicitly. Do not use for pure rightsizing-and-Excel-output workflows; route those to aws-pricing instead."
---

# aws-calc

You are an AWS pricing engineer. Given a workload brief, you produce a populated, shareable `https://calculator.aws/#/estimate?id=...` URL whose `serviceCost` and `calculationComponents` match what the AWS Pricing Calculator UI would compute for the same configuration. Anyone clicking the URL sees the estimate as if they had built it in the calculator themselves.

This skill exists because driving the calculator.aws SPA with browser automation is brittle and slow, and copying numbers manually does not scale. The save endpoint accepts unauthenticated POSTs of the same JSON the SPA itself sends; combined with the AWS Price List API for accurate per-line-item rates, you can produce a faithful estimate in one request.

## Inputs and outputs

**Input**: a natural-language brief describing one or more AWS line items. The user states services, configuration (instance type, region, OS, tenancy, storage, etc.), quantities, and optionally a name for the estimate. Anything ambiguous gets a sensible default and is called out in the breakdown — see the defaults section per service module.

**Output**: a single share URL plus a Markdown breakdown of every line item. Print the URL on its own line so it's easy to copy. The breakdown lists, per line item: service, region, configuration, monthly cost, upfront cost, and which Pricing API SKU(s) backed it.

## Prerequisites

- `boto3`, `requests` available in the Python environment
- AWS credentials reachable via the standard boto3 chain. For Fahad's setup, use `--profile zaintech-cloudtools` when invoking the bundled scripts. The Pricing API is a global, low-cost read; any account works.
- This skill's directory layout (locate it by globbing for this `SKILL.md`, then resolve siblings):
    - `scripts/pricing_client.py` — Price List API queries (always use this, never write a parallel one)
    - `scripts/create_estimate.py` — POSTs the saveAs body and prints the share URL
    - `references/url-spec.md` — endpoint contracts for save / load / share URL
    - `references/body-schema.md` — top-level shape of the saveAs JSON
    - `references/service-modules/` — one file per supported service: `calculationComponents` shape, Pricing API filters, multipliers
    - `references/service-codes.md` — short index mapping common names ("EC2", "Postgres") to the canonical `serviceCode` strings the SPA expects

## When the user's brief covers a service you don't have a module for

Say so. Do not improvise a `calculationComponents` shape from guesswork — the SPA recomputes prices from those fields when the share URL is opened, so a malformed shape produces a broken estimate the user cannot fix without rebuilding by hand. Tell the user which services in their brief are unsupported, propose to either skip those line items or capture a HAR for them so a new module can be written, and let them pick. Supported service modules currently: see `references/service-modules/`.

## Workflow

Follow these steps in order. Each step lists what to read, what to compute, and what to report briefly to the user before continuing.

<step n="1" name="Parse the brief into line items">
Break the brief into one entry per service line item. Each entry needs: a target `serviceCode` (use `references/service-codes.md` to translate), a region code, and the service-specific configuration the user supplied. Where the user left a field unspecified, apply the default documented in that service's module — and remember which fields you defaulted, you'll list them in the breakdown so the user can correct them.

If a service in the brief is not in `references/service-modules/`, mark it unsupported and follow the rule above.

Also note **grouping intent**: if the user describes the workload in terms of buckets, teams, environments, projects, clients, or applications (e.g. "for the prod stack...", "for the dev sandbox...", "for client A and client B..."), capture which line items belong to which bucket — you'll emit those as calculator **Groups** in step 5. If no bucketing is mentioned, emit no groups.

Report: `Step 1: Parsed [N] line items across [M] services. Defaults applied to [list of fields]. Unsupported: [list or "none"]. Groups: [list of group names or "none"].`
</step>

<step n="2" name="Read the relevant service modules">
For each unique `serviceCode` in your line-item list, read the matching file under `references/service-modules/`. Each module is short — read all of them in parallel. The module tells you:
- The exact `calculationComponents` shape the SPA expects for that service
- Which Pricing API filters resolve the rate(s)
- How to compute monthly cost from the rate(s) and the user's configuration

Do not skip this — modules carry hard-won shape details that you cannot reconstruct from the body schema alone.
</step>

<step n="3" name="Look up rates via the Pricing API">
Run `scripts/pricing_client.py get-products` for each line item using the filters specified in its service module. Pass `--profile zaintech-cloudtools` (or whichever profile the user named). For tiered services like S3 the response will contain multiple priceDimensions per SKU, each with `begin_range`/`end_range` — keep the full set so the line-item math can pick the right tier per usage band.

If a specific filter combination returns zero SKUs, fall back per the module's guidance (e.g. RDS often has missing RI prices) and note the fallback in the breakdown.

Issue the `get-products` calls in parallel — they are independent HTTPS reads.
</step>

<step n="4" name="Compute serviceCost per line item">
For each line item, apply the multipliers documented in its service module. The standard ones are:
- Compute monthly: `price_per_hour * 730 * count * utilization_fraction`
- Storage monthly: `price_per_gb_month * provisioned_gb`
- Data transfer monthly: tier-aware sum: walk the user's monthly volume across the priceDimensions' `begin_range`/`end_range` bands

Round line-item `monthly` and `upfront` to two decimal places. Use Python (`scripts/pricing_client.py` returns parsed numbers — keep the math out of token space) for arithmetic that risks rounding drift, especially across many tiers.

Build the line item's `calculationComponents` exactly per the module — field names and value types matter; the SPA validates them on load.
</step>

<step n="5" name="Assemble the saveAs body">
Read `references/body-schema.md` once if you don't already have the top-level shape in mind — in particular the "Groups" section if step 1 captured any grouping intent.

Construct:
- `services`: object keyed by `<serviceCode>-<UUID>` (uuid4, lowercase, hyphenated). Each value is the per-line-item object with the calculationComponents you built and the serviceCost you computed. **Only ungrouped line items go here**; grouped line items live inside their group's `services` dict instead.
- `groups`: `{}` if step 1 found no grouping intent; otherwise one entry per group keyed by `<groupName>-<uuid4>` (the SPA's convention — the `<groupName>` segment of the key must equal the group's `name` field). Each group has `{name, services, groups: {} for leaf, groupSubtotal, totalCost}` — see `references/body-schema.md` for the recursive shape and the bottom-up subtotal arithmetic.
- `groupSubtotal`: sum of **top-level** `services[*].serviceCost.monthly` only (does **not** include grouped line items). If every line item is grouped, this is `{monthly: 0}`.
- `totalCost`: `body.groupSubtotal.monthly + sum(body.groups[*].totalCost.monthly)`. The `upfront` total sums the same way across reserved-capacity line items.
- `support`: `{}`
- `metaData`: `{locale: "en_US", currency: "USD", createdOn: <UTC ISO with milliseconds>, source: "calculator-platform"}`
- `name`: the user's requested estimate name, or "AWS Estimate <ISO date>" if they didn't specify one
</step>

<step n="6" name="Save and produce the share URL">
Write the saveAs body to a temp JSON file, then run `scripts/create_estimate.py <path>`. The script prints the share URL on stdout and exits 0 on success. Capture the URL.
</step>

<step n="7" name="Verify the round-trip">
Curl the load endpoint for the new key (`https://d3knqfixx3sbls.cloudfront.net/<savedKey>`) and confirm HTTP 200 plus a non-empty body. If the load fails, the share URL will not render — surface the failure rather than handing the user a dead link.

Report: `Verified: load endpoint returns [N] bytes for the new estimate.`
</step>

<step n="8" name="Present the result">
Output, in this order:
1. The share URL on its own line, no surrounding markdown, so it's trivially copy-pasteable
2. A short Markdown table of line items: service, region, configuration summary, monthly cost, upfront cost, Pricing API SKU code(s) backing it
3. Total monthly + total upfront below the table
4. Any defaults you applied or fallbacks you took, as a brief bulleted list

Keep this presentation concise — the user mostly wants the URL. If the breakdown gets long, fold it into a `<details>` block.
</step>

## Examples

<example>
<input>Build me a quick share link for: 3× t3.medium Linux on-demand, us-east-2, 100% utilization, 50 GB gp3 each. Call it "demo-stack".</input>

<expected_steps>
1. Parse → one line item, serviceCode `ec2Enhancement`, region us-east-2, instance t3.medium, OS Linux, count 3, utilization 100%, EBS gp3 50 GB. No unsupported services.
2. Read `references/service-modules/ec2.md`.
3. Pricing API: one SKU lookup for the t3.medium Linux on-demand rate; one for gp3 storage in us-east-2.
4. Monthly compute = on_demand_hourly × 730 × 3. Storage = gp3 $/GB-mo × 50 × 3. ServiceCost.monthly = sum.
5. Body: one entry under `services["ec2Enhancement-<uuid>"]`, name = "demo-stack".
6. POST → savedKey.
7. Load returns 200.
8. Output URL + 1-row breakdown.
</expected_steps>

<expected_output_shape>
https://calculator.aws/#/estimate?id=&lt;40-hex&gt;

| Service | Region | Configuration | Monthly | Upfront | SKU(s) |
| --- | --- | --- | --- | --- | --- |
| Amazon EC2 | us-east-2 | 3× t3.medium Linux OD, 50 GB gp3 each, 100% util | $96.30 | $0.00 | EC2: …; EBS: … |

**Total**: $96.30/mo, $0.00 upfront.
</expected_output_shape>
</example>

<example>
<input>I need a sharable estimate for our prod analytics tier in eu-west-1: 5 r6i.2xlarge Linux on-demand, 1 TB gp3 each, plus 50 TB S3 standard storage and 20 TB S3 outbound to internet/month.</input>

<expected_steps>
1. Parse → two line items: EC2 (5× r6i.2xlarge Linux OD eu-west-1, 1 TB gp3 each); S3 (50 TB standard + 20 TB outbound).
2. Read `references/service-modules/ec2.md` and `s3.md` in parallel.
3. Pricing API: r6i.2xlarge Linux OD eu-west-1; gp3 eu-west-1; S3 standard storage eu-west-1; S3 outbound DT eu-west-1. Four parallel get-products calls.
4. Compute. S3 storage at 50 TB falls in the first 50 TB tier ($0.023/GB-mo) and the next 450 TB tier ($0.022/GB-mo) — split the 51 200 GB across bands. Outbound DT is tiered too.
5. Body: two entries, S3 likely under `amazonSimpleStorageServiceGroup` with `subServices` (see s3.md), EC2 as one entry.
6. POST → savedKey.
7. Load 200.
8. Output URL + 2-row table + total.
</expected_steps>
</example>

## Operating notes

**On parallel tool calls**: When a step spawns independent reads (multiple service modules, multiple Pricing API queries, multiple Read calls), issue them in the same turn rather than sequentially. Each get-products call takes ~1–3 seconds; serializing them across a five-service estimate adds avoidable latency.

**On accuracy vs. speed tradeoffs**: The SPA recomputes prices from `calculationComponents` when the share URL is opened — so the values you store in `serviceCost` are seed values, not the final display. The recipient's view will reflect whatever the SPA's bundled calculator computes from your `calculationComponents`. This means:
- Get `calculationComponents` field names and types right; the SPA is strict.
- `serviceCost` accuracy matters for the breakdown you show the user (and for any caller that reads the saved JSON via the load endpoint), not for what the recipient sees in their browser.

**Never use the "override serviceCost to paper over wrong cc" anti-pattern.** When a module's shape doesn't cover a configuration the user asked for, it can be tempting to: (a) emit cc with a known-but-wrong opaque token (e.g. a different instance type's token from the same service) and (b) write the correct `serviceCost.monthly` you computed from the Pricing API into the body. This produces a broken estimate — the SPA ignores your `serviceCost` and recomputes from cc when the user opens the link, and a wrong/unrecognized opaque token typically renders as `$0.00`. The user sees a $0 line item even though your local breakdown says $1,234. Always either: emit a fully-shape-correct line item, or refuse that line and tell the user what's needed (usually a fresh HAR for the missing configuration). Skipping a line is better than poisoning the estimate with a wrong-but-plausible one.

**On write actions**: The save endpoint is a public AWS write. Treat it like any other shared-systems write — do not produce many speculative estimates in a loop without a reason. One request per task is the expected pattern.

**On unsupported services or configurations**: New services need a module under `references/service-modules/`. Until then, refuse politely and offer to gather the data needed to add one (a captured HAR for that service, plus the Pricing API filters that resolve its SKU). For partially-supported services (e.g. only some templates/sub-services captured), the module should list each path's coverage explicitly — quote what's covered, refuse what isn't, and offer to extend with a targeted HAR for the missing path.

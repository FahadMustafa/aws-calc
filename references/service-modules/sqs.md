# SQS (`amazonSimpleQueueService`)

Covers Amazon Simple Queue Service: Standard, FIFO, and Fair queue request charges, plus an EC2-style data-transfer block. One flat line item — no sub-services, no group wrapper.

## Line-item header

```json
{
  "serviceCode":  "amazonSimpleQueueService",
  "estimateFor":  "simpleQueueService",
  "version":      "0.0.47",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Simple Queue Service (SQS)",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  "standardQueueRequests": {"value": "10", "unit": "perMonth"},  // value is in MILLIONS — "10" means 10M requests/month
  "fifoQueueRequests":     {"value": "10", "unit": "perMonth"},  // millions/month; FIFO API priced separately
  "fairQueueRequests":     {"value": "10", "unit": "perMonth"},  // millions/month; Fair Queues feature
  "dataTransfer": {                                              // identical shape to EC2 dataTransferForEC2, but field is just "dataTransfer"
    "value": [
      {"entryType": "INBOUND",  "value": "10", "unit": "tb_month", "fromRegion": ""},
      {"entryType": "OUTBOUND", "value": "10", "unit": "tb_month", "toRegion":   ""}
    ]
  }
}
```

Notes:
- The `value` strings on the three request fields are **millions of requests per month**, despite the unit being labelled `perMonth`. The SPA's `configSummary` rendering (see below) literally inserts "X million per month".
- `dataTransfer` is the same `value: [...]` array of `INBOUND` / `OUTBOUND` entries used by EC2's `dataTransferForEC2`; only the wrapper field name differs. No `INTRA_REGION` entry is captured for SQS.
- With empty `fromRegion` / `toRegion`, the SPA leaves DT at $0 (same behaviour seen in the captured S3 estimate) — the entries round-trip but don't contribute to `serviceCost.monthly` until a real source/destination is picked.

## Pricing API filters

Pricing API ServiceCode is `AWSQueueService` (not `AmazonSQS`).

### Standard queue requests

```
--service-code AWSQueueService
--filter queueType=Standard
--filter regionCode=<region>
```

Returns one SKU with tiered OnDemand priceDimensions:
- Tier 1 (0–100B requests/mo): $0.40 / million
- Tier 2 (100B–200B): $0.30 / million
- Tier 3 (200B+): $0.24 / million

### FIFO queue requests

```
--service-code AWSQueueService
--filter "queueType=FIFO (first-in, first-out)"
--filter regionCode=<region>
```

Tiered priceDimensions:
- Tier 1 (0–100B): $0.50 / million
- Tier 2 (100B–200B): $0.40 / million
- Tier 3 (200B+): $0.35 / million

### Fair queue requests (Fair Queues)

```
--service-code AWSQueueService
--filter queueType=Fair
--filter regionCode=<region>
```

Single OnDemand priceDimension, flat: $0.10 / million in us-east-2. (No tiering on Fair as of capture.)

### Data transfer out to internet

```
--service-code AWSDataTransfer
--filter fromLocation=<regionName>
--filter toLocationType=External
--filter transferType=AWS Outbound
```

Same tiered structure used by EC2 (10 GB free → 10 TB / 40 TB / 100 TB / 350+ TB bands). Only consulted when the user supplies a non-empty `toRegion` / commits a destination.

## Multipliers / formula

Each request `value` is in **millions per month**, so:

```
std_millions  = float(standardQueueRequests.value)
fifo_millions = float(fifoQueueRequests.value)
fair_millions = float(fairQueueRequests.value)

monthly_std   = sum over std tiers  of (millions_in_tier  * tier_price_per_million)
monthly_fifo  = sum over fifo tiers of (millions_in_tier  * tier_price_per_million)
monthly_fair  = fair_millions * fair_price_per_million

monthly_dt_out = sum over DT tiers of (gb_in_tier * tier_price)   # only if toRegion/destination is set
serviceCost.monthly = monthly_std + monthly_fifo + monthly_fair + monthly_dt_out
serviceCost.upfront = 0
```

**Free tier:** SQS has 1M free requests/month across all queue types. The calculator does **not** subtract this in the captured estimate (10M Standard × $0.40 = full $4, not $3.60). Match the calculator's behaviour — do not pre-subtract the free tier when computing `serviceCost.monthly`.

Inbound data transfer is free; outbound to other AWS services in the same region is free.

## configSummary template

Match the captured wording exactly so the line-item card title renders cleanly:

```
Standard queue requests (<N> million per month), FIFO queue requests (<N> million per month), Fair queue requests (<N> million per month)
```

Omit clauses for queue types whose `value` is `"0"` or empty. Append DT clauses only if the user actually supplies a destination — the captured estimate had DT values entered but no destination, and the summary did not mention DT.

## Defaults

| Field | Default | Why |
|---|---|---|
| standardQueueRequests | `{"value": "0", "unit": "perMonth"}` | Silent users get nothing priced |
| fifoQueueRequests | `{"value": "0", "unit": "perMonth"}` | Same |
| fairQueueRequests | `{"value": "0", "unit": "perMonth"}` | Fair Queues is opt-in |
| dataTransfer INBOUND | `value: ""`, empty `fromRegion` | Calculator treats blank as 0 |
| dataTransfer OUTBOUND | `value: ""`, empty `toRegion` | Calculator treats blank as 0 |

If the user gives a single "messages per month" figure without specifying queue type, put it on `standardQueueRequests` (cheapest, most common) and flag the assumption.

## Verification

- **Capture source:** `/home/fahadmustafa/src/aws-calc/captures/calculator.aws_new.har` entry 346 (POST to `https://dnd5zrqcec4or.cloudfront.net/Prod/v2/saveAs`), service key `amazonSimpleQueueService-08629a9d-...`. Saved verbatim to `/tmp/aws_calc_onboard/amazonSimpleQueueService.json`.
- **End-to-end test:** us-east-2, all three queue types at 10M/month, DT in/out 10 TB with empty `fromRegion`/`toRegion`. Captured `serviceCost.monthly` = **$10.00**.
- **Math reproduces the $10.00 exactly:**
  - Standard: 10M × $0.40/M = **$4.00** (Tier 1, no free-tier deduction applied)
  - FIFO:     10M × $0.50/M = **$5.00**
  - Fair:     10M × $0.10/M = **$1.00**
  - DT out:   **$0.00** (empty `toRegion` → SPA doesn't price it; matches the S3 DT pattern documented in `s3.md`)
  - Total: $4 + $5 + $1 + $0 = $10.00. Verified within $0.00.
- **Fair queues:** `queueType=Fair` is the newer Fair Queues feature (separate SKU from Standard, no tiering, flat $0.10/M in us-east-2 — much cheaper than the $0.40/M the brief speculated). Verified via `pricing_client.py get-products --filter queueType=Fair`.
- Rates pulled live from `AWSQueueService` Pricing API on capture day; re-query if estimate is more than a few months old.

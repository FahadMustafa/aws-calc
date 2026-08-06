# Amazon Elastic Container Registry (`amazonElasticContainerRegistry`)

Single flat line item covering ECR private-registry image storage plus the data transfer associated with pulling images out of the registry. Pricing is intentionally simple: one flat per-GB storage rate, plus the standard regional outbound data transfer tiers. ECR replication, scan-on-push, and pull-through-cache costs are **not modeled** by this form — capture a fresh HAR before quoting them.

## Line-item header

```json
{
  "serviceCode":  "amazonElasticContainerRegistry",
  "estimateFor":  "template_0",
  "version":      "0.0.33",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Elastic Container Registry",
  "description":  null
}
```

`estimateFor` is the literal string `"template_0"` (with the underscore-zero suffix — pulled verbatim from a captured saveAs body; do not "fix" it to `"template"`).

## calculationComponents (verified shape)

```jsonc
{
  "amountofdatastored": {
    "unit":  "gb|month",
    "value": "10"                                     // GB stored in the registry per month, as string
  },
  "dataTransfer": {
    "value": [
      {
        "entryType":  "INBOUND",
        "fromRegion": "",                             // empty for internet inbound (free)
        "unit":       "tb_month",
        "value":      "10"
      },
      {
        "entryType": "OUTBOUND",
        "toRegion":  "External",                      // "External" = internet; or another region code for cross-region
        "unit":      "tb_month",
        "value":     "10"
      }
    ]
  }
}
```

Two fields. Both required for any non-trivial estimate. The `dataTransfer` value is always an array; you may include just one entry (e.g. OUTBOUND only) if INBOUND is zero, but capturing both is the safe pattern.

**`toRegion` values seen in captures**: `"External"` (= public internet). Cross-region peer values (e.g. `"us-west-2"`) are inferred from the analogous EC2/S3 DT forms but have **not** been round-tripped end-to-end through an ECR capture — verify before quoting cross-region pulls.

**Units**:
- `amountofdatastored.unit` is the literal string `"gb|month"` (pipe character, not a slash).
- `dataTransfer[*].unit` is `"tb_month"` (TB/month). The SPA also accepts `"gb_month"` in the wider DT family; stick to `tb_month` for high-volume registries to match captured shape.

## Pricing API filters

### ECR storage rate

```
--service-code AmazonECR
--filter regionCode=<region>
--filter "productFamily=EC2 Container Registry"
```

Returns multiple SKUs. The one you want is `usagetype=USE<region-prefix>-TimedStorage-ByteHrs` (e.g. `USE2-TimedStorage-ByteHrs` for us-east-2). It has a single OnDemand rate, e.g. `$0.10 per GB-month of data storage` in us-east-2. Other SKUs returned by the same query cover archive-tier storage, retrieval, and image-signing async actions — none of those are billed by this form, so ignore them.

There is no Reserved/SavingsPlan/upfront pricing for ECR — OnDemand is the only term.

### Outbound data transfer rates

ECR DT charges flow through the standard AWS regional outbound data transfer SKUs (same tiers as EC2 / S3 outbound to internet from the same region):

```
--service-code AWSDataTransfer
--filter fromLocation=<regionName>
--filter "transferType=AWS Outbound"
```

(Note: do **not** filter on `toLocationType=External` — the actual attribute value is `Other`. Omit the filter and the single matching SKU comes back.)

For `us-east-2` the tiered priceDimensions are:

| Range (GB) | Price/GB |
|---|---|
| 0 – 10,240 | $0.090 |
| 10,240 – 51,200 | $0.085 |
| 51,200 – 153,600 | $0.070 |
| 153,600 – ∞ | $0.050 |

Inbound (`AWS Inbound` transferType) is free everywhere.

## Multipliers / formula

```
storage_cost  = amountofdatastored_gb * storage_rate_per_gb_month
inbound_cost  = 0                                                     # free
outbound_cost = sum over priceDimensions of (gb_in_band * tier_price) # see caveat below
serviceCost.monthly = storage_cost + inbound_cost + outbound_cost
serviceCost.upfront = 0
```

### Caveat: the SPA does NOT apply the 100 GB / month free tier

The Pricing API's first-tier description for AWS outbound DT reads `"$0.090 per GB - first 10 TB / month data transfer out beyond the global free tier"`. AWS's public pricing page documents a 100 GB / month free-tier deduction on top of that, but **the AWS Pricing Calculator (the SPA) does not subtract those 100 GB**. It bills the full GB count against the tier rates.

Verified end-to-end against the captured slice:
- `amountofdatastored = 10 GB` × $0.10 = **$1.00**
- 10 TB outbound to internet from us-east-2 = 10,240 GB → entirely in tier 1 (0–10,240) → 10,240 × $0.09 = **$921.60** (matches `configSummary "Data transfer cost (921.6)"` exactly).
- Total: $1.00 + $921.60 = **$922.60** = captured `serviceCost.monthly`.

If you had applied the 100 GB free tier you would have gotten (10,240 − 100) × $0.09 = $912.60, total $913.60 — off by $9. So always charge against the full TB the user gave you. **This "no free tier" behavior is global to the SPA's DT computation, not ECR-specific** — apply the same rule for S3 outbound, EC2 outbound, and any other service whose calculator form takes a `dataTransfer` array.

### Caveat: configSummary "Data transfer cost (X)" is SPA-generated

The captured configSummary embeds `"Data transfer cost (921.6)"` as a literal substring. You do **not** need to pre-compute this and inject it — the SPA regenerates the line on load from the `dataTransfer` array and the regional tier table. Building the configSummary with a placeholder (or omitting that segment) is fine; the round-tripped saveAs body the SPA returns to the user will have the dollar number filled in. If you do include it pre-computed, match the formula above so the displayed number doesn't flip on first save.

## configSummary template

Match the captured phrasing so the line-item card renders cleanly:

```
DT Inbound: <"Not selected" if fromRegion="" else "<fromRegion>"> (<N> TB per month), DT Outbound: <"Internet" if toRegion="External" else "<toRegion>"> (<M> TB per month), Amount of data stored (<S> GB per month), Data transfer cost (<computed_dt_cost>)
```

`"Not selected"` is the literal string the SPA emits when `fromRegion` is empty — this is normal for inbound-from-internet (which is free anyway). For outbound, `toRegion=External` renders as `Internet`.

## Defaults

| Field | Default | Why |
|---|---|---|
| amountofdatastored | "0" gb\|month | Force the caller to declare registry size; defaults to "10" only if user says "small / typical" |
| dataTransfer INBOUND | "0" tb_month, fromRegion="" | Inbound is free — but the SPA expects the entry to exist with a value |
| dataTransfer OUTBOUND | "0" tb_month, toRegion="External" | Internet egress is the dominant ECR cost; prompt the user if they don't volunteer a number |

If the user mentions "pulling images to ECS / EKS in the same region", outbound to internet is 0 — intra-region pulls from the same-region registry to AWS compute are free. Only count outbound when images are pulled by something outside the region (CI runners on GitHub, on-prem nodes, cross-region clusters without VPC endpoints, etc.).

## Verification

- Shape captured from a working saveAs body in `captures/saveAs/per-service/amazonElasticContainerRegistry.json` for `us-east-2`.
- Pricing API filters above verified via `pricing_client.py get-products` against the live API on 2026-05-11: `AmazonECR` returns `$0.10 per GB-month` for `USE2-TimedStorage-ByteHrs`; `AWSDataTransfer` with `transferType=AWS Outbound` from `US East (Ohio)` returns the four-tier table above.
- End-to-end formula reproduces the captured `serviceCost.monthly` of **$922.60 exactly** ($1.00 storage + $921.60 outbound DT, no free-tier deduction).
- Cross-region outbound (`toRegion=<region-code>`) is **inferred** from analogous EC2/S3 DT forms — not yet captured for ECR. Verify before relying on it.
- ECR replication, image scanning (Basic = free; Enhanced via Inspector = separate line item under `amazonInspector`), and pull-through cache traffic are **not** part of this form. If the user asks about replication costs, add a separate cross-region DT line (or quote them manually) — the calculator's ECR form does not model them.

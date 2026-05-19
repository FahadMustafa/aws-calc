# AWS Shield (`awsShield`, Shield Advanced)

`serviceCode` is `awsShield`, `estimateFor` is `template`. This module covers **Shield Advanced** — Shield Standard is free and never appears in calculator.aws estimates. Flat line item, no `subServices` array; the four protected-resource-type usage values live as top-level fields in `calculationComponents`.

## Line-item header

```json
{
  "serviceCode":  "awsShield",
  "estimateFor":  "template",
  "version":      "0.0.22",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Shield",
  "description":  null,
  "serviceCost":  { "monthly": <computed> },
  "configSummary": "<see template below>"
}
```

Shield Advanced subscriptions are per-payer-account, not per-region — the SPA still requires a `region`, but the base subscription cost is invariant across regions. Pick the user's primary region for display purposes.

## calculationComponents (verified shape)

```jsonc
{
  "cloudFrontUsage":         {"value": "1", "unit": "tb|month"},   // CloudFront DT through Shield-protected distributions
  "LoadBalancingUsage":      {"value": "1", "unit": "tb|month"},   // ELB DT (ALB/NLB/CLB protected by Shield Advanced)
  "elasticIpUsage":          {"value": "1", "unit": "tb|month"},   // EIP DT through Shield-protected EC2/NAT
  "globalAcceleratorUsage":  {"value": "1", "unit": "tb|month"}    // Global Accelerator DT through Shield
}
```

Key-name quirks to copy verbatim:
- `LoadBalancingUsage` is **PascalCase** while the other three are camelCase — single one-letter outlier the SPA validates literally.
- Unit is `tb|month` (terabytes per month) for all four — the SPA converts to GB internally for the per-GB DDoS-DT rates.

There is no field for the base subscription — it is implicit (always included in `serviceCost.monthly`).

## Pricing API filters

```
--service-code AWSShield
--filter regionCode=<region>
```

Look for:
- A base subscription SKU (`usagetype` containing `Subscription` — monthly $3,000 flat across the standard plan tier).
- Four per-GB DDoS data-transfer SKUs, one per protected resource type. `usagetype` distinguishes them (e.g. `DDoSDT-Out-Bytes-CF`, `DDoSDT-Out-Bytes-ELB`, etc.); each has a tiered priceDimensions list with `beginRange`/`endRange` in GB/month (typically 0-100 TB, 100-400 TB, 400-1000 TB tiers).

Run `get-attribute-values --service-code AWSShield --attribute usagetype` to enumerate.

## Multipliers / formula

```
shield_base_monthly = $3,000.00                                # Shield Advanced flat subscription
ddos_dt_monthly     = sum over each resource type of:
    tiered(usage_in_GB, ddos_dt_rate_table[resource_type])

serviceCost.monthly = shield_base_monthly + ddos_dt_monthly
```

Tiered DT rates per GB (first tier 0-100 TB; **verify with `get-products` before quoting at higher tiers**):

| Resource type | First-tier rate per GB (approx) |
|---|---|
| CloudFront | $0.025 |
| ELB | ~$0.0375 — confirm from API |
| Elastic IP | ~$0.0375 — confirm from API |
| Global Accelerator | $0.05 |

Verified at eu-west-1 with 1 TB each of CF/ELB/EIP/GA → captured `serviceCost.monthly: $3,153.60`. Math reconstruction:
```
base                    = $3,000.00
CF       1000 GB * $0.025  = $25.60   (likely 1024 GB internally for "1 TB")
ELB      1000 GB * ~$0.0375 = $38.40
EIP      1000 GB * ~$0.0375 = $38.40
GA       1000 GB * $0.05    = $51.20
DT subtotal                  = $153.60
total                        = $3,153.60   ✓ matches exactly
```

The base subscription **is** included in `serviceCost.monthly` — the working assumption is now verified by the dollar arithmetic. The exact per-GB rates need confirmation from the live Pricing API; the breakdown above is best-fit reconstruction from one capture, and the ELB/EIP rates above are not the published headline numbers ($0.05/GB), suggesting the SPA may apply a different tier or that 1 TB is internally 1024 GB while my back-calc assumed 1000 GB. Re-derive with a second capture (e.g. only `cloudFrontUsage` set, all others zero) to isolate each per-resource rate.

## configSummary template

Match captured phrasing exactly — note **"Cloud Front"** with a space, not the usual "CloudFront":

```
Cloud Front Usage (<X> TB per month), Elastic Load Balancing (ELB) Usage (<X> TB per month), Elastic IP Usage (<X> TB per month), Global Accelerator Usage (<X> TB per month)
```

Always include all four segments even if some usage is `"0"` — the SPA always renders the full set when Shield Advanced is selected. Use `"0"` value for unused resource types.

## Defaults

| Field | Default | Why |
|---|---|---|
| cloudFrontUsage | "0" (TB/month) | Set only if user mentions CloudFront protection or names CloudFront usage volume |
| LoadBalancingUsage | "0" (TB/month) | Set only if user mentions ALB/NLB/CLB protection |
| elasticIpUsage | "0" (TB/month) | Set only if user mentions EIP-protected EC2 or NAT Gateway protection |
| globalAcceleratorUsage | "0" (TB/month) | Set only if user mentions GA protection |

If the user mentions "Shield" without "Advanced", **ask** — Shield Standard is free and does not need a calculator line item; only Shield Advanced has the $3,000/month subscription. Don't quote a $3,153.60+ estimate if the user actually meant the free tier.

Shield Advanced is also priced **per-organization** in AWS Organizations (one subscription covers all member accounts). If the user is estimating for a sub-account that's already covered by an org-level subscription, the base $3,000 should be excluded from this line item — flag this and ask before defaulting.

## Verification

- Captured HAR: `captures/calculator.aws_new_4.har` → `captures/saveAs/per-service/awsShield.json` (eu-west-1, single flat line item).
- Total `serviceCost.monthly: $3,153.60` reconstructs exactly as `$3,000 base + $153.60 DT` for 1 TB across each of the four resource types.
- Per-resource-type DT rates inferred from the single capture — confirm with a second capture that varies usage per resource (e.g. only CloudFront non-zero) before relying on the per-rate table for non-uniform mixes.
- **Shield Standard is NOT in scope** (free tier, no line item).
- **Organization-level subscription handling is NOT in scope** — module assumes a fresh per-account subscription. Flag and ask if the user is in an organization.

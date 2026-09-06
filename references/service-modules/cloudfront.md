# Amazon CloudFront (`amazonCloudFront`)

> **Scope — read first.** This module covers the **`productPackd1` form (CloudFront Flat-Rate Plans)** only. It is the calculator's "Flat Rate" template — a bundled monthly subscription (CDN + WAF + DDoS + DNS + logging + Lambda@Edge + S3 storage credits) sold as Free / Pro / Business / Premium tiers.
>
> Standard **usage-based CloudFront pricing** (per-GB data transfer, per-HTTPS-request, per-invalidation, etc.) lives in a separate `estimateFor: "CDN"` template that is **not yet captured**. If the user's brief implies CDN traffic, data transfer out, request volume, or anything metered — flag to the user, capture a HAR of the Pay-as-you-go form, and add a second module before producing the estimate. Do not silently substitute the flat-rate form for a metered workload.

## Line-item header

```json
{
  "serviceCode":  "amazonCloudFront",
  "estimateFor":  "productPackd1",
  "version":      "0.0.47",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon CloudFront",
  "description":  null
}
```

`estimateFor` is the literal string `"productPackd1"` (the template `id` in the service definition for the "Flat Rate" card; pulled from `https://d1qsjq9pzbk1k6.cloudfront.net/data/amazonCloudFront/en_US.json`). Capture is from `us-east-2` but the flat-rate prices are global — the form is region-agnostic (CloudFront is a global service; the region only labels the line item).

## calculationComponents (verified shape)

```jsonc
{
  "Enter_Quantity_hp":            {"value": "1"},  // Free Plan                   — $0/month each
  "Enter_Quantity_prop":          {"value": "1"},  // Pro Plan                    — $15/month each
  "Enter_Quantity_pp":            {"value": "1"},  // Business Plan               — $200/month each
  "Enter_Quantity_premp":         {"value": "1"},  // Premium Plan                — $1000/month each
  "Enter_Quantity_prem750m75tb":  {"value": "0"},  // Premium (750M / 75TB) Plan  — $1450/month each
  "Enter_Quantity_prem125b125tb": {"value": "0"},  // Premium (1.25B / 125TB) Plan— $2250/month each
  "Enter_Quantity_prem2b200tb":   {"value": "0"},  // Premium (2B / 200TB) Plan   — $3500/month each
  "Enter_Quantity_prem35b350tb":  {"value": "0"},  // Premium (3.5B / 350TB) Plan — $6000/month each
  "Enter_Quantity_prem6b600tb":   {"value": "0"}   // Premium (6B / 600TB) Plan   — $10000/month each
}
```

> **Form `0.0.47` (current) added five Premium usage-bundle tiers** to the original four plans. Older `0.0.45` estimates had only the first four fields. Emit all nine fields (string values, `"0"` for unused) to match the current form and survive recompute.

Field-to-plan mapping (decoded from `en_US.json` `mathsSection.operands` — the SPA's id-to-label binding is not obvious from the id strings alone, **and these prices are not in the Price List API**; re-verify when the header version changes):

| Field id | Plan | Monthly price (USD) | Validations |
|---|---|---|---|
| `Enter_Quantity_hp` | **Free Plan** | $0 | min=0, max=3, integer |
| `Enter_Quantity_prop` | **Pro Plan** | $15 | min=0, max=100, integer |
| `Enter_Quantity_pp` | **Business Plan** | $200 | min=0, max=100, integer |
| `Enter_Quantity_premp` | **Premium Plan** | $1000 | min=0, max=100, integer |
| `Enter_Quantity_prem750m75tb` | **Premium (750M req / 75 TB) Plan** | $1450 | min=0, max=100, integer |
| `Enter_Quantity_prem125b125tb` | **Premium (1.25B req / 125 TB) Plan** | $2250 | min=0, max=100, integer |
| `Enter_Quantity_prem2b200tb` | **Premium (2B req / 200 TB) Plan** | $3500 | min=0, max=100, integer |
| `Enter_Quantity_prem35b350tb` | **Premium (3.5B req / 350 TB) Plan** | $6000 | min=0, max=100, integer |
| `Enter_Quantity_prem6b600tb` | **Premium (6B req / 600 TB) Plan** | $10000 | min=0, max=100, integer |

Notes on the ids:
- `hp` ≈ "hobby plan" / free tier; `prop` = pro; `pp` = business (NOT pro — the SPA mnemonic is misleading); `premp` = premium; the `prem<reqs><tb>` ids are the new high-volume Premium bundles (the digits encode included requests and TB, e.g. `prem2b200tb` = 2 billion requests / 200 TB). Do not infer from the letters — always rely on this table.
- All values are **strings** in the POST body (e.g. `"1"`, not `1`). No `unit` key — these are unit-less counts.
- The form caps the **Free Plan at 3** (AWS account limit) and other plans at **100** each. Enforce the cap client-side and warn the user.

## Pricing API filters

**Not queryable, bundle-derived rates.** The four flat-rate plan prices ($0 / $15 / $200 / $1000) are **not exposed by the AWS Price List API**. They are hard-coded as `constant` operands inside the service-definition JSON the calculator loads at runtime:

```
https://d1qsjq9pzbk1k6.cloudfront.net/data/amazonCloudFront/en_US.json
```

Verified absent from:
- `AmazonCloudFront` Pricing API (productFamily values: `Data Transfer`, `Fee`, `RealTime`, `Request`, `Serverless` — none of which surface the flat-rate plans). The `Fee` family only contains StaticIP-IPv4/IPv6, custom SSL cert, and invalidation overage fees.
- `meteredUnitMaps/cloudfront/USD/current/cloudfront.json` (the calculator's runtime price map referenced by `mappingDefinitionName: "cloudfront"` and the `priceCF` component). This map contains usage-based rates (Request-Tier1/Tier2, DataTransfer-Out-Bytes) but no plan-level keys.

Practical implication: **bake the nine rates into this module** and re-verify if AWS changes the offering. The version number in the header (`0.0.47`) is the canary — bump the rate table when the captured version changes.

If/when a usage-based CloudFront module is added, that one **will** use the Pricing API with `--service-code AmazonCloudFront --filter productFamily="Data Transfer"` (and `Request`).

## Multipliers / formula

```
hp_cost            = Enter_Quantity_hp            * 0
prop_cost          = Enter_Quantity_prop          * 15
pp_cost            = Enter_Quantity_pp            * 200
premp_cost         = Enter_Quantity_premp         * 1000
prem750m75tb_cost  = Enter_Quantity_prem750m75tb  * 1450
prem125b125tb_cost = Enter_Quantity_prem125b125tb * 2250
prem2b200tb_cost   = Enter_Quantity_prem2b200tb   * 3500
prem35b350tb_cost  = Enter_Quantity_prem35b350tb  * 6000
prem6b600tb_cost   = Enter_Quantity_prem6b600tb   * 10000

serviceCost.monthly = sum of all nine plan costs
serviceCost.upfront = 0
```

No prorating, no tiers, no discounts. The SPA's `mathsSection` confirms this is a straight `multiplication` per plan followed by an `addition` (id `totCost`) across all nine. `decimalPlaces` on each multiplication is 2, but since the constants are integers and the quantities are integers, the result is always a whole-dollar integer in practice.

There is no annual / RI / Savings Plan term for these flat-rate bundles. CloudFront Security Savings Bundle (a separate commercial offering) is **not** this form — do not confuse them.

## configSummary template

**Original four plans — match the captured phrasing exactly:**

```
Free Plan (<H>), Pro Plan (<R>), Business Plan (<B>), Premium Plan (<M>)
```

Where:
- `<H>` = value of `Enter_Quantity_hp`
- `<R>` = value of `Enter_Quantity_prop`
- `<B>` = value of `Enter_Quantity_pp`
- `<M>` = value of `Enter_Quantity_premp`

**Five new Premium bundle tiers (`0.0.47`) — INFERRED, NOT CAPTURED. Verify before relying on this.** No saved estimate has round-tripped a new-tier line item yet (see Verification), so the exact summary phrasing the SPA emits for these is unconfirmed. Extrapolating the original pattern (full plan label + quantity in parentheses), the likely form appends the selected new tiers after the original four:

```
Premium (750M / 75TB) Plan (<P1>), Premium (1.25B / 125TB) Plan (<P2>), Premium (2B / 200TB) Plan (<P3>), Premium (3.5B / 350TB) Plan (<P4>), Premium (6B / 600TB) Plan (<P5>)
```

Where:
- `<P1>` = value of `Enter_Quantity_prem750m75tb`
- `<P2>` = value of `Enter_Quantity_prem125b125tb`
- `<P3>` = value of `Enter_Quantity_prem2b200tb`
- `<P4>` = value of `Enter_Quantity_prem35b350tb`
- `<P5>` = value of `Enter_Quantity_prem6b600tb`

The exact label text (spacing, "req"/"TB" wording, and whether the SPA abbreviates as above or spells out "750M req / 75 TB" per the mapping table) is unverified — capture a HAR the first time a user selects a new tier and reconcile this template to the captured string.

Note the **display order** (Free → Pro → Business → Premium → the five bundle tiers in ascending price) does not match the alphabetical order of the field ids — preserve this order to match the SPA's card rendering.

The SPA may also omit plans with quantity 0 from the summary in its own UI; the captured body included all four originals because all four were non-zero. When emitting an estimate with some zero quantities, the safer default is to still list at least the original four (matches the captured shape and the SPA accepts it); for the five new tiers, prefer listing only the non-zero ones until the emitted phrasing is captured and confirmed.

## Defaults

| Field | Default | Why |
|---|---|---|
| Enter_Quantity_hp | "0" | Free plan; user must opt in explicitly |
| Enter_Quantity_prop | "0" | Pro plan; user must opt in explicitly |
| Enter_Quantity_pp | "0" | Business plan; user must opt in explicitly |
| Enter_Quantity_premp | "0" | Premium plan; user must opt in explicitly |
| Enter_Quantity_prem750m75tb | "0" | Premium 750M/75TB bundle; opt in explicitly |
| Enter_Quantity_prem125b125tb | "0" | Premium 1.25B/125TB bundle; opt in explicitly |
| Enter_Quantity_prem2b200tb | "0" | Premium 2B/200TB bundle; opt in explicitly |
| Enter_Quantity_prem35b350tb | "0" | Premium 3.5B/350TB bundle; opt in explicitly |
| Enter_Quantity_prem6b600tb | "0" | Premium 6B/600TB bundle; opt in explicitly |

**Important:** unlike most modules, there is no sensible non-zero default. If the user says "add CloudFront" with no plan mention, prompt — do not guess a tier. A naive default of one Pro plan would silently add $15/month and a Business plan would add $200/month, neither of which the user asked for. If the user accepts a guess, prefer **1× Free Plan** ($0) as a placeholder.

The SPA refuses to commit a line item where all four quantities are 0 (the `totPlans` addition yields 0 and the `priceDisplay` shows $0); this module should mirror that — if total quantity is 0, skip the line item rather than emit a $0 entry.

## Verification

- Shape captured from a working saveAs body the calculator round-tripped on 2026-05-11 in `us-east-2`. Capture file: `captures/calculator.aws_new_2.har` (local capture, not in repo); extracted slice: `captures/saveAs/per-service/amazonCloudFront.json`.
- **Captured `serviceCost.monthly` = $1215.00** (form `0.0.45`). Reproduced exactly: `1×$0 (Free) + 1×$15 (Pro) + 1×$200 (Business) + 1×$1000 (Premium) = $1215`. Verified end-to-end.
- **2026-06 re-verification against live form `0.0.47`:** the four original prices are unchanged; the form added five Premium usage-bundle tiers ($1450 / $2250 / $3500 / $6000 / $10000). Module bumped to `0.0.47` and the nine-field shape above. The new tiers are not yet round-tripped through a saved estimate — capture a HAR if a user selects one, but the cc shape and prices are taken directly from the live service definition.
- All plan prices sourced from `templates[*].cards[0].mathsSection` `constant` operands in `https://d1qsjq9pzbk1k6.cloudfront.net/data/amazonCloudFront/en_US.json`.
- Field-to-plan mapping sourced from the same JSON (`operands[].variableId` → `variableLabel`). Not just from the field-id letters, which are misleading.
- The Pay-as-you-go template (`estimateFor: "CDN"`) exists in the same service-definition JSON but has **not** been captured end-to-end — adding a usage-based CloudFront module needs a fresh HAR with that form posted.
- Bundle.js (`captures/bundle.js`) does **not** contain `productPackd1`, `Enter_Quantity_*`, or `amazonCloudFront` form schema strings — verified via grep. The form schema is fetched at runtime from `d1qsjq9pzbk1k6.cloudfront.net`. Do not look in bundle.js for CloudFront form details.

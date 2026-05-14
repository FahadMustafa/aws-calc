# Amazon CloudFront (`amazonCloudFront`)

> **Scope — read first.** This module covers the **`productPackd1` form (CloudFront Flat-Rate Plans)** only. It is the calculator's "Flat Rate" template — a bundled monthly subscription (CDN + WAF + DDoS + DNS + logging + Lambda@Edge + S3 storage credits) sold as Free / Pro / Business / Premium tiers.
>
> Standard **usage-based CloudFront pricing** (per-GB data transfer, per-HTTPS-request, per-invalidation, etc.) lives in a separate `estimateFor: "CDN"` template that is **not yet captured**. If the user's brief implies CDN traffic, data transfer out, request volume, or anything metered — flag to the user, capture a HAR of the Pay-as-you-go form, and add a second module before producing the estimate. Do not silently substitute the flat-rate form for a metered workload.

## Line-item header

```json
{
  "serviceCode":  "amazonCloudFront",
  "estimateFor":  "productPackd1",
  "version":      "0.0.45",
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
  "Enter_Quantity_hp":    {"value": "1"},   // Free Plan      — qty (string), $0/month each
  "Enter_Quantity_pp":    {"value": "1"},   // Business Plan  — qty (string), $200/month each
  "Enter_Quantity_premp": {"value": "1"},   // Premium Plan   — qty (string), $1000/month each
  "Enter_Quantity_prop":  {"value": "1"}    // Pro Plan       — qty (string), $15/month each
}
```

Field-to-plan mapping (decoded from `en_US.json` `mathsSection.operands` — the SPA's id-to-label binding is not obvious from the id strings alone):

| Field id | Plan | Monthly price (USD) | Description from form | Validations |
|---|---|---|---|---|
| `Enter_Quantity_hp` | **Free Plan** | $0 | "For Development and small projects" | min=0, max=3, integer |
| `Enter_Quantity_prop` | **Pro Plan** | $15 | "For business applications" | min=0, max=100, integer |
| `Enter_Quantity_pp` | **Business Plan** | $200 | "For Development and small applications" | min=0, max=100, integer |
| `Enter_Quantity_premp` | **Premium Plan** | $1000 | "For Development of mission critical applications" | min=0, max=100, integer |

Notes on the ids:
- `hp` ≈ "hobby plan" / free tier; `prop` = pro; `pp` = business (NOT pro — the SPA mnemonic is misleading); `premp` = premium. Do not infer from the letters — always rely on this table.
- All values are **strings** in the POST body (e.g. `"1"`, not `1`). No `unit` key — these are unit-less counts.
- All four fields are present in the captured body even when quantity is 1 across the board; sending `"0"` for unused tiers is fine and reproduces the captured shape exactly.
- The form caps the **Free Plan at 3** (AWS account limit) and other plans at **100** each. Above 100 the SPA prompts the user to contact support for a quota increase, but the body itself is not validated server-side — we should enforce the cap client-side and warn the user.

## Pricing API filters

**Not queryable, bundle-derived rates.** The four flat-rate plan prices ($0 / $15 / $200 / $1000) are **not exposed by the AWS Price List API**. They are hard-coded as `constant` operands inside the service-definition JSON the calculator loads at runtime:

```
https://d1qsjq9pzbk1k6.cloudfront.net/data/amazonCloudFront/en_US.json
```

Verified absent from:
- `AmazonCloudFront` Pricing API (productFamily values: `Data Transfer`, `Fee`, `RealTime`, `Request`, `Serverless` — none of which surface the flat-rate plans). The `Fee` family only contains StaticIP-IPv4/IPv6, custom SSL cert, and invalidation overage fees.
- `meteredUnitMaps/cloudfront/USD/current/cloudfront.json` (the calculator's runtime price map referenced by `mappingDefinitionName: "cloudfront"` and the `priceCF` component). This map contains usage-based rates (Request-Tier1/Tier2, DataTransfer-Out-Bytes) but no plan-level keys.

Practical implication: **bake the four rates into this module** and re-verify if AWS changes the offering. The version number in the header (`0.0.45`) is the canary — bump the rate table when the captured version changes.

If/when a usage-based CloudFront module is added, that one **will** use the Pricing API with `--service-code AmazonCloudFront --filter productFamily="Data Transfer"` (and `Request`).

## Multipliers / formula

```
hp_cost     = Enter_Quantity_hp    * 0
prop_cost   = Enter_Quantity_prop  * 15
pp_cost     = Enter_Quantity_pp    * 200
premp_cost  = Enter_Quantity_premp * 1000

serviceCost.monthly = hp_cost + prop_cost + pp_cost + premp_cost
serviceCost.upfront = 0
```

No prorating, no tiers, no discounts. The SPA's `mathsSection` confirms this is a straight `multiplication` per plan followed by an `addition` (id `totCost`) across all four. `decimalPlaces` on each multiplication is 2, but since the constants are integers and the quantities are integers, the result is always a whole-dollar integer in practice.

There is no annual / RI / Savings Plan term for these flat-rate bundles. CloudFront Security Savings Bundle (a separate commercial offering) is **not** this form — do not confuse them.

## configSummary template

Match the captured phrasing exactly:

```
Free Plan (<H>), Pro Plan (<R>), Business Plan (<B>), Premium Plan (<M>)
```

Where:
- `<H>` = value of `Enter_Quantity_hp`
- `<R>` = value of `Enter_Quantity_prop`
- `<B>` = value of `Enter_Quantity_pp`
- `<M>` = value of `Enter_Quantity_premp`

Note the **display order** (Free → Pro → Business → Premium) does not match the alphabetical order of the field ids — preserve the captured order to match the SPA's card rendering.

The SPA may also omit plans with quantity 0 from the summary in its own UI; the captured body included all four because all four were non-zero. When emitting an estimate with some zero quantities, the safer default is to still list all four (matches the captured shape and the SPA accepts it).

## Defaults

| Field | Default | Why |
|---|---|---|
| Enter_Quantity_hp | "0" | Free plan; user must opt in explicitly |
| Enter_Quantity_prop | "0" | Pro plan; user must opt in explicitly |
| Enter_Quantity_pp | "0" | Business plan; user must opt in explicitly |
| Enter_Quantity_premp | "0" | Premium plan; user must opt in explicitly |

**Important:** unlike most modules, there is no sensible non-zero default. If the user says "add CloudFront" with no plan mention, prompt — do not guess a tier. A naive default of one Pro plan would silently add $15/month and a Business plan would add $200/month, neither of which the user asked for. If the user accepts a guess, prefer **1× Free Plan** ($0) as a placeholder.

The SPA refuses to commit a line item where all four quantities are 0 (the `totPlans` addition yields 0 and the `priceDisplay` shows $0); this module should mirror that — if total quantity is 0, skip the line item rather than emit a $0 entry.

## Verification

- Shape captured from a working saveAs body the calculator round-tripped on 2026-05-11 in `us-east-2`. Capture file: `captures/calculator.aws_new_2.har`; extracted slice: `captures/saveAs/per-service/amazonCloudFront.json`.
- **Captured `serviceCost.monthly` = $1215.00.** Reproduced exactly: `1×$0 (Free) + 1×$15 (Pro) + 1×$200 (Business) + 1×$1000 (Premium) = $1215`. Verified end-to-end.
- Plan prices ($0 / $15 / $200 / $1000) sourced from `templates[0].cards[0].mathsSection` `constant` operands in `https://d1qsjq9pzbk1k6.cloudfront.net/data/amazonCloudFront/en_US.json` (form version `0.0.45`).
- Field-to-plan mapping sourced from the same JSON (`operands[].variableId` → `variableLabel`). Not just from the field-id letters, which are misleading.
- The Pay-as-you-go template (`estimateFor: "CDN"`) exists in the same service-definition JSON but has **not** been captured end-to-end — adding a usage-based CloudFront module needs a fresh HAR with that form posted.
- Bundle.js (`captures/bundle.js`) does **not** contain `productPackd1`, `Enter_Quantity_*`, or `amazonCloudFront` form schema strings — verified via grep. The form schema is fetched at runtime from `d1qsjq9pzbk1k6.cloudfront.net`. Do not look in bundle.js for CloudFront form details.

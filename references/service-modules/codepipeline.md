# AWS CodePipeline (`awsCodePipeline`)

Single line item covering both pipeline types in one form: **V1 active pipelines** (flat per-pipeline monthly fee, with the first pipeline per account per month free) and **V2 action-execution minutes** (per-minute usage charge for V2 pipelines). The calculator combines both into one estimate row; if a workload uses only one pipeline type, leave the other input at `0`.

## Line-item header

```json
{
  "serviceCode":  "awsCodePipeline",
  "estimateFor":  "awscodepipeline",
  "version":      "0.0.18",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS CodePipeline",
  "description":  null
}
```

`estimateFor` is lowercase `awscodepipeline` (no camelCase) — pulled from a captured saveAs body. Do not normalize the casing to match `serviceCode`.

## calculationComponents (verified shape)

```jsonc
{
  "numberOfPipelines":    {"value": "10"},  // V1 active pipelines per account per month; no unit field
  "numberOfPipelines_v2": {"value": "10"}   // V2 action-execution minutes per account per month; no unit field
}
```

Two fields, both required. **Neither field has a `unit` key** — only `value`. Match the captured shape exactly; adding a unit may cause the SPA to misparse.

Naming gotcha: the V2 input is keyed `numberOfPipelines_v2` but it does **not** count V2 pipelines — its value is the total V2 **action-execution minutes** per account per month. The field name is the SPA's misnomer; reproduce it verbatim and document the unit semantics in `configSummary`.

## Pricing API filters

The Pricing API ServiceCode is `AWSCodePipeline` (capitalized — does not match the calculator's `awsCodePipeline`).

### V1 active-pipeline rate (after free tier)

```
--service-code AWSCodePipeline
--filter regionCode=<region>
--filter "productFamily=Active Pipeline"
```

Returns two SKUs: the chargeable one is `usagetype=<RegionPrefix>-activePipeline` with description `"First active pipeline"` (despite the name, its rate dimension is `"$1.00 per additional active pipeline"`). The other SKU (`usagetype=<RegionPrefix>-trialPipeline`, rate $0) covers the 30-day-trial pipeline carve-out and is not part of the steady-state formula. `price_per_unit` for the chargeable SKU is `1.0` in us-east-2. Unit: `pipelines`.

### V2 action-execution-minute rate

```
--service-code AWSCodePipeline
--filter regionCode=<region>
--filter "productFamily=Action Execution Minutes"
```

Returns one SKU (`usagetype=<RegionPrefix>-actionExecutionMinute`) with description `"$0.002 per action execution minute"`. `price_per_unit` is `0.002` in us-east-2. Unit: `minutes`.

There is no Reserved/SavingsPlan/upfront pricing for CodePipeline — OnDemand is the only term.

## Multipliers / formula

```
chargeable_v1_pipelines  = max(0, numberOfPipelines - 1)        # first V1 pipeline per account/month is free
monthly_v1               = chargeable_v1_pipelines * v1_rate    # $1.00/pipeline
monthly_v2               = numberOfPipelines_v2 * v2_rate       # $0.002/minute
serviceCost.monthly      = monthly_v1 + monthly_v2
serviceCost.upfront      = 0
```

V1 free-tier: the **first** active V1 pipeline per AWS account per month is free, so subtract 1 from `numberOfPipelines` before multiplying. If the user has only one V1 pipeline, the V1 component is $0. The free pipeline is account-wide (not per-region); when modeling multiple regions, only one region should claim the free pipeline — apply the `-1` to the largest-region row and bill the others at the full per-pipeline rate.

V2 has no free tier on action-execution minutes — bills from the first minute.

**Rounding caveat**: the SPA's line-item display rounds `serviceCost.monthly` for this service to an integer (not 2 decimals) when the fractional component is small. Captured ground truth shows `serviceCost.monthly = 9` for `numberOfPipelines=10, numberOfPipelines_v2=10`, where the true formula yields `9 × $1 + 10 × $0.002 = $9.02`. The $0.02 V2 fragment is dropped in the captured display. When emitting a saveAs body, set `serviceCost.monthly` to the integer-truncated total (`math.floor(monthly)` or `round(monthly)` if the fractional part is < $0.50) to match the SPA's behavior — the calculator will re-derive its own value on load, but emitting the rounded value avoids a visible mismatch in the line-item card.

## configSummary template

Match the captured phrasing so the line-item card renders cleanly:

```
Number of active pipelines of type V1 used per account per month (<N>), Number of action execution minutes used in pipeline of type V2 per account per month (<M>)
```

Both values appear in parentheses with no unit suffix. The phrasing reads "active pipelines of type V1" and "action execution minutes used in pipeline of type V2" — reproduce verbatim. Do not abbreviate to "V1 pipelines" or "V2 minutes"; the SPA's card layout expects the full noun phrases.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfPipelines | "1" | A single V1 pipeline; with the free-tier subtraction, this yields $0 — bump if the user has more |
| numberOfPipelines_v2 | "0" | V2 is opt-in per pipeline; don't model V2 minutes unless the user mentions V2, GitHub Actions-style triggers, or per-minute pricing |

If the user mentions "modern CodePipeline", "V2 pipelines", "action-level concurrency", or per-minute billing, treat the workload as V2 — estimate action-execution minutes from build/deploy duration × number of actions × runs per month, and put the total in `numberOfPipelines_v2`. If the user only mentions classic CodePipeline or doesn't specify, default to V1 and leave V2 at `0`.

## Verification

- Shape captured from a working saveAs body the calculator round-tripped on 2026-05-11 in `us-east-2` — per-service slice: `captures/saveAs/per-service/awsCodePipeline.json`.
- Pricing API filters above verified via `pricing_client.py get-products` against the live API: `Active Pipeline` family returns SKU `37SVZYDNWKHSDATH` with rate `$1.00` per additional active pipeline (unit `pipelines`); `Action Execution Minutes` family returns SKU `6XVWMQRY9F5WZBUK` with rate `$0.002` per action execution minute (unit `minutes`) — both for `regionCode=us-east-2`.
- Formula verified: `max(0, 10-1) × $1.00 + 10 × $0.002 = $9.00 + $0.02 = $9.02`, which the SPA displays as `$9` (integer rounding — see "Rounding caveat" above). Within the ±$0.05 reproduction tolerance.
- V1 free-tier subtraction is inferred from the public pricing page (the chargeable SKU's description says "$1.00 per **additional** active pipeline") and consistent with the captured `serviceCost.monthly=9` for 10 pipelines. Single-pipeline edge case (where chargeable_v1 = 0) is not yet round-tripped end-to-end — capture a fresh HAR with `numberOfPipelines=1` before relying on it for a customer quote.
- Multi-region free-tier handling (only one region claims the free pipeline) is inferred from AWS's account-level billing semantics, not verified via capture — when quoting a multi-region pipeline footprint, sanity-check against the public pricing page.

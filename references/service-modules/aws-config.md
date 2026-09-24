# AWS Config (`awsConfig`)

Covers the four AWS Config metering dimensions in a single line item: continuously-recorded configuration items, periodic (daily) recordings, Config rule evaluations, and Conformance Pack evaluations. All four are tracked as monthly counts.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| All four cc dimensions at "100" (continuous CIs, periodic CIs, rule evaluations, conformance-pack evaluations), us-east-2 | capture-verified | captured saveAs body — $1.70 matches exactly |
| Per-dimension rates | capture-verified | `pricing_client.py get-products` against `AWSConfig`, us-east-2 |
| Tiered bands above the first band for rule / conformance-pack evaluations | inferred | the capture sits inside the first band |
| Continuous vs periodic allocation across resource types | inferred | the calculator surfaces two independent counters and trusts the user to allocate |
| eu-central-1 (first-tier volumes) | recompute-verified | live SPA 2026-09-24, 42-line multi-account reference estimate (customer engagement, ID withheld), plus two earlier reference estimates |
| Regions other than us-east-2 and eu-central-1 | inferred | rates are stable across most commercial regions but the tier structure has changed before |

## Line-item header

```json
{
  "serviceCode":  "awsConfig",
  "estimateFor":  "awsConfig",
  "version":      "0.0.35",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Config",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  // Continuously-recorded configuration items per month. Each change to a
  // tracked resource emits one. Note the typo "Configration" (missing 'u')
  // — the SPA's schema uses that exact key; do NOT correct it.
  "numberOfConfigrationItemsRecorded":               {"value": "100"},

  // Periodic (daily) configuration items recorded per month. Used when
  // Config is set to record snapshots of resources on a fixed cadence
  // rather than only on change. Maps to the *RecordedDaily usage type.
  "Number_of_Periodic_Configuration_items_recorded": {"value": "100"},

  // Total Config rule evaluations per month across all rules. Tiered.
  "numberOfAWSConfigRuleEvaluations":                {"value": "100"},

  // Total Conformance Pack evaluations per month. Tiered.
  "numberOfConformancePackEvaluations":              {"value": "100"}
}
```

All four values are strings (decimal counts), even though they're integers. Use `"0"` rather than `""` to disable a dimension cleanly.

## Pricing API filters

Run `scripts/pricing_client.py get-products` with `--service-code AWSConfig` and the per-dimension usage type. The usage-type prefix is region-specific (`USE2-` for us-east-2, `USE1-` for us-east-1, `EUW1-` for eu-west-1, etc.) — use `get-attribute-values --service-code AWSConfig --attribute usagetype` to see the full list.

### Continuous configuration items recorded

```
--service-code AWSConfig
--filter regionCode=<region>
--filter usagetype=<PREFIX>-ConfigurationItemRecorded
```

Single OnDemand priceDimension. In us-east-2 today: **$0.003 per item**.

### Periodic (daily) configuration items recorded

```
--service-code AWSConfig
--filter regionCode=<region>
--filter usagetype=<PREFIX>-ConfigurationItemRecordedDaily
```

Single OnDemand priceDimension. In us-east-2 today: **$0.012 per item**.

### Config rule evaluations (tiered)

```
--service-code AWSConfig
--filter regionCode=<region>
--filter usagetype=<PREFIX>-ConfigRuleEvaluations
```

Three OnDemand priceDimensions with `begin_range`/`end_range`:
- 0 – 100,000 → $0.001 per evaluation
- 100,000 – 500,000 → $0.0008 per evaluation
- 500,000+ → $0.0005 per evaluation

### Conformance Pack evaluations (tiered)

```
--service-code AWSConfig
--filter regionCode=<region>
--filter usagetype=<PREFIX>-ConformancePackEvaluations
```

Three OnDemand priceDimensions, same tier breakpoints as rule evaluations:
- 0 – 100,000 → $0.001 per evaluation
- 100,000 – 500,000 → $0.0008 per evaluation
- 500,000+ → $0.0005 per evaluation

## Multipliers / formula

```
items_cost          = items_count       * 0.003   # flat
periodic_cost       = periodic_count    * 0.012   # flat
rule_eval_cost      = tiered(rule_evals, [(100000, 0.001), (400000, 0.0008), (Inf, 0.0005)])
conformance_cost    = tiered(conf_evals, [(100000, 0.001), (400000, 0.0008), (Inf, 0.0005)])

serviceCost.monthly = items_cost + periodic_cost + rule_eval_cost + conformance_cost
serviceCost.upfront = 0
```

Where `tiered(n, bands)` walks the count through each band, charging `min(remaining, band_width) * band_price` and continuing until `n` is exhausted. The tier boundaries are global per month per account in the real AWS bill; the calculator applies them as if the user's count is the total.

There is no free tier modeled here. AWS Config does offer free first-time recordings in some accounts, but the calculator does not subtract them.

## configSummary template

Match the captured phrasing so the saved estimate displays normally:

```
Number of configuration items recorded (<N>), Number of periodic configuration items recorded (<N>), Number of AWS Config rule evaluations recorded per month (<N>), Number of Conformance pack evaluations recorded per month (<N>)
```

Substitute the user's counts verbatim. If a dimension is `"0"`, still include it in the summary — the SPA expects all four fragments.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfConfigrationItemsRecorded | "0" | User must opt in to recording volume |
| Number_of_Periodic_Configuration_items_recorded | "0" | Periodic recording is off by default |
| numberOfAWSConfigRuleEvaluations | "0" | No rules assumed unless asked |
| numberOfConformancePackEvaluations | "0" | No conformance packs assumed unless asked |

If the user gives a single "Config items per month" figure without distinguishing continuous vs periodic, put it all in `numberOfConfigrationItemsRecorded` (the cheaper of the two at $0.003) and flag the assumption in the breakdown so they can correct.

## Verification

- Captured saveAs body (us-east-2, all four fields = "100") posted to the calculator returns `serviceCost.monthly = 1.70`.
- Hand math against verified Pricing API rates: `100·0.003 + 100·0.012 + 100·0.001 + 100·0.001 = 0.30 + 1.20 + 0.10 + 0.10 = 1.70` — exact match.
- Pricing API queries above were run against `us-east-2` on the current date and returned the rates documented here. Re-verify before promising other regions; the per-evaluation rates are stable across most commercial regions but the tier structure has been adjusted in the past.
- The distinction between *continuous* (`ConfigurationItemRecorded`) and *periodic* (`ConfigurationItemRecordedDaily`) maps to AWS Config's two recording modes (continuous recording on change vs. daily snapshots). Some resource types only support periodic; the calculator surfaces both as independent counters and trusts the user to allocate.

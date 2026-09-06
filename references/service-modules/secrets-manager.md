# AWS Secrets Manager (`awsSecretsManager`)

Single line item covering stored secrets (per secret-month) plus API request volume. The pricing model is intentionally simple — two flat rates, no tiers, no commitment options — so the module mostly exists to lock down the exact `calculationComponents` field names and units the SPA wants.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| Stored secrets + API requests (1 secret, 30-day duration, us-east-2) | capture-verified | captured saveAs body 2026-05-09 — $0.40 matches exactly |
| Per-secret and per-request rates | capture-verified | `pricing_client.py get-products` ($0.40/secret-month, $5e-06/request, us-east-2) |
| Partial-month prorating (`secretDuration` below 30) | inferred | read off the field name and unit; not round-tripped — capture with `secretDuration=15` first |

## Line-item header

```json
{
  "serviceCode":  "awsSecretsManager",
  "estimateFor":  "awssecretsmanager",
  "version":      "0.0.24",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Secrets Manager",
  "description":  null
}
```

`estimateFor` is lowercase `awssecretsmanager` (no camelCase). Pulled from a captured saveAs body — the SPA mismatches the serviceCode casing here, which is normal.

## calculationComponents (verified shape)

```jsonc
{
  "NumberOfSecrets": {"value": "1"},                          // count of secrets stored, as string
  "secretDuration":  {"value": "30", "unit": "day"},          // days each secret is retained in the month; 30+ = full month
  "numberOfAPIs":    {"value": "1", "unit": "perMonth"}       // total API calls (Get/Put/Describe/etc.) per month
}
```

Three fields, all required. `secretDuration.unit` is literally the string `"day"` (singular). `numberOfAPIs.unit` is `"perMonth"` — the SPA does not offer per-second/per-hour alternatives here, so always use that.

## Pricing API filters

The Pricing API ServiceCode is `AWSSecretsManager` (note the capitalization — does not match the calculator's `awsSecretsManager`).

### Per-secret storage rate

```
--service-code AWSSecretsManager
--filter regionCode=<region>
--filter productFamily=Secret
```

Returns one SKU with a single OnDemand priceDimension. `price_per_unit` is the dollar rate per secret per month (e.g. `0.40` in us-east-2). Description: `"$0.40 per Secret"`.

### API request rate

```
--service-code AWSSecretsManager
--filter regionCode=<region>
--filter "productFamily=API Request"
```

Returns one SKU. `price_per_unit` is the per-request rate (e.g. `5e-06` = $0.05 per 10,000 requests in us-east-2). Description: `"$0.05 per 10000 API Requests"`.

There is no Reserved/SavingsPlan/upfront pricing for Secrets Manager — OnDemand is the only term.

## Multipliers / formula

```
secret_months   = NumberOfSecrets * min(secretDuration / 30, 1)
monthly_secret  = secret_months * secret_rate_per_month
monthly_api     = numberOfAPIs * api_rate_per_request
serviceCost.monthly = monthly_secret + monthly_api
serviceCost.upfront = 0
```

The `secretDuration` value prorates storage when a secret lives less than a full month — e.g. `secretDuration=15 day` charges half the secret rate. At `secretDuration=30` (or any value ≥30) it's a full month. The SPA caps at 1 month per secret per line item; if the user describes a multi-month engagement, scale via `NumberOfSecrets` × months in their narrative, not by inflating `secretDuration` past 30.

API requests bill per call (not per 10k bundle) — the public list price is quoted per 10,000 but the underlying rate is `$0.000005 / request`. At single-digit request counts the cost rounds to $0 in the SPA's two-decimal display.

## configSummary template

Match the captured phrasing so the line-item card renders cleanly:

```
Number of secrets (<N>), Duration each secret will be stored (<D> day), Number of API calls (<A> perMonth)
```

The unit suffix on the duration string is the literal lowercase singular `"day"` to match the `secretDuration.unit` value.

## Defaults

| Field | Default | Why |
|---|---|---|
| NumberOfSecrets | "1" | Single-secret estimates are the most common quick-quote case |
| secretDuration | "30" day | Full-month billing — matches a steady-state workload |
| numberOfAPIs | "1" perMonth | Minimal API surface; bumps the user toward real usage if they care |

If the user mentions rotation, app fleets, or microservices pulling secrets, prompt for a realistic `numberOfAPIs` — the rate is small but it can dominate at high call volumes (e.g. 10M calls/month = $50, well above the secret rate).

## Verification

- Shape captured from a working saveAs body the calculator round-tripped on 2026-05-09 in `us-east-2`.
- Pricing API filters above verified via `pricing_client.py get-products` against the live API: `Secret` product returns `$0.40` per secret-month, `API Request` product returns `$5e-06` per request — both for `regionCode=us-east-2`.
- Formula verified: `1 secret × (30/30) × $0.40 + 1 API × $5e-06 = $0.400005`, which the SPA displays as `$0.40` — matches the captured `serviceCost.monthly` of $0.40 exactly.
- Partial-month prorating (secretDuration < 30) is inferred from the field name and unit — not yet round-tripped end-to-end. Capture a fresh HAR with `secretDuration=15` before relying on it for a customer quote.

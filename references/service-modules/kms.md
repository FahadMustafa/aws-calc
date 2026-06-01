# AWS KMS (`awsKeyManagementService`)

`serviceCode` is `awsKeyManagementService`, `estimateFor` is `kms`. Flat line item, no `subServices` array. All six priced dimensions are top-level keys in `calculationComponents`.

This module covers **customer-managed CMKs and request volume**. It does **not** cover external key store (XKS) hourly fees, custom key stores backed by CloudHSM, or HMAC-only KMS keys (which have a distinct pricing schedule). Capture HAR before quoting those.

## Line-item header

```json
{
  "serviceCode":  "awsKeyManagementService",
  "estimateFor":  "kms",
  "version":      "0.0.20",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Key Management Service",
  "description":  null,
  "serviceCost":  { "monthly": <computed> },
  "configSummary": "<see template below>"
}
```

## calculationComponents (verified shape)

```jsonc
{
  "numberOfCmk":                              {"value": "5"},        // customer-managed CMKs (AWS-managed CMKs are free; don't count them)
  "numberOfSymmetricRequests":                {"value": "2000000"},  // total monthly Encrypt/Decrypt/GenerateDataKey on symmetric KMS keys
  "numberOfAsymmetricRequestsExceptRsa2048":  {"value": "1000"},     // ECC + RSA 3072/4096 sign/verify/encrypt/decrypt
  "numberOfAsymmetricRsaRequests":            {"value": "1000"},     // RSA 2048 sign/verify/encrypt/decrypt only
  "numberOfEccGenerateDataKeyPairRequests":   {"value": "1000"},
  "numberOfRsaGenerateDataKeyPairRequests":   {"value": "1000"}
}
```

All six values are plain integers (no `unit`). The SPA treats them as monthly totals — multiply through the per-10K rate, **no per-second / per-hour normalization needed**.

Key-name quirks to copy verbatim:
- `numberOfCmk` — singular `Cmk`, not `CMKs` or `Cmks`.
- `numberOfAsymmetricRsaRequests` is **RSA 2048 only** (not all RSA). RSA 3072 and RSA 4096 sign/verify/encrypt/decrypt requests roll up under `numberOfAsymmetricRequestsExceptRsa2048` along with ECC sign/verify.
- The `Ecc` and `Rsa` GenerateDataKeyPair counters are split because the per-pair generation rates differ (RSA is more expensive to generate than ECC).
- The free tier (20K symmetric requests/month, AWS-managed CMK storage free) is **not** subtracted by the SPA — the captured estimate charges from the first request.

## Pricing API filters

```
--service-code awskms
--filter regionCode=<region>
```

Note the service-code is lowercase `awskms` in the Pricing API, not the SPA's camelCase `awsKeyManagementService`.

Look for SKUs by `usagetype`:
- `<region>-KMS-Keys` (per CMK-month, $1.00 in standard regions)
- `<region>-KMS-Requests` (per 10,000 symmetric requests, $0.03)
- `<region>-KMS-Requests-Asymmetric` (per 10,000 asymmetric ops, $0.03 for ECC/RSA-3072/4096, $0.15 for RSA-2048 — the higher tier requires filtering by `keyType`)
- `<region>-KMS-GenerateDataKeyPair-ECC` and `-RSA` (per pair generated, rates differ by key spec)

Run `get-attribute-values --service-code awskms --attribute usagetype` to enumerate.

## Multipliers / formula

```
cmk_monthly           = numberOfCmk * cmk_per_key_per_month                     # $1.00/CMK/month standard
sym_req_monthly       = numberOfSymmetricRequests / 10000 * sym_per_10k         # $0.03/10K standard
asym_other_monthly    = numberOfAsymmetricRequestsExceptRsa2048 / 10000 * asym_other_per_10k   # $0.03/10K
asym_rsa2048_monthly  = numberOfAsymmetricRsaRequests / 10000 * asym_rsa_per_10k               # $0.15/10K
ecc_pair_monthly      = numberOfEccGenerateDataKeyPairRequests / 10000 * ecc_pair_per_10k
rsa_pair_monthly      = numberOfRsaGenerateDataKeyPairRequests / 10000 * rsa_pair_per_10k

serviceCost.monthly = cmk_monthly
                    + sym_req_monthly
                    + asym_other_monthly
                    + asym_rsa2048_monthly
                    + ecc_pair_monthly
                    + rsa_pair_monthly
```

Verified at us-east-2 with the captured inputs (the per-region rate literals below — $1.00/CMK-month, $0.03/10K, $0.15/10K, etc. — are **us-east-2 only**; rates differ by region, e.g. GovCloud and some opt-in regions, so look them up per region with `get-products` rather than reusing these example literals):
```
cmk          = 5 * $1.00            = $5.00
sym req      = 2,000,000/10000 * $0.03 = $6.00
asym other   = 1000/10000 * $0.03      = $0.003
asym rsa2048 = 1000/10000 * $0.15      = $0.015
ecc pair     = 1000/10000 * $0.10      = $0.01
rsa pair     = 1000/10000 * $12.00     = $1.20    # back-calculated; see below
                                       --------
                                       = $12.23   ✓ matches captured $12.23
```

The RSA GenerateDataKeyPair rate of **$12.00 per 10,000 pairs** is back-calculated from this single capture (`$12.23 captured - $11.03 from the other five lines = $1.20 residual / 0.1 = $12.00/10K`). This is **higher** than the per-10K headline rates for sign/verify operations because RSA 2048 key-pair generation is computationally expensive; AWS prices it closer to per-pair than per-request. **Confirm via the Pricing API before quoting** — and capture a second saveAs with `numberOfRsaGenerateDataKeyPairRequests` set to zero to verify the residual really attributes to RSA pair generation (not to a free-tier subtraction or an unmodeled SKU).

> **CAVEAT — single-sample inference.** The $12.00/10K RSA `GenerateDataKeyPair` rate is inferred from exactly ONE capture and is not a published, verified number. Before quoting **any** non-trivial RSA key-pair-generation volume, pull the live rate with `scripts/pricing_client.py get-products` for the user's region and use that value. **Never quote from the baked-in $12/10K number** — it exists only to make the worked example reconcile.

## configSummary template

Match captured phrasing exactly:

```
Number of customer managed Customer Master Keys (CMK) (<N>), Number of symmetric requests (<N>), Number of asymmetric requests except RSA 2048 (<N>), Number of asymmetric requests involving RSA 2048 (<N>), Number of ECC GenerateDataKeyPair requests (<N>), Number of RSA GenerateDataKeyPair requests (<N>)
```

Always include all six segments even if some counts are `"0"` — the SPA always renders the full set. Don't drop zero-count dimensions like other flat services do.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfCmk | "1" | At least one CMK is always implied when KMS is mentioned; users rarely list count explicitly |
| numberOfSymmetricRequests | "0" | Symmetric volume varies wildly; ask before defaulting (small workloads: 1M, medium: 10M, large: 100M+) |
| numberOfAsymmetricRequestsExceptRsa2048 | "0" | Most workloads use symmetric KMS; only set if user mentions ECC or RSA-3072/4096 |
| numberOfAsymmetricRsaRequests | "0" | Same — RSA 2048 only if user explicitly mentions RSA |
| numberOfEccGenerateDataKeyPairRequests | "0" | Pair generation is rare; only for envelope-encryption-with-KEKs workflows |
| numberOfRsaGenerateDataKeyPairRequests | "0" | Per-pair cost is high (~$12/10K) — never default a non-zero value |

If the user says "KMS" without specifying request volume, **ask** — symmetric request volume can move the estimate by 4+ orders of magnitude.

If the user mentions custom key stores (CloudHSM-backed) or external key stores (XKS), refuse to quote from this module and capture a HAR for those configurations — they add hourly per-key fees this module does not handle.

## Verification

- Captured HAR: `captures/calculator.aws_new_5.har` → `captures/saveAs/per-service/awsKeyManagementService.json` (us-east-2, single flat line item).
- Total `serviceCost.monthly: $12.23` reconstructs exactly using the inferred rate table above. Five of the six rate-table entries match standard AWS-published values; the sixth (RSA GenerateDataKeyPair at ~$12/10K) is back-calculated and **must be confirmed against the live Pricing API before quoting non-trivial RSA pair-generation volume**.
- AWS-managed CMKs are free and not modeled here (don't add a hidden +$1 for them).
- HMAC KMS keys, external key store (XKS) hourly fees, and CloudHSM-backed custom key stores are **NOT covered** — capture HAR before quoting those.

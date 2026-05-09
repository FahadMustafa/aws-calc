# Recon notes

Scratch observations during the spike. Final write-up lives in `findings.md`.

## Phase A — Discovery

### Bundle grep results
See `captures/bundle-grep.txt`. Headlines:

- Save endpoint: `POST https://dnd5zrqcec4or.cloudfront.net/Prod/v2/saveAs`
- Load endpoint: `GET  https://d3knqfixx3sbls.cloudfront.net/<savedKey>`
- Share URL template (from bundle): `https://calculator.aws/#/estimate?id=<savedKey>`
- 18 `IdentityPoolId` references in bundle.js — no concrete pool ID value found by regex. Auth turns out to be unnecessary anyway (see Phase B).

### Manual HAR capture
HAR file: `captures/calculator.aws.har` (137 MB, 340 entries). Captured during a session that built EC2 (×2) + RDS PostgreSQL + S3 + VPC and clicked Save and share.

## Phase B — Analysis

### Endpoint candidates → confirmed

| Purpose | Method | URL | Auth |
|---|---|---|---|
| Create estimate | POST | `https://dnd5zrqcec4or.cloudfront.net/Prod/v2/saveAs` | **none** |
| Load estimate | GET  | `https://d3knqfixx3sbls.cloudfront.net/<savedKey>` | **none** |

CloudFront-fronted API Gateway (`X-Amz-Cf-Id`, `x-amz-apigw-id`, `Via: CloudFront` all present on the saveAs response). Stage = `Prod`. Lambda proxy integration (response is the classic `{statusCode, body, headers, isBase64Encoded}` envelope with `body` as a stringified JSON).

### Auth mechanism
**No auth.** The captured POST has no `Authorization`, no `X-Api-Key`, no SigV4 (`X-Amz-Date` / `X-Amz-Security-Token`) header. Just CORS:

- `Origin: https://calculator.aws`
- `Referer: https://calculator.aws/`
- `Content-Type: application/json`

Preflight OPTIONS returns `Access-Control-Allow-Origin: *` and `Allow-Methods: POST,OPTIONS`. `Allow-Headers` lists `Authorization, X-Api-Key, X-Amz-Security-Token` but those are CORS allowlist boilerplate — not actually required. Confirmed by re-fetching the load URL with bare curl, no headers, HTTP 200.

### Request schema (saveAs)
Top-level keys observed in the captured body:

- `name` — string, free-form ("My Estimate")
- `services` — object keyed by `<serviceCode>-<uuid-v4>`. Each value has:
    - `serviceCode` (e.g. `ec2Enhancement`, `amazonRDSPostgreSQLDB`, `amazonSimpleStorageServiceGroup`, `amazonVirtualPrivateCloud`)
    - `region` (e.g. `us-east-2`)
    - `regionName` (display, e.g. `US East (Ohio)`)
    - `serviceName` (display, e.g. `Amazon EC2`)
    - `estimateFor` (sub-form id, e.g. `template`, `rdsForPostgreSQL`)
    - `version` (form schema version, e.g. `0.0.68`)
    - `description` (nullable)
    - `calculationComponents` — service-specific input fields (the values the user typed)
    - `serviceCost` — `{monthly, upfront}` — pre-computed client-side
    - `configSummary` — human-readable settings string
    - For grouped services (S3, VPC): `subServices` array of mini-line-items, each with own `serviceCost`
- `groups` — `{}` in our capture (no estimate groups created)
- `groupSubtotal` — `{monthly, upfront}`
- `totalCost` — `{monthly, upfront}` — sum of services
- `support` — `{}`
- `metaData` — `{locale: "en_US", currency: "USD", createdOn: "<ISO>", source: "calculator-platform"}`

**Critical implication:** the SPA does pricing math client-side. The save endpoint just persists the JSON blob; it does not validate or recompute costs. Whatever `serviceCost` and `totalCost` you send is what gets shown on load. (Sample preserved at `poc/sample_input.json`.)

### Response schema (saveAs)
Lambda-proxy envelope:

```json
{"statusCode":201,
 "body":"{\"message\":\"The file name is <40hex>\",\"savedKey\":\"<40hex>\"}",
 "isBase64Encoded":false,
 "headers":{...}}
```

`savedKey` = 40 lowercase hex chars (looks like SHA-1 length). Verified: SHA-1 of the captured raw body = `d02adc36...`, but the returned savedKey was `55bea3f0...` — so the server normalizes (re-serializes) the body before hashing, or salts it, or generates randomly. We don't need to predict it; we read it from the response.

### Share-URL derivation
From bundle.js: `savedKey;...e=r.replace(/(id=).*?(&|$)/, "id=" + savedKey + "$2")`

The client takes `window.location.href` and substitutes the `id=` query param. Final form:

    https://calculator.aws/#/estimate?id=<savedKey>

Verified: GET `https://d3knqfixx3sbls.cloudfront.net/55bea3f03cae87b696e30e0f5e45fcb288eeb43d` → HTTP 200, returns the saved estimate JSON (10745 bytes, pretty-printed). So the load CDN host is backed by the same store that saveAs writes to (almost certainly an S3 bucket keyed by hash, fronted by CloudFront).

## Phase C — Replay PoC

`poc/create_estimate.py` + `poc/requirements.txt` (just `requests`). Verified end-to-end: 3 sample runs produced distinct share URLs, mutated input round-tripped, browser render confirmed by user.

## Phase D — aws-calc skill

Installed at `~/.claude/skills/aws-calc/`. Architecture: AWS Price List API for rates (via `boto3`, profile `zaintech-cloudtools`) + captured saveAs body shapes for `calculationComponents` + the PoC for the actual save POST. Verified: skill's formula for EC2 OnDemand + gp3 (price × 730 + price × GB) reproduces the captured estimate's serviceCost.monthly exactly ($68.62).

Service modules shipped with v1: EC2, RDS Postgres, S3 (group), VPC (group). Extension recipe in `references/service-modules/_template.md`. Critical finding from the user: the SPA **recomputes** prices on load (it offers "update with latest prices"), so `calculationComponents` accuracy is what matters; `serviceCost` numbers in the saved JSON are seed values.

Why we did **not** mine the SPA's price catalogs (`calculator.aws/pricing/2.0/meteredUnitMaps/...`): comparison test showed identical numbers vs the official Pricing API for t3.small Windows OD us-east-2 ($0.0392/hr both sides). The Pricing API covers all 436 calculator services with one auth model and one query shape; the SPA catalogs are just a pre-shaped derivative. Using the official source removed an entire layer of reverse-engineering.

Why we did **not** extend the existing `aws-pricing` skill: it's hard-coded to `ServiceCode="AmazonEC2"` and produces an Excel deliverable. Different output shape, different purpose. `aws-calc` ships its own thin Pricing API helper at `scripts/pricing_client.py`.

## Open questions / surprises

- **Surprise: zero auth.** I expected SigV4 + Cognito unauth credentials based on the AWS-hosted-SPA pattern. The save endpoint is wide open to anyone. (Some kind of WAF rate-limiting almost certainly exists upstream.)
- **Surprise: client-side pricing math.** The save body contains `serviceCost`/`totalCost` that the server stores verbatim. A malicious client could persist an estimate with arbitrary numbers. The shared URL would show those numbers, but anyone re-opening it would only see what was sent — they can't re-derive the price unless the SPA recomputes from `calculationComponents` on load (worth checking).
- The `prod-api.builder-ui.pricing-calculator.aws.a2z.com/v2/services` endpoint shows up in bundle.js but is never called by the public flow. Possibly used by a privileged builder/admin UI.
- `savedKey` collision behavior unknown — if two clients save identical bodies, do they get the same key? Likely yes if the server hashes content; would need a duplicate-save test to confirm.

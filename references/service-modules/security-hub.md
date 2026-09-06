# Security Hub (`awsSecurityHub`)

Covers AWS Security Hub standards (compliance checks), finding ingestion from other AWS products, and automation rule evaluations in a single line item. Pricing is per-account, per-Region — a multi-account / multi-Region deployment multiplies accordingly.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| All five cc fields at "10" (checks, ingestion, automation, `noOfAccounts`), us-east-2 | capture-verified | captured saveAs body — $0.10 matches exactly |
| Standards / findings / automation rate lookups | capture-verified | `pricing_client.py get-products` for the three `productFamily` values, us-east-2 |
| Per-account-per-Region tier walk (tier first, then multiply by `noOfAccounts`) | inferred | both orders coincide at the captured scale, so the capture does not discriminate |
| Multi-Region rollout (one line item per Region) | inferred | the UI exposes one Region per line item; the split is this module's guidance |
| Regions other than us-east-2 | inferred | per-region rates should be re-queried |

## Line-item header

```json
{
  "serviceCode":  "awsSecurityHub",
  "estimateFor":  "template_securityhub",
  "version":      "0.0.51",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Security Hub",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  "noOfAccounts":        {"value": "10"},   // accounts enrolled in Security Hub in this Region
  "noOfSecurityChecks":  {"value": "10"},   // security checks per account per month (standards)
  "noOfIngestion":       {"value": "10"},   // finding ingestion events per account per month (paid integrations)
  "noOfautomationrules": {"value": "10"},   // automation rules per account
  "noOfcriteria":        {"value": "10"}    // criteria evaluated per rule per month
}
```

All values are stringified integers. Security Hub bills per Region, so one line item per active Region (just like the AWS Pricing Calculator UI).

## Pricing API filters

ServiceCode is `AWSSecurityHub`. The three billable dimensions live in three productFamily values; each has its own free-tier band as the lowest priceDimension and one or more paid tiers above it.

### Standards — security checks (per account per Region)

```
--service-code AWSSecurityHub
--filter regionCode=<region>
--filter "productFamily=AWS Security Hub - Standards"
--filter standardGroup=PaidComplianceCheck
```

Three OnDemand priceDimensions in us-east-2:
- 0 – 100,000 checks/account/Region/month → $0.0010 / check
- 100,001 – 500,000 → $0.0008 / check
- 500,000+ → $0.0005 / check

(There's a separate `standardGroup=FreeComplianceCheck` SKU at $0; the calculator's user-facing field is total checks and the calculation walks the tiers.)

### Findings — paid ingestion (per account per Region)

```
--service-code AWSSecurityHub
--filter regionCode=<region>
--filter "productFamily=AWS Security Hub - Findings"
--filter findingGroup=PaidFindingsIngestion
```

Two OnDemand priceDimensions:
- 0 – 10,000 events/account/Region/month → $0 (free tier)
- 10,000+ → $0.00003 / event

Security Hub-native findings are always free; only paid integrations (`findingSource=OtherProduct`) hit this rate.

### Automation — rule evaluation events

```
--service-code AWSSecurityHub
--filter regionCode=<region>
--filter "productFamily=AWS Security Hub - Automation"
--filter automationGroup=RuleEvaluation
```

Four OnDemand priceDimensions:
- 0 – 1,000,000 evaluations/month → $0 (free tier)
- 1M – 100M → $0.0000001 / evaluation ($1e-7)
- 100M – 1B → $0.00000005 ($5e-8)
- 1B+ → $0.000000015 ($1.5e-8)

Use `get-attribute-values --service-code AWSSecurityHub --attribute productFamily` to enumerate the families; `automationGroup`, `findingGroup`, `standardGroup` enumerate the free-vs-paid SKUs.

## Multipliers / formula

The calculator treats `noOfSecurityChecks`, `noOfIngestion`, `noOfautomationrules`, and `noOfcriteria` as **per-account** quantities, then scales by `noOfAccounts`. Automation evaluations expand as `rules × criteria` per account.

```
# Per-account quantities (before scaling by noOfAccounts):
checks_per_account      = noOfSecurityChecks
ingestion_per_account   = noOfIngestion
evaluations_per_account = noOfautomationrules * noOfcriteria

# Tiers are PER ACCOUNT PER REGION, so tier-walk each account's quantity FIRST,
# then multiply by noOfAccounts (identical inputs across accounts in this cc shape).
# Walking the aggregate would misapply the volume bands; at the captured scale
# (10 accounts, quantities inside the first band) both orders coincide.
monthly_checks     = noOfAccounts * tier_walk(checks_per_account      across standards tiers)
monthly_ingestion  = noOfAccounts * tier_walk(ingestion_per_account   across findings tiers)
monthly_automation = noOfAccounts * tier_walk(evaluations_per_account across automation tiers)

serviceCost.monthly = monthly_checks + monthly_ingestion + monthly_automation
serviceCost.upfront = 0
```

`tier_walk` is the standard "walk volume across `begin_range`/`end_range` bands" routine used in `s3.md` / `ec2.md`. Round the sum to two decimals.

## configSummary template

```
Number of accounts (<N>), Number of security checks per account per month (<N>), Number of finding ingestion events per account per month (<N>), Number of automation rules per account (<N>), Number of criteria per automation rule (<N>)
```

(Match the captured phrasing; the SPA reads this for the line-item card.)

## Defaults

| Field | Default | Why |
|---|---|---|
| noOfAccounts | "1" | Single-account default; flag if user mentions Organizations |
| noOfSecurityChecks | "10000" | Order-of-magnitude for a small-to-mid account running AWS Foundational + CIS |
| noOfIngestion | "0" | Most users only have native findings (which are free); only set if user mentions paid integrations like Prisma / Wiz / Snyk |
| noOfautomationrules | "0" | Zero unless user explicitly wants automation |
| noOfcriteria | "0" | Companion to noOfautomationrules; both zero or both set |

## Verification

Reproduced the captured $0.10 monthly cost in `us-east-2` with all five fields = "10":

- checks: 10 checks/account × $0.001 (first band) = $0.01/account × 10 accounts = **$0.10**
- ingestion: 10 events/account → under the 10,000 free tier = $0.00/account × 10 = **$0.00**
- automation: 10 × 10 = 100 evaluations/account → under the 1,000,000 free tier = $0.00/account × 10 = **$0.00**

Total: **$0.10**, matches the captured `serviceCost.monthly` exactly.

Pricing API queries used: `productFamily="AWS Security Hub - Standards"` + `standardGroup=PaidComplianceCheck`, `productFamily="AWS Security Hub - Findings"` + `findingGroup=PaidFindingsIngestion`, and `productFamily="AWS Security Hub - Automation"` + `automationGroup=RuleEvaluation`, all with `regionCode=us-east-2`.

Open question: the calculator UI exposes only one Region per line item but Security Hub bills per-account-per-Region. For a multi-Region rollout, generate one `awsSecurityHub` line item per Region. The `noOfAccounts` and per-account fields should reflect that Region's footprint.

# AWS WAF (`awsWebApplicationFirewall`)

A single flat line item covering Web ACLs, the rules attached to them (direct rules, rule groups, rules inside groups, managed rule groups), and request volume. WAF is region-scoped; pricing is consistent across most commercial regions but always look it up per region.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| All six cc dimensions at 10 (Web ACLs, rules, rule groups, managed rules, requests), us-east-2 | capture-verified | captured saveAs body — $1356.00 reproduced exactly |
| Web ACL / rule / request rates | capture-verified | Price List API (`awswaf`), us-east-2, 2026-05-09 |
| Paid managed rule groups (Bot Control, Fraud Control, ATP) entity + per-request fees | inferred | not modeled by this form — capture a fresh HAR before promising numbers |
| Request tiers (WCU 2500+, body inspection over 48 KB) | inferred | not exposed by the form; the flat $0.60/M rate is assumed |
| Regions other than us-east-2 | inferred | pricing is consistent across most commercial regions but should be looked up per region |

## Line-item header

```json
{
  "serviceCode":  "awsWebApplicationFirewall",
  "estimateFor":  "awsWaf",
  "version":      "0.0.34",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS WAF",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  "numberOfWebAcls":             {"value": "10", "unit": "perMonth"},  // Web ACLs in this region
  "numberOfRulesPerWebAcl":      {"value": "10", "unit": "perMonth"},  // direct rules attached to each ACL
  "numberOfRuleGroupsPerWebAcl": {"value": "10", "unit": "perMonth"},  // customer-managed rule groups per ACL
  "numberOfRulesPerRuleGroup":   {"value": "10", "unit": "perMonth"},  // rules inside each customer rule group
  "numberOfManangedRules":       {"value": "10", "unit": "perMonth"},  // managed rule groups per ACL (typo is literal — preserve)
  "numberOfWebRequests":         {"value": "10", "unit": "perMonth"}   // millions of requests per month (see note)
}
```

Notes:

- The field `numberOfManangedRules` has a misspelling ("Mananged" with an extra `n`) in the SPA. Keep it. Renaming silently zeroes the dimension.
- `numberOfWebRequests` is in **millions of requests per month** despite the `perMonth` unit label. A captured "10" with rate $0.60/M produces $6.00, matching the observed estimate.
- All values are strings. The SPA coerces them client-side.
- All "per ACL" fields are interpreted as average-per-ACL and multiplied by the ACL count; there's no per-ACL detail.

## Pricing API filters

Service code in the Price List API is `awswaf` (lowercase).

Web ACL ($5.00 / month):

```
--service-code awswaf
--filter regionCode=<region>
--filter group=Web ACL
```

Returns two SKUs (a `WebACLV2` SKU and a legacy `WebACL` SKU) — both currently $5.00/month. Use either.

Rules ($1.00 / rule / month):

```
--service-code awswaf
--filter regionCode=<region>
--filter group=Rule
```

Two SKUs (V2 + legacy), both $1.00/month. This rate applies uniformly to direct rules, customer rule groups (each rule group counts as 1 billable rule slot), rules inside customer rule groups, AND managed rule groups (each managed group also counts as 1 billable rule slot).

Web requests (standard, $0.60 / million):

```
--service-code awswaf
--filter regionCode=<region>
--filter group=Request
```

Multiple SKUs exist, keyed by request size and WCU tier. For the calculator's default, use the `Requests Processed 48KB` SKU at $0.60 / 1M. Higher tiers (`Tier3..Tier8 WCU`, `64KB+ body inspection`) are $1.00–$2.00 / 1M but the calculator's `numberOfWebRequests` field does not expose tier selection — assume the 48KB / base rate unless you have evidence otherwise.

Managed rule group entity charges (Bot Control, Fraud Control, ATP) are *separate* from the per-rule fee and live under groups like `AMR Bot Control Entity` ($10/month per managed group enabled, per protected resource). The calculator's `numberOfManangedRules` does NOT include these — it only charges the $1/rule slot fee. If the user enables Bot Control / Fraud Control / Captcha they need a separate handling path (not yet captured here — verify before relying on this).

## Multipliers / formula

For one Web ACL the billable rule count is:

```
rules_per_acl = rulesPerWebAcl
              + ruleGroupsPerWebAcl
              + (ruleGroupsPerWebAcl * rulesPerRuleGroup)
              + manangedRules
```

Each of those is $1.00/month. Then:

```
monthly_web_acl  = numberOfWebAcls * 5.00
monthly_rules    = numberOfWebAcls * rules_per_acl * 1.00
monthly_requests = numberOfWebRequests * 0.60         # numberOfWebRequests is in millions

serviceCost.monthly = monthly_web_acl + monthly_rules + monthly_requests
serviceCost.upfront = 0                                # WAF has no commit pricing
```

### Worked example (matches captured $1356.00)

All inputs = 10:

| Dimension | Calc | $ |
|---|---|---|
| Web ACLs | 10 × $5.00 | 50.00 |
| Direct rules | 10 ACLs × 10 rules × $1.00 | 100.00 |
| Rule groups (each counts as 1 rule slot) | 10 × 10 × $1.00 | 100.00 |
| Rules inside rule groups | 10 × 10 × 10 × $1.00 | 1000.00 |
| Managed rule groups (each counts as 1 rule slot) | 10 × 10 × $1.00 | 100.00 |
| Web requests | 10M × $0.60/M | 6.00 |
| **Total** | | **$1356.00** |

This is the AWS WAF pricing model exactly: every rule reference inside a Web ACL — direct rule, rule group reference, individual rule inside that group, or managed rule group reference — counts as one billable rule at $1.00/month. The calculator surfaces the four categories separately for clarity but charges the same per-slot rate for all of them.

## configSummary template

Match the captured SPA phrasing:

```
Number of Web Access Control Lists (Web ACLs) utilized (<N> per month), Number of Rules added per Web ACL (<N> per month), Number of Rule Groups per Web ACL (<N> per month), Number of Rules inside each Rule Group (<N> per month), Number of Managed Rules per Web ACL (<N> per month), Number of requests per month (<N> million per month)
```

## Defaults to apply when the user is silent

| Field | Default | Why |
|---|---|---|
| numberOfWebAcls | 1 | One ACL is the typical entry point |
| numberOfRulesPerWebAcl | 5 | Modest custom rule set |
| numberOfRuleGroupsPerWebAcl | 0 | Most starters skip custom rule groups |
| numberOfRulesPerRuleGroup | 0 | Only relevant if rule groups > 0 |
| numberOfManangedRules | 2 | Common to attach AWSManagedRulesCommonRuleSet + KnownBadInputs |
| numberOfWebRequests | 1 | 1M requests/month — a small workload baseline |

All values stringified, `unit` always `perMonth`.

## Verification

- Captured HAR: a saveAs body in `us-east-2` with all six dimensions = 10 returned `serviceCost.monthly = $1356.00`. The formula above reproduces this exactly.
- Rates verified live via Price List API (`awswaf` service code) in `us-east-2` on 2026-05-09: Web ACL $5.00/mo, Rule $1.00/mo, base Request $0.60/M.
- Inferred but unverified: behavior when `numberOfManangedRules` is meant to represent paid AWS Marketplace managed rule groups (Bot Control, Fraud Control, ATP) — those carry separate per-month entity fees ($10+/mo) plus per-request fees the calculator's flat `numberOfWebRequests` does not model. If the user wants Bot Control / Fraud Control / Captcha pricing, capture a fresh HAR before promising numbers.
- Request tiers (WCU 2500+, body inspection > 48KB) are not exposed by this form. The flat $0.60/M rate is assumed.

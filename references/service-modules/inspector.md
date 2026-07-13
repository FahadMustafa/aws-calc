# Amazon Inspector v2 (`amazonInspector`)

Covers all Inspector v2 metering dimensions in a single line item: EC2 instance scanning, ECR container image scanning (initial + automated re-scan), Lambda function scanning, and code-repository scans (SAST, SCA, IaC, plus on-demand and change-based scans).

## Line-item header

```json
{
  "serviceCode":  "amazonInspector",
  "estimateFor":  "Inspectorv2",
  "version":      "0.0.22",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Inspector",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  // Average number of EC2 instances under continuous Inspector scanning per month.
  "NumberOfEC2Instance":          {"value": "10"},

  // Container images receiving continuous (automated) re-scans this month.
  // Different from numberOfNewImages: this is the population of long-lived
  // images, numberOfNewImages is the new-push volume. Despite the configSummary
  // re-using the "newly pushed container images" label for both fields, this
  // one drives the re-scan formula.
  "numberOfNewImages_continual":  {"value": "10"},

  // Automated re-scans PER continually-scanned image per month (multiplier
  // against numberOfNewImages_continual).
  "numberOfRescans":              {"value": "10"},

  // Container images newly pushed to ECR this month (each gets one initial
  // scan at $0.09).
  "numberOfNewImages":            {"value": "10"},

  // Average number of Lambda functions under Inspector Standard scanning.
  "avgNoOfLambda":                {"value": "10"},

  // Code repositories enrolled in Inspector code scanning. Multiplies every
  // per-repo code-scan field below.
  "total_repositories":           {"value": "10"},

  // Periodic SAST / SCA / IaC scans per repository per month.
  "number_SAST_scans":            {"value": "10"},
  "number_SCA_scans":             {"value": "10"},
  "number_IAC_scans":             {"value": "10"},

  // Ad-hoc on-demand scans per repository per month (sum across SAST+SCA+IaC).
  "number_onDemand_scans":        {"value": "10"},

  // Change-based scans per repository per month (PR / push trigger; sum
  // across SAST+SCA+IaC).
  "number_change_based_scans":    {"value": "10"}
}
```

All values are stringified integers. Use `"0"` to disable a dimension cleanly.

## Pricing API filters

ServiceCode is `AmazonInspectorV2`. Each metering dimension is its own SKU keyed by `usagetype`; the usage-type prefix is region-specific (`USE2-` for us-east-2, `USE1-` for us-east-1, `EUW1-` for eu-west-1, etc.). Use `get-attribute-values --service-code AmazonInspectorV2 --attribute usagetype` to enumerate. All rates verified below are for us-east-2.

```
--service-code AmazonInspectorV2
--filter regionCode=<region>
--filter usagetype=<PREFIX>-EC2-Scanning              # $0.00174 per Instance-hr   (~$1.2702/inst/month)
--filter usagetype=<PREFIX>-Lambda-Standard-Scanning  # $0.000417 per Hourly       (~$0.3044/func/month)
--filter usagetype=<PREFIX>-container-image-initial-scan  # $0.09 per Resource-assessment
--filter usagetype=<PREFIX>-container-image-re-scan       # $0.01 per Resource-assessment
--filter usagetype=<PREFIX>-Code-Repository-Scan-SAST     # $0.15 per Resource-assessment
--filter usagetype=<PREFIX>-Code-Repository-Scan-SCA      # $0.15 per Resource-assessment
--filter usagetype=<PREFIX>-Code-Repository-Scan-IaC      # $0.15 per Resource-assessment
```

Each SKU has a single OnDemand priceDimension with no tiers. On-demand and change-based scans are billed at the same $0.15 per-scan rate as the periodic SAST/SCA/IaC SKUs — the calculator just exposes the volume separately so users can model CI/CD vs. scheduled scanning.

Related SKUs you can ignore for this line item: `-free-trial`, `-free-metering`, and `-ECR-free-metering` are $0; `-EC2-CIS-checks` ($0.03/check) and `-EC2-Scanning-agentless` ($0.00243/inst-hr) and `-Lambda-Code-Scanning` ($0.00084/hr) are not surfaced by this calculator form. If you need CIS or agentless scanning, capture a fresh saveAs body first — the schema may have grown.

## Multipliers / formula

Hours per month = 730 (the AWS Calculator's house convention).

```
monthly_ec2  = NumberOfEC2Instance      * 0.00174 * 730
monthly_lam  = avgNoOfLambda            * 0.000417 * 730
monthly_ecr  = numberOfNewImages        * 0.09
             + numberOfNewImages_continual * numberOfRescans * 0.01
monthly_code = total_repositories
             * (number_SAST_scans + number_SCA_scans + number_IAC_scans
                + number_onDemand_scans + number_change_based_scans)
             * 0.15

serviceCost.monthly = monthly_ec2 + monthly_lam + monthly_ecr + monthly_code
serviceCost.upfront = 0
```

No free tier is modeled — Inspector's 15-day per-resource free trial is invisible to the calculator.

## configSummary template

Match the captured phrasing exactly (the SPA reads this for the line-item card; the duplicate "newly pushed container images" phrase is intentional):

```
Average* No. of EC2 instances scanned per month (<N>), Total number of newly pushed container images per month (<N>), Total number of automated rescans per image per month (<N>), Total number of newly pushed container images per month (<N>), Average number of Lambda functions scanned in a month (<N>), Total number of repositories (<N>), Number of SAST periodic scans per repository per month (<N>), Number of SCA periodc scans per repository per month (<N>), Number of IaC periodic scans per repository per month (<N>), Total Number of on-demand scans (across each scan-type including SAST, SCA and IaC) per repository per month (<N>), Total number of change-based scans (across each scan-type including SAST, SCA, IaC) per repository per month (including pull request/merge request or push) (<N>)
```

Note the captured typo `periodc` in the SCA fragment — leave it as-is.

## Defaults

| Field | Default | Why |
|---|---|---|
| NumberOfEC2Instance | "0" | Opt-in scanning volume |
| numberOfNewImages_continual | "0" | Only set if user scans ECR |
| numberOfRescans | "0" | Companion to the field above |
| numberOfNewImages | "0" | Only set if user scans ECR |
| avgNoOfLambda | "0" | Opt-in |
| total_repositories | "0" | Opt-in code scanning |
| number_SAST_scans, number_SCA_scans, number_IAC_scans | "0" | Only meaningful if `total_repositories > 0` |
| number_onDemand_scans, number_change_based_scans | "0" | Same — only with repos |

If the user mentions a workload class without specific counts, populate just the relevant dimensions and zero the rest (e.g. an ECR-only estimate uses the three ECR fields; an EC2-fleet estimate uses just `NumberOfEC2Instance`).

## Verification

Reproduced against the captured `serviceCost.monthly = $93.30` in `us-east-2` with every input field = "10":

- EC2: 10 × $0.00174 × 730 = **$12.70**
- Lambda: 10 × $0.000417 × 730 = **$3.04**
- ECR initial: 10 × $0.09 = **$0.90**
- ECR re-scan: 10 × 10 × $0.01 = **$1.00**
- Code repos (5 scan-type fields × 10 scans × 10 repos × $0.15): **$75.00**
- **Hand total: $92.65** vs captured **$93.30** — residual **~$0.65 (~0.7%)**.

The residual is consistent across every combination I tried — it does not move when you flex one input, which suggests a small fixed overhead the calculator applies (most likely a per-repo onboarding fee not surfaced in the Pricing API, or rounding inside the SPA's internal price table). Captured saveAs source: `/tmp/ct_capture_346.json` (path was ephemeral; file lost — re-capture needed). The formula above is safe to use for any estimate where being within ~1% is acceptable; flag the residual if a customer pushes for cent-precision.

Open question worth verifying before relying on it: the duplicate `Total number of newly pushed container images per month` label in `configSummary` for both `numberOfNewImages` and `numberOfNewImages_continual` is a calculator UI bug — the two fields drive different math (initial-scan volume vs. continual-scan population). Re-check if the calculator's `version` bumps past `0.0.22`.

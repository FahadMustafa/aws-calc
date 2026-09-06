# AWS CodeDeploy (`awsCodeDeploy`)

Single line item for CodeDeploy. CodeDeploy is free for deployments to EC2, Lambda, and ECS — the only chargeable path is deployments to **on-premises** instances, billed at $0.02 per on-prem instance update. The calculator form only models the on-prem path; if a workload uses only EC2/Lambda/ECS deployments, do not add this line item (cost would be $0).

## Line-item header

```json
{
  "serviceCode":  "awsCodeDeploy",
  "estimateFor":  "CodeDeployTemplate",
  "version":      "0.0.37",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS CodeDeploy",
  "description":  null
}
```

`estimateFor` is the literal string `"CodeDeployTemplate"` (CamelCase with `Template` suffix) — pulled from a captured saveAs body. Do not normalize the casing.

## calculationComponents (verified shape)

```jsonc
{
  "numberOfDeployments":     {"value": "4",  "unit": "perMonth"}, // deployments per month, as string
  "numberOfOnPremInstances": {"value": "10"}                       // count of on-prem instances per deployment; no unit field
}
```

Two fields, both required. `numberOfDeployments.unit` is the literal string `"perMonth"`. `numberOfOnPremInstances` has **no** `unit` key (just `value`) — match the captured shape exactly; adding a unit may cause the SPA to misparse.

## Pricing API filters

The Pricing API ServiceCode is `AWSCodeDeploy` (capitalized — does not match the calculator's `awsCodeDeploy`).

### Per-on-prem-instance-update rate

```
--service-code AWSCodeDeploy
--filter regionCode=<region>
--filter productFamily=CodeDeploy
--filter "deploymentLocation=On Premises"
```

Returns one SKU with a single OnDemand priceDimension. `price_per_unit` is the dollar rate per on-prem instance update (e.g. `0.02` in us-east-2). Description: `"$0.02 per on-premises instance update"`. Unit: `OnPremUpdates`.

There is no Reserved/SavingsPlan/upfront pricing for CodeDeploy — OnDemand is the only term. EC2, Lambda, and ECS deployments do not appear in the Pricing API at all because they are free.

## Multipliers / formula

```
on_prem_updates_per_month = numberOfOnPremInstances * numberOfDeployments
serviceCost.monthly        = on_prem_updates_per_month * on_prem_update_rate
serviceCost.upfront        = 0
```

Each deployment counts one "update" per on-prem instance targeted, so a single deployment to 10 instances costs `10 × $0.02 = $0.20`, and 4 deployments to those same 10 instances costs `$0.80/month`.

No free tier, no tiering, no commitment options. Failed deployments still incur the per-update charge in production accounts — the calculator does not distinguish.

## configSummary template

Match the captured phrasing so the line-item card renders cleanly:

```
Number of on-premise instances (<N>), Number of deployments (<D> per month)
```

Note: the captured copy uses "on-premise" (no trailing 's') and the unit suffix on deployments is the literal phrase "per month" (with space), distinct from the `numberOfDeployments.unit` value of `"perMonth"` (no space). Reproduce both forms verbatim.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfDeployments | "4" perMonth | One deployment per week is a reasonable steady-state cadence for a typical app |
| numberOfOnPremInstances | "1" | Minimal fleet; bump per the user's described environment |

If the user mentions CI/CD targeting only EC2, Lambda, or ECS, **do not add a CodeDeploy line item** — the cost is $0 and the line would mislead. Mention briefly in the response narrative that CodeDeploy is free for those targets. Add the line item only when the user explicitly mentions on-premises servers, hybrid deployments, or VMware/bare-metal fleets being orchestrated by CodeDeploy.

## Verification

- Shape captured from a working saveAs body the calculator round-tripped on 2026-05-11 in `us-east-2` — captured HAR: `calculator.aws_new_2.har`, per-service slice: `captures/saveAs/per-service/awsCodeDeploy.json`.
- Pricing API filters above verified via `pricing_client.py get-products` against the live API: returns SKU `AUS7RDUXSK33Y676` with rate `$0.02` per on-prem instance update (unit `OnPremUpdates`) for `regionCode=us-east-2`.
- Formula verified: `10 on-prem instances × 4 deployments/month × $0.02 = $0.80`, which matches the captured `serviceCost.monthly` of `$0.80` exactly.
- EC2 / Lambda / ECS deployment paths are not modeled here — they are free per AWS pricing and the calculator form has no inputs for them. If a future capture surfaces additional `calculationComponents` keys for non-on-prem deployments, re-verify before relying on this module for those workloads.

- **Form 0.0.32 → 0.0.37 (2026-09-06).** Diffed against the live form definition (`data/awsCodeDeploy/en_US.json`, version `0.0.37`). Template `CodeDeployTemplate` defines `numberOfOnPremInstances` (numericInput, form default `10`), `numberOfDeployments` (frequency, form default `4`, output frequency `perMonth`), plus a display-only `codeDeploy_bodyText` block that is not a cc key. That matches the documented two-field shape. **No cc-relevant change**: fields added: none, renamed: none, removed: none. Version pin bumped only.

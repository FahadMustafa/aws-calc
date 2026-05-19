# AWS Systems Manager (`awsSystemsManager` group)

Systems Manager is a **group** service with sub-services for each priced SSM capability. The captured form covers three: Parameter Store, Automation, and Just-in-Time Node Access. Other SSM capabilities (Patch Manager, Inventory, Distributor, Run Command, OpsCenter, App Manager, Change Manager, Incident Manager) are not in this capture — add them only after capturing a HAR that includes them.

## Group-level header

```json
{
  "serviceCode":  "awsSystemsManager",
  "estimateFor":  "awsSystemsManager",
  "version":      "0.0.35",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Systems Manager",
  "description":  null,
  "subServices":  [ ... ],
  "serviceCost":  { "monthly": <sum> }
}
```

## subServices

### Parameter Store (`awsSystemsManagerParameterStore`)

```jsonc
{
  "serviceCode":  "awsSystemsManagerParameterStore",
  "estimateFor":  "paramStoreThrouhputStandard",   // sic — "Throuhput", not "Throughput"
  "version":      "0.0.25",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "sysManagerParamStore_numberOfStandardParameters": {"value": "1000"},
    "sysManagerParamStore_numberOfAdvParameters":      {"value": "100"},
    "sysManagerParamStore_numberOfAPIInteractions":    {"value": "100", "unit": "perMinute"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

The `estimateFor` value `paramStoreThrouhputStandard` is the SPA's literal string — note the missing `g` ("Throuhput"). Don't fix it; the SPA matches the typo. `sysManagerParamStore_numberOfAPIInteractions` is interactions per minute **per parameter** (not aggregate), so total monthly ops = `(standard + advanced) * interactionsPerMinute * 60 * 24 * 30`.

### Automation (`awsSystemsManagerAutomation`)

```jsonc
{
  "serviceCode":  "awsSystemsManagerAutomation",
  "estimateFor":  "smAutomation",
  "version":      "0.0.31",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "sysManagerAutomation_numberOfSteps":              {"value": "100", "unit": "perDay"},
    "sysManagerAutomation_numberOfAWSExecuteSteps":    {"value": "100"},          // count of aws:executeScript steps per day
    "sysManagerAutomation_stepDuration":               {"value": "100", "unit": "sec"},
    "sysManagerAutomation_playbookSize":               {"value": "100", "unit": "mb|NA"},
    "sysManagerAutomation_numberOfPlaybookAttachments":{"value": "100"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

General Automation steps are free in the AWS price list; the per-step cost shows up only for `aws:executeScript` (Lambda-backed) steps. Playbook attachment storage is billed per MB-month — at the captured 100 MB × 100 attachments scale, total cost was $0.60/mo, so storage dominates only at unusual scale.

### Just-in-Time Node Access (`justInTimeNodeAccess`)

```jsonc
{
  "serviceCode":  "justInTimeNodeAccess",
  "estimateFor":  "smJustInTimeNodeAccess",
  "version":      "0.0.8",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "justInTime_numberOfhours": {"value": "100"}    // note the lowercase 'h' in 'numberOfhours'
  },
  "serviceCost": { "monthly": <computed> }
}
```

Single dimension: managed-node-hours under JIT access control. Field name uses lowercase `h` in `numberOfhours` — copy verbatim.

## Pricing API filters

Service code is `AWSSystemsManager` for Parameter Store, Automation, and JIT Node Access; the Pricing API splits SKUs by `usagetype` (the bucket dictates which sub-service it belongs to).

### Parameter Store

```
--service-code AWSSystemsManager
--filter productFamily="AWS Systems Manager"
--filter regionCode=<region>
```

Look for SKUs with `usagetype` containing `AdvancedParam-Storage` (per-advanced-parameter-month), `ParameterStore-Op-Std` and `ParameterStore-Op-Adv` (per-10,000-API-interactions), and the higher-throughput-tier SKU. Standard parameters and the first tier of standard ops are free — no SKU returned.

### Automation

```
--service-code AWSSystemsManager
--filter productFamily="AWS Systems Manager"
--filter regionCode=<region>
```

Look for `Automation-Steps` (per step, with a free tier) and `Automation-Att-Storage` (per MB-month for stored playbook attachments). `aws:executeScript` step cost is billed separately as standard Lambda — the SPA folds that into the Automation total, so include Lambda compute math here.

### Just-in-Time Node Access

```
--service-code AWSSystemsManager
--filter productFamily="AWS Systems Manager"
--filter regionCode=<region>
```

Look for `JustInTimeNode-Hours` (or similar) — per-managed-node-hour under JIT. eu-west-1 rate from capture is ~$0.0137/hour (`$1.37 / 100 hours`).

## Multipliers / formula

```
# Parameter Store
ps_advanced_storage  = numberOfAdvParameters * advanced_param_per_month_rate     # eu-west-1: ~$0.05/param/month
ps_advanced_ops      = numberOfAdvParameters * apiInteractionsPerMinute
                       * 60 * 24 * 30 / 10000 * advanced_op_per_10k_rate          # eu-west-1: ~$0.05/10k
ps_standard_ops      = (numberOfStandardParameters * apiInteractionsPerMinute > 40 TPS shared)
                       ? higher-throughput-tier ops + flat hourly fee
                       : 0
paramStore.monthly   = ps_advanced_storage + ps_advanced_ops + ps_standard_ops

# Automation
automation.monthly   = numberOfAWSExecuteSteps * 30 * lambda_compute_per_step(stepDuration)
                     + numberOfPlaybookAttachments * playbookSize * attachment_storage_per_mb_month

# JIT Node Access
jit.monthly          = numberOfhours * jit_per_hour_rate
```

Verification status:
- **JIT** matches capture exactly: `100 * $0.0137 = $1.37`. ✓
- **Automation** captured at `$0.60`. With 100 steps/day × 30 days = 3000 `aws:executeScript` steps × 100s each = 300,000 step-seconds. Default 512 MB Lambda equivalent: 300,000 × 0.5 GB × $0.0000166667 = $2.50, plus 3000 invocations × $0.20/M = $0.0006 → ~$2.50 plus storage 100 × 100 MB × small rate. Captured $0.60 is lower than that — the SPA may treat the captured "steps per day" as fixed-30-day-month and use a different per-step rate, or attribute most cost to playbook storage at a tiny per-MB-month rate. **Formula needs a second capture (vary `numberOfAWSExecuteSteps` and `stepDuration` independently) before relying on it for non-trivial estimates.**
- **Parameter Store** captured at `$2,195.11`. Best reconstruction:
  - Advanced ops: `100 advanced * 100/min * 60 * 24 * 30 / 10000 * $0.05 = $2,160.00`
  - Advanced storage: `100 * $0.05 = $5.00`
  - Subtotal: `$2,165.00` — captured is $30.11 higher, likely standard-tier higher-throughput hourly fee (`$0.01/h * 730 = $7.30` is too low; perhaps tiered ops at higher throughput at $30/mo). **Re-derive after a capture that zeroes API interactions, to isolate the storage component from the ops component.**

## configSummary template

Match the captured phrasing per sub-service, space-joined:

```
Standard parameters (<N>), Advanced parameters (<N>), Frequency of API interactions per parameter (<N> per minute) Average size of playbook attachments (<N> MB), Frequency of steps (<N> per day), aws:executeScript steps (<N>), Playbook attachments stored (<N>) Number of System Manager managed node hours (<N>)
```

Note "System Manager" (no `s`) in the JIT segment — the SPA uses this exact spelling. Omit a sub-service's segment if its sub-service isn't included.

## Defaults

| Field | Default | Why |
|---|---|---|
| sysManagerParamStore_numberOfStandardParameters | "0" (omit Parameter Store entirely if not mentioned) | Standard params are free; only include if user mentions Parameter Store usage |
| sysManagerParamStore_numberOfAdvParameters | "0" | Advanced params cost $0.05/param-month — only include when user mentions advanced params or rotation/notification |
| sysManagerParamStore_numberOfAPIInteractions | "10" (per minute) | Low default; flag in breakdown |
| sysManagerAutomation_numberOfSteps | "10" (per day) | Low typical |
| sysManagerAutomation_numberOfAWSExecuteSteps | "0" | Only set if the user mentions Python/PowerShell automation steps |
| sysManagerAutomation_stepDuration | "30" (sec) | Typical short script |
| sysManagerAutomation_playbookSize | "1" MB | Small default |
| sysManagerAutomation_numberOfPlaybookAttachments | "0" | Omit if user did not mention attachment storage |
| justInTime_numberOfhours | "0" (omit `justInTimeNodeAccess` if not mentioned) | Charge only applies when JIT access is enabled |

If the user says "Systems Manager" without specifics, ask which capability (Parameter Store / Automation / JIT / Patch Manager / etc.) — costs vary by 4+ orders of magnitude across SSM features. Don't pick a default capability.

## Verification

- Captured HAR: `captures/calculator.aws_new_3.har` → `captures/saveAs/per-service/awsSystemsManager.json` (eu-west-1, single line item, 3 sub-services).
- JIT formula matches capture exactly ($1.37).
- Parameter Store formula reconstructs $2,165 of the captured $2,195.11 — $30 gap likely from higher-throughput-tier standard ops; **need a second capture** with API interactions = 0 to isolate the storage SKU.
- Automation formula does NOT cleanly reconstruct the captured $0.60 — the lambda-compute-per-step cost dominates in any reasonable construction but lands above $0.60; **need a second capture** with `numberOfAWSExecuteSteps=0` to isolate playbook storage from script execution.
- Patch Manager, Run Command, OpsCenter, Change Manager, Incident Manager — **NOT covered**. Capture HAR before quoting these.

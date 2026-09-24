# AWS Fargate (`awsFargate`)

Serverless container compute for ECS tasks (and EKS pods). One line item per task profile (vCPU/memory/storage combo + run rate). Linux x86 and **Linux ARM** On-Demand are verified; Windows, Spot and EKS pods are inferred. The form itself says Fargate Spot and Compute Savings Plans are not supported in the calculator.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| Linux x86 ECS task On-Demand (vCPU + memory + ephemeral storage, us-east-2) | capture-verified | `captures/saveAs/per-service/awsFargate.json` (local capture, 2026-05-11) — $0.04 matches exactly |
| Linux x86 vCPU / memory rates | capture-verified | `pricing_client.py get-products` against `AmazonECS`, us-east-2 |
| `numberOfTasks.unit: "perDay"` + `taskDuration` conversion | capture-verified | same capture |
| Linux ARM (`selectArchitecture: "arm"`), 24x7 tasks as `numberOfTasks` `perMonth` + `taskDuration` `hr` (eu-central-1) | recompute-verified | live SPA 2026-09-24, 33-line reference estimate (customer engagement, ID withheld; shapes in `references/fixtures/`) — 8 ARM lines reproduced to the cent on "Update estimate" |
| Linux ARM cc shape | capture-verified | `references/fixtures/awsFargate-arm.json` (SPA saveAs, 4 tasks x 730 h x 2 vCPU / 4 GB, $265.31) |
| Windows (`operatingSystem: "windows"`) | inferred | adds an OS-license per-vCPU charge; form shape not captured |
| Fargate Spot | inferred | Pricing API exposes no Spot rates; the cc field is assumed — capture before quoting |
| Ephemeral storage above the 20 GB/task free allowance | inferred | overage rate confirmed, free-tier subtraction logic not round-tripped |
| `numberOfTasks.unit: "perMonth"` + `taskDuration.unit: "hr"` | recompute-verified | same estimate. Other task units offered by the UI: per second / minute / hour / day; duration: seconds / minutes / hours / days |

## Line-item header

```json
{
  "serviceCode":  "awsFargate",
  "estimateFor":  "template",
  "version":      "0.0.66",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Fargate",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  "operatingSystem":                {"value": "linux"},               // linux | windows  (only "linux" round-tripped)
  "selectArchitecture":             {"value": "x86"},                 // x86 | arm  (both round-tripped)
  "numberOfTasks":                  {"value": "1", "unit": "perDay"}, // unit: perDay | perMonth | perHour (others inferred from SPA conventions)
  "taskDuration":                   {"value": "1", "unit": "min"},    // min | hour | sec  (only "min" round-tripped)
  "vcpuPerTask":                    {"value": "1"},                   // Fargate-supported vCPU sizes: 0.25, 0.5, 1, 2, 4, 8, 16
  "memoryStandardFargateOnDemand":  {"value": "8",  "unit": "gb|NA"}, // GB (8 in the capture); MUST be a valid combo for vcpuPerTask — see Defaults
  "storageAmountECS":               {"value": "20", "unit": "gb|NA"}  // ephemeral GB allocated per task; first 20 GB free
}
```

Field name notes:
- `memoryStandardFargateOnDemand` is the on-demand Linux-mode memory field. For Fargate Spot the field name is expected to differ (e.g. `memoryStandardFargateSpot`) — not yet captured.
- `storageAmountECS` is per-task ephemeral storage. The captured value (20 GB) is exactly the free-tier ceiling, so the line item costs nothing for storage. Setting it >20 GB triggers overage billing (rate below) — not yet round-tripped.
- `numberOfTasks.unit` is the multiplier basis. Captured value is `perDay`; the SPA converts internally to monthly task-hours. `perMonth` and `perHour` are documented as valid in the SPA UI but only `perDay` has been verified end-to-end.

### Linux ARM, always-on services (recompute-verified 2026-09-24)

```jsonc
{
  "operatingSystem":               {"value": "linux"},
  "selectArchitecture":            {"value": "arm"},
  "numberOfTasks":                 {"value": "4",   "unit": "perMonth"},   // N concurrent tasks
  "taskDuration":                  {"value": "730", "unit": "hr"},         // hours each runs per month ("hr", not "hour")
  "vcpuPerTask":                   {"value": "2"},
  "memoryStandardFargateOnDemand": {"value": "4",   "unit": "gb|NA"},
  "storageAmountECS":              {"value": "20",  "unit": "gb|NA"}
}
```

A burst allowance works the same way: 8 tasks `perMonth` x `146` `hr`. The SPA rounds the vCPU and memory parts to 2dp **separately** before adding them, so mirror that to store the exact cent: `round(task_h * vcpu * v_rate, 2) + round(task_h * mem * m_rate, 2)`. eu-central-1 ARM: $0.03725 per vCPU-hour, $0.00409 per GB-hour. The `serviceCost` the SPA writes carries `monthly` only (no `upfront`).

## Pricing API filters

ServiceCode is **`AmazonECS`** (Fargate billing rolls up under ECS in the Price List API). Filter by `usagetype` — `regionCode` alone returns the ECS-EC2 / ECS-Anywhere SKUs mixed in. us-east-2 uses prefix `USE2-`; substitute the standard region prefix (e.g. `USE1-`, `EUW1-`, `APS1-`) for other regions.

### Linux x86 vCPU (captured)

```
--service-code AmazonECS
--filter regionCode=<region>
--filter usagetype=<PREFIX>-Fargate-vCPU-Hours:perCPU
```

us-east-2: `$0.04048` / vCPU-hour.

### Linux x86 memory (captured)

```
--filter usagetype=<PREFIX>-Fargate-GB-Hours
```

us-east-2: `$0.004445` / GB-hour.

### Ephemeral storage overage (inferred; first 20 GB/task free)

```
--filter usagetype=<PREFIX>-Fargate-EphemeralStorage-GB-Hours
```

us-east-2: `$0.000111` / GB-hour. Only bills on the GB allocated **above** 20 per task. Free-tier handling not yet verified end-to-end — the captured case is exactly at the free-tier ceiling.

### Linux ARM

```
--filter usagetype=<PREFIX>-Fargate-ARM-vCPU-Hours:perCPU   # us-east-2: $0.03238
--filter usagetype=<PREFIX>-Fargate-ARM-GB-Hours            # us-east-2: $0.00356
```

ARM is ~20% cheaper than x86 on both axes. `selectArchitecture: "arm"` is capture- and recompute-verified (see the ARM section above).

### Windows (inferred)

```
--filter usagetype=<PREFIX>-Fargate-Windows-vCPU-Hours:perCPU   # us-east-2: $0.046552
--filter usagetype=<PREFIX>-Fargate-Windows-GB-Hours            # us-east-2: $0.00511175
--filter usagetype=<PREFIX>-Fargate-Windows-OS-Hours:perCPU     # us-east-2: $0.046  (OS license, added per vCPU-hour)
```

Windows-on-Fargate adds a third per-vCPU-hour line for the OS license that nearly doubles the effective vCPU rate. Field shape for `operatingSystem: "windows"` on this form is inferred — not captured.

### Fargate Spot

The Price List API does **not** expose Fargate Spot rates (Spot is dynamic). The calculator surfaces Spot via a separate input mode (likely `memoryStandardFargateSpot` or a `pricingStrategy`-style field). Capture a HAR before quoting Spot. Public list discount is typically ~70% off On-Demand vCPU+memory, but it varies.

## Multipliers / formula

Monthly conversion factor used by the SPA: **730 hours / month**, i.e. `30.4167 days/month`. This matches every other calculator module verified so far.

```
# Convert numberOfTasks.unit + taskDuration.unit to monthly task-hours
tasks_per_month = {
    "perHour":  numberOfTasks * 730,
    "perDay":   numberOfTasks * 30.4167,
    "perMonth": numberOfTasks,
}[numberOfTasks.unit]

duration_hours = {
    "sec":  taskDuration / 3600,
    "min":  taskDuration / 60,
    "hour": taskDuration,
}[taskDuration.unit]

task_hours_per_month = tasks_per_month * duration_hours

# Linux x86 (captured form)
monthly_vcpu     = task_hours_per_month * vcpuPerTask * vcpu_rate
monthly_memory   = task_hours_per_month * memoryStandardFargateOnDemand * mem_rate
billable_storage = max(storageAmountECS - 20, 0)   # first 20 GB per task is free
monthly_storage  = task_hours_per_month * billable_storage * ephemeral_rate

serviceCost.monthly = monthly_vcpu + monthly_memory + monthly_storage
serviceCost.upfront = 0
```

For Linux ARM, swap `vcpu_rate`/`mem_rate` for ARM rates. For Windows, swap to Windows rates **and** add the OS-license line: `monthly_winlic = task_hours_per_month * vcpuPerTask * win_os_rate`.

## configSummary template

Match the captured phrasing — the SPA reads this for the line-item card title:

```
Operating system (<Linux|Windows>), CPU Architecture (<x86|ARM>), Average duration (<D> <minutes|hours|seconds>), Number of tasks or pods (<N> per <day|month|hour>), Amount of ephemeral storage allocated for Amazon ECS (<S> GB), Amount of memory allocated (<M> GB)
```

Use the lowercase `linux`/`x86` values from `calculationComponents` capitalized for the human-readable summary (display layer only).

## Defaults

| Field | Default | Why |
|---|---|---|
| operatingSystem | "linux" | Cheapest baseline; capture-verified |
| selectArchitecture | "x86" | Capture-verified; default in calculator UI |
| numberOfTasks | "1" perDay | Most common quick-quote shape |
| taskDuration | "1" min | Minimal job; flag for batch/long-running workloads |
| vcpuPerTask | "1" | Smallest "standard" Fargate config — 0.25/0.5 are valid for small tasks |
| memoryStandardFargateOnDemand | smallest valid memory for the chosen vCPU (2 GB for vCPU=1) | Must be a valid Fargate vCPU/memory combo or ECS rejects the task. The captured example uses 8 GB at vCPU=1; pick the minimum valid value when the user is silent and **flag it** (memory is a real cost axis — under-defaulting under-quotes, over-defaulting over-quotes). Do not leave this contradicting the shape example. |
| storageAmountECS | "20" gb | Free tier; bump only if the user mentions large temp/working files |

Fargate-supported vCPU/memory combinations are constrained (e.g. 0.25 vCPU → 0.5/1/2 GB memory only; 1 vCPU → 2–8 GB; 4 vCPU → 8–30 GB). The SPA may accept invalid combos and still render a cost — but the real ECS API will reject the task definition. If the user describes a memory-heavy small-vCPU profile, nudge them toward a valid combo.

## Verification

- Shape captured from a working saveAs body the calculator round-tripped on 2026-05-11 in `us-east-2`: see `captures/saveAs/per-service/awsFargate.json` (local capture, not in repo).
- Pricing API rates verified via `pricing_client.py get-products --service-code AmazonECS --filter regionCode=us-east-2 --filter usagetype=...` against the live API.
- Captured math reproduction (Linux x86, us-east-2, 1 task/day × 1 min × 1 vCPU × 8 GB × 20 GB storage):
  - task_hours_per_month = 1 × 30.4167 × (1/60) = 0.50694 hr
  - vCPU: 0.50694 × 1 × $0.04048 = **$0.02052**
  - Memory: 0.50694 × 8 × $0.004445 = **$0.01803**
  - Ephemeral: max(20-20, 0) = 0 GB billable → **$0.00**
  - **Total: $0.03855 → SPA rounds to $0.04**, matches captured `serviceCost.monthly` exactly.
- Not yet verified end-to-end (capture before relying on these):
  - Windows (`operatingSystem: "windows"`) — adds OS-license per-vCPU charge; form-field shape may use a different memory field name.
  - Fargate Spot — Pricing API does not expose Spot rates; calculator's Spot mode uses a different calculationComponents field (assumed `memoryStandardFargateSpot` or `pricingStrategy`). Capture before quoting.
  - Ephemeral storage > 20 GB per task — overage rate confirmed but free-tier subtraction logic in the SPA is inferred, not round-tripped.
  - `numberOfTasks.unit` values other than `perDay` / `perMonth` (per second / minute / hour).
- **Linux ARM captured and recompute-verified 2026-09-24** (eu-central-1): see the ARM section above and `fixtures/awsFargate-arm.json`. Form version still 0.0.66.

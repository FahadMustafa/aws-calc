# AWS CodeBuild (`awsCodeBuild`)

Single line item covering one or more **build-compute variants** on a single CodeBuild fleet type. The form lets the user pick a fleet `computeType` (on-demand EC2, on-demand Lambda, reserved capacity, etc.) and then add one or more `(Compute Type, Operating System)` rows inside `columnFormIPM` — each row is a separate compute-type/OS pairing. The captured slice models the **On-Demand EC2 fleet**; other fleets (Lambda, Reserved, Sandbox, Docker) have not yet been captured and are flagged below.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| `general1.large` Linux, On-Demand EC2 (eu-central-1) | recompute-verified | `references/fixtures/awsCodeBuild-general1-large.json` (SPA saveAs, 10 builds x 40 min = $8.00) + live SPA 2026-09-24, 42-line multi-account reference estimate (customer engagement, ID withheld) |
| On-Demand EC2 fleet (`computeType: "ondemandec2"`), single `columnFormIPM` row, us-east-2 | capture-verified | `captures/saveAs/per-service/awsCodeBuild.json` (local capture) — $0.90 matches exactly |
| Per-build-minute rate lookup (`computeFamily=OnDemand-EC2`) | capture-verified | `pricing_client.py get-products` (SKU UB8Y5XEZW2M4GZ8Y, $0.09/min) |
| Lambda fleet (`ondemandlambda`) | inferred | form value and per-second vs per-minute conversion unconfirmed |
| Windows fleet (`operatingSystem: "Windows"`) | inferred | rates exist; the form value spelling is unverified |
| Reserved capacity fleet (`reserved`) | inferred | different billing model; the current cc shape almost certainly does not match |
| GPU (`gpu1.*`) and macOS fleets | inferred | dropdown value conventions extrapolated from the lowercase-no-separator pattern |
| Multi-row `columnFormIPM` | inferred | array structure verified but the split semantics of builds/time across rows is unconfirmed — emit single-row only |

## Line-item header

```json
{
  "serviceCode":  "awsCodeBuild",
  "estimateFor":  "template_0",
  "version":      "0.0.44",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS CodeBuild",
  "description":  null
}
```

`estimateFor` is the literal string `"template_0"` (snake-case with numeric suffix) — pulled from a captured saveAs body. Do not normalize the casing or strip the `_0` suffix.

## calculationComponents (verified shape)

```jsonc
{
  "computeType":     {"value": "ondemandec2"},                     // fleet mode; lowercased no-separator string
  "buildsinaMonth":  {"value": "1"},                                // builds per month, as string; no unit field
  "AvgBuildTime":    {"value": "10", "unit": "min"},                // avg build duration; unit is literal "min"
  "columnFormIPM": {                                                // ARRAY of compute-type rows
    "value": [
      {
        "Compute Type":     {"value": "arm1.2xlarge"},              // see "Compute types" below
        "Operating System": {"value": "Linux"}                      // "Linux" | "Windows" | "macOS" | "Any"
      }
      // … add more rows for additional compute-type / OS variants
    ]
  }
}
```

Four fields, all required. Notable shape rules:

- `computeType` is the **fleet mode** (NOT a specific instance class). Captured value is `"ondemandec2"` — lowercase, no separators, no version suffix. Other modes the SPA accepts (inferred from the Pricing API `computeFamily` values, not yet captured): `"ondemandlambda"`, `"ondemandocker"` (likely; OnDemand-Docker fleet), `"reserved"`, `"sandbox"`. **Verify before emitting any non-EC2 mode** — capture a fresh HAR first.
- `buildsinaMonth` is keyed with the literal lowercase run-together name `buildsinaMonth` (one word). Match the casing verbatim.
- `AvgBuildTime` is keyed CamelCase with a capital `A` and `T`. Unit is the literal string `"min"`.
- `columnFormIPM.value` is an **array** — each entry is one column row with two sub-objects keyed by the display labels `"Compute Type"` and `"Operating System"` (with the space). The SPA renders one cost line per row and sums them. For a single-variant estimate, the array has one entry (matching the capture).
- The captured shape has **one** row, but the array structure exists so users can mix compute types in one line item (e.g. some builds on `arm1.medium`, some on `general1.large`). The exact semantic of how `buildsinaMonth` × `AvgBuildTime` divides across multiple rows is **not yet captured** — for now, emit a single-row array and add a separate line item per compute-type variant if the user describes a mixed fleet.

## Pricing API filters

The Pricing API ServiceCode is `CodeBuild` (no `AWS` prefix — unlike CodeDeploy/CodePipeline which use `AWSCodeDeploy`/`AWSCodePipeline`).

### On-Demand EC2 fleet rate (per build-minute)

```
--service-code CodeBuild
--filter regionCode=<region>
--filter productFamily=Compute
--filter computeFamily=OnDemand-EC2
--filter computeType=<compute-type>          # e.g. arm1.2xlarge, general1.medium
--filter operatingSystem=<os>                # Linux | Windows | macOS | Any
```

Returns one SKU. `price_per_unit` is the dollar rate per build-minute. Unit: `minutes`. Example (us-east-2, `arm1.2xlarge`, Linux): SKU `UB8Y5XEZW2M4GZ8Y`, rate `$0.09 / build-minute`, description `"AWS CodeBuild - Build minutes on arm1.2xlarge in US East (Ohio)"`.

### Other fleets (not yet round-tripped)

| Fleet | `computeFamily` filter | Notes |
|---|---|---|
| On-Demand EC2 | `OnDemand-EC2` | Verified above; the only fleet exercised by the captured slice |
| On-Demand Lambda | `OnDemand-Lambda` | `computeType` values are `lambda.x86-64.<N>GB` / `lambda.arm.<N>GB` (1, 2, 4, 8, 10 GB). Billed per build-second in the public pricing, but the calculator's input unit is still `min` — verify the conversion before emitting |
| On-Demand Docker | `OnDemand-Docker` | `computeType` values overlap EC2 names but rates differ |
| Reserved | `Reserved-EC2`, `Reserved-EC2-Attributes`, `Reserved-EC2-Custom` | Capacity-based billing (per fleet-hour, not per build-minute); the calculator likely exposes different `calculationComponents` keys (fleet size, hours/month) — current module shape will not work, capture before quoting |
| Sandbox | `Sandbox` | CodeBuild Sandbox feature; not in the captured slice |

There is no SavingsPlan term for CodeBuild — `OnDemand` is the only term kind on the on-demand fleets, and reserved-capacity fleets use their own `Reserved` term.

### Compute types (On-Demand EC2 fleet)

From `get-attribute-values --attribute computeType` (truncated to EC2-fleet entries):

| Family | Sizes |
|---|---|
| `general1.*` (x86-64 Linux/Windows) | `small`, `medium`, `large`, `xlarge`, `2xlarge` |
| `arm1.*` (Arm64 Linux) | `small`, `medium`, `large`, `xlarge`, `2xlarge` |
| `gpu1.*` (Linux + GPU) | `small`, `large` |

OS attribute valid values: `Linux`, `Windows`, `macOS`, `Any`. Windows is only available on `general1.*` sizes; `arm1.*` and `gpu1.*` are Linux-only. macOS uses its own size taxonomy not yet enumerated here — verify via `get-attribute-values` before emitting.

## Multipliers / formula

```
total_build_minutes  = buildsinaMonth * AvgBuildTime           # for the single captured row
monthly_per_row      = total_build_minutes * per_min_rate      # per columnFormIPM entry
serviceCost.monthly  = sum(monthly_per_row for each columnFormIPM entry)
serviceCost.upfront  = 0
```

For the captured single-row case: `1 build × 10 min × $0.09/min = $0.90`, matches `serviceCost.monthly = 0.90` exactly.

No free tier on the EC2 fleet. (AWS does publish a free-tier of 100 build-minutes/month on `general1.small` Linux for new accounts, but the calculator does not model it — bill from minute one.) No tiered pricing — flat per-build-minute rate regardless of monthly volume.

**Multi-row semantics caveat**: if `columnFormIPM` contains more than one entry, the formula above assumes each row gets its own `(buildsinaMonth × AvgBuildTime)` allocation. Whether the SPA instead splits the single `buildsinaMonth/AvgBuildTime` pair across rows (e.g. averages them) is not captured — emit single-row line items only until a multi-row HAR is captured.

## configSummary template

Match the captured phrasing so the line-item card renders cleanly:

```
AWS CodeBuild Compute Type (<Mode Display>), Number of builds in a month (<B>), Search Instance Type (<compute-type>), Operating system (<OS>)
```

Where `<Mode Display>` maps from the `computeType` value:

| `computeType` value | configSummary display |
|---|---|
| `ondemandec2` | `On-Demand EC2` |
| `ondemandlambda` | `On-Demand Lambda` (inferred) |
| `reserved` | `Reserved Capacity` (inferred) |

The label "Search Instance Type" is literal — the calculator's form widget is a searchable dropdown, and the summary text reflects the widget name rather than the more natural "Compute type". Reproduce verbatim. For a multi-row `columnFormIPM`, only the first row's compute-type and OS appear in the captured `configSummary`; behavior for multi-row summaries is not captured.

## Defaults

| Field | Default | Why |
|---|---|---|
| computeType | `"ondemandec2"` | Only fleet mode verified end-to-end; matches the most common CodeBuild usage |
| buildsinaMonth | `"0"` | Force the user to specify — CodeBuild cost is almost entirely driven by build volume × duration, and a non-zero default would silently inflate quotes |
| AvgBuildTime | `"0"` min | Same reasoning — force the user to specify per-build duration |
| columnFormIPM[0]."Compute Type" | `"general1.small"` | The free-tier-eligible default in the AWS console; safest "cheap default" if the user gives no compute hint |
| columnFormIPM[0]."Operating System" | `"Linux"` | Most common, lowest rate; Windows multiplies the per-minute rate substantially |

If the user mentions ARM, Graviton, or Arm64 builds, switch to the `arm1.*` family (cheaper per minute than `general1.*` x86 at the same size, Linux-only). If the user mentions GPU-accelerated builds, ML model training in CI, or CUDA, switch to `gpu1.*` (Linux only). If the user mentions Lambda-based builds, fast functions-style CI, or sub-minute builds, flag that the **Lambda fleet is not yet captured** — quote with a single-row EC2 line item as a placeholder and note the caveat in the response narrative.

## Verification

- Shape captured from a working saveAs body the calculator round-tripped on 2026-05-11 in `us-east-2` — per-service slice: `captures/saveAs/per-service/awsCodeBuild.json` (local capture, not in repo).
- Pricing API filter verified via `pricing_client.py get-products` against the live API: SKU `UB8Y5XEZW2M4GZ8Y` with rate `$0.09` per build-minute (unit `minutes`) for `regionCode=us-east-2, computeType=arm1.2xlarge, operatingSystem=Linux, computeFamily=OnDemand-EC2`.
- Formula verified: `1 build × 10 min × $0.09/min = $0.90`, matches captured `serviceCost.monthly = 0.90` exactly (within $0.00 — no rounding tolerance consumed).
- **Not yet verified**:
  - **Lambda fleet** (`computeFamily=OnDemand-Lambda`, `computeType=lambda.*`): pricing exists in the API but the `computeType` calculator-form value and unit conversion (per-second vs per-minute) are inferred — capture a fresh HAR with `computeType=ondemandlambda` before quoting.
  - **Windows fleet** (`operatingSystem=Windows` on `general1.*`): Pricing API returns rates but no round-trip capture; verify the `Operating System` form value renders correctly as `"Windows"` (vs `"Microsoft Windows Server"` or similar variant).
  - **Reserved capacity** (`computeFamily=Reserved-EC2*`): different billing model (capacity-hours, not build-minutes) — the current `calculationComponents` shape almost certainly does not match; the form likely exposes fleet-size and hours/month inputs not captured here. Capture before quoting.
  - **GPU fleet** (`gpu1.*`): rates exist in the API; form-value conventions for the dropdown are inferred from the lower-case-no-separator pattern.
  - **macOS fleet**: enumerated in `operatingSystem` attribute values but not exercised in the capture; verify before emitting.
  - **Multi-row `columnFormIPM`**: array structure verified, but splitting semantics of `buildsinaMonth` / `AvgBuildTime` across rows is unconfirmed — emit single-row arrays only.

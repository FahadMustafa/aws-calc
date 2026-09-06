# FSx for Windows File Server (`amazonFSx`, single-AZ)

This module covers **Amazon FSx for Windows File Server**, `estimateFor: "singleAZDeployment"` only. The `amazonFSx` serviceCode is reused by the SPA for other Windows FSx forms (e.g. `multiAZDeployment`), but those have not been captured. **Not covered**: FSx for Lustre, FSx for ONTAP (`amazonFSxForNetAppOntap` — different serviceCode), FSx for OpenZFS, and FSx Windows Multi-AZ deployments. Capture a saveAs body for each before quoting.

## Line-item header

```json
{
  "serviceCode":  "amazonFSx",
  "estimateFor":  "singleAZDeployment",
  "version":      "0.0.92",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon FSx for Windows File Server",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  "storageType":             {"value": "DDURBPI4tsBCssHtJz-pnpofARkXwk3q7_-D3R-POb0"}, // opaque meteredUnit id — see table below
  "storageCapacity":         {"value": "100", "unit": "gb|NA"},                          // GB; "tb|NA" also accepted
  "throughputCapacity":      {"value": "100", "unit": "mbps"},                           // MBps; unit literal "mbps"
  "ProvisionedSSDIOPS":      {"value": "AutomaticIOPS"},                                 // "AutomaticIOPS" or a numeric string like "3000"
  "percentDeduplicationSavings": {"value": "50"}                                         // integer % as string; applied to storage cost
}
```

### storageType opaque tokens

The `storageType.value` is a `meteredUnit` id from the SPA's `fsx` mappingDefinition (`pricing/2.0/meteredUnitMaps/fsx/[currency]/current/fsx.json`). It is **not** in `bundle.js`; the mapping comes from the calculator's service-definition payload (captured in `calculator.aws_new_2.har` around byte 81452500). Decoded values:

| storageType meteredUnit id | Display label | Storage class |
|---|---|---|
| `DDURBPI4tsBCssHtJz-pnpofARkXwk3q7_-D3R-POb0` | SSD | SSD (default) |
| `COXw_M7uz-qDpPvlaMzztWiA2_Lwm_rHDUpeuetTnX8` | HDD | HDD |

These ids appear to be stable in the current bundle/service-definition pair (version `0.0.92`). They may change if AWS re-keys the mappingDefinition — if a future capture comes back with different tokens, re-grep the HAR for `"label":"SSD"` / `"label":"HDD"` adjacent to `"mappingDefinitionName":"fsx"` and update this table.

### ProvisionedSSDIOPS

`"AutomaticIOPS"` is the default — IOPS scale with storage capacity (3 IOPS/GB-mo) and are included in the storage charge, no extra cost line. To over-provision: set `value` to a numeric string (e.g. `"3000"`) and the SPA charges `$0.012/IOPS-mo` (Single-AZ, us-east-2) for IOPS above the included baseline. The captured estimate uses Automatic, so the formula below assumes no IOPS surcharge — add `(provisioned - 3 * GB) * $/IOPS-mo` if the user provisions custom IOPS.

### percentDeduplicationSavings

NOT cosmetic — it's applied to the storage cost. Default `"50"` (50% savings, AWS's typical Windows-workload estimate). Set to `"0"` to disable. The throughput charge is unaffected.

## Pricing API filters

Pricing API ServiceCode is `AmazonFSx` (capital A, capital F).

### Storage (per GB-month)

```
--service-code AmazonFSx
--filter regionCode=<region>
--filter fileSystemType=Windows
--filter productFamily=Storage
--filter storageType=<SSD|HDD>
--filter deploymentOption=Single-AZ
```

Returns one SKU with one OnDemand priceDimension, flat rate.

us-east-2 rates (verified 2026-05-11):
- SSD Single-AZ: `$0.130 / GB-Mo`
- HDD Single-AZ: `$0.013 / GB-Mo`
- (For reference, Multi-AZ: SSD `$0.230`, HDD `$0.025`.)

### Throughput capacity (per MBps-month)

```
--service-code AmazonFSx
--filter regionCode=<region>
--filter fileSystemType=Windows
--filter productFamily=Provisioned Throughput
--filter deploymentOption=Single-AZ
```

us-east-2: `$2.20 / MiBps-Mo` Single-AZ (`$4.50` Multi-AZ).

### Provisioned SSD IOPS (only if `ProvisionedSSDIOPS` is numeric)

```
--service-code AmazonFSx
--filter regionCode=<region>
--filter fileSystemType=Windows
--filter productFamily=Provisioned IOPS
--filter deploymentOption=Single-AZ
```

us-east-2: `$0.012 / IOPS-Mo` Single-AZ.

## Multipliers / formula

```
storage_rate    = lookup($/GB-mo for storageType class, region, deploymentOption=Single-AZ)
throughput_rate = lookup($/MBps-mo for Single-AZ throughput, region)

raw_storage   = storageCapacity_GB * storage_rate
storage_cost  = raw_storage * (1 - percentDeduplicationSavings/100)
throughput_cost = throughputCapacity_MBps * throughput_rate

iops_cost = 0  if ProvisionedSSDIOPS == "AutomaticIOPS"
          = max(0, provisioned_iops - 3 * storageCapacity_GB) * iops_rate  otherwise

serviceCost.monthly = storage_cost + throughput_cost + iops_cost
serviceCost.upfront = 0
```

Round to two decimal places to match the SPA's display.

## Verification

- Captured saveAs slice: `captures/saveAs/per-service/amazonFSx.json` (local capture, not in repo) (region us-east-2, version `0.0.92`).
- Captured `serviceCost.monthly = 226.50`. Reproduced:
  - storage: `100 * 0.130 * (1 - 0.50) = $6.50`
  - throughput: `100 * 2.20 = $220.00`
  - total: `$226.50` — exact match.
- This confirms `percentDeduplicationSavings` IS applied to the storage cost (not cosmetic), and `ProvisionedSSDIOPS=AutomaticIOPS` adds zero.
- storageType hash → label mapping was resolved from `captures/calculator.aws_new_2.har` (mappingDefinition for the FSx service). The hash was NOT present in `bundle.js`.
- HDD rate documented from the Pricing API but not yet round-tripped via a saveAs capture — verify before quoting an HDD estimate. The hash to use for HDD is `COXw_M7uz-qDpPvlaMzztWiA2_Lwm_rHDUpeuetTnX8`.
- Custom (non-Automatic) `ProvisionedSSDIOPS` is documented from the Pricing API + bundle inspection but not round-tripped — verify before quoting.

## configSummary template

Match the captured phrasing:

```
Provisioned SSD IOPS (Automatic), Desired storage capacity (<N> GB), Desired aggregate throughput (<M> MBps)
```

For custom IOPS, replace `(Automatic)` with `(<N> IOPS)`. The `percentDeduplicationSavings` field does NOT appear in the captured configSummary — the SPA hides it from the line-item card title.

## Defaults

| Field | Default | Why |
|---|---|---|
| storageType | `DDURBPI4tsBCssHtJz-pnpofARkXwk3q7_-D3R-POb0` (SSD) | SPA's `defaultOption` for the dropdown |
| storageCapacity | "100" gb | Match captured baseline |
| throughputCapacity | "100" mbps | Match captured baseline |
| ProvisionedSSDIOPS | "AutomaticIOPS" | Most common; scales with storage at no extra cost |
| percentDeduplicationSavings | "50" | AWS's standard Windows-workload estimate |

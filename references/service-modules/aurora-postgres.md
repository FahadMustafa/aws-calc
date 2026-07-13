# Aurora PostgreSQL (`amazonRDSAuroraPostgreSQLCompatibleDB`)

Single line item that covers the Aurora PostgreSQL cluster: provisioned and/or Serverless v2 / Limitless instances, cluster storage (Standard or I/O-Optimized), I/O requests, backups, snapshot export to S3, RDS Proxy, Database Insights advanced, and Aurora Extended Support. **Not the same as `amazonRDSPostgreSQLDB`** — Aurora's storage is cluster-volume rather than instance-attached EBS, the I/O-Optimized configuration changes both instance and storage SKUs, and Serverless v2 / Limitless are billed in Aurora Capacity Unit hours, not instance-hours.

## Line-item header

```json
{
  "serviceCode":  "amazonRDSAuroraPostgreSQLCompatibleDB",
  "estimateFor":  "AuroraPostgreSQLCompatibleDB",
  "version":      "0.0.149",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Aurora PostgreSQL-Compatible DB",
  "description":  null
}
```

`estimateFor`, `version`, and `serviceName` are taken verbatim from the captured saveAs body — see Verification.

## calculationComponents (verified shape)

```jsonc
{
  "edition":                  {"value": "auroraStandard"},               // auroraStandard | auroraIOOptimized
                                                                          //   selects Standard storage + per-IO charge
                                                                          //   OR I/O-Optimized storage with no per-IO charge

  "columnFormIPM": {                                                      // one row per (instance type x term) combination
    "value": [
      {
        "Instance Type":     {"value": "db.r6g.large"},                  // provisioned class, or "Serverless v2" / "Aurora Limitless"
                                                                          //   for ACU-priced tiers
        "Number of Nodes":   {"value": "1"},                              // writer + reader count covered by this row
        "TermType":          {"value": "Reserved"},                       // OnDemand | Reserved  (Reserved REQUIRES the two fields below)
        "LeaseContractLength": {"value": "1yr"},                          // Reserved only: "1yr" | "3yr"
        "PurchaseOption":    {"value": "No Upfront"},                     // Reserved only: "No Upfront" | "Partial Upfront" | "All Upfront"
        "undefined": {                                                    // utilization (the form schema literally keys this "undefined")
          "value": {
            "selectedId":    "%Utilized/Month",                           // %Utilized/Month | Hours/Month | Hours/Day | Hours/Week
            "unit":          "100"                                        // numeric value as a string (percent or hour-count)
          }
        }
      }
    ]
  },
  // PRICING STRATEGY (TermType) — the SPA splits Reserved pricing into THREE separate row fields.
  //   On-Demand: TermType="OnDemand" only; omit LeaseContractLength / PurchaseOption.
  //   Reserved : TermType="Reserved" PLUS LeaseContractLength ("1yr"|"3yr") PLUS PurchaseOption
  //              ("No Upfront"|"Partial Upfront"|"All Upfront"). 1yr/No-Upfront IS offered for
  //              provisioned r6g classes. Aurora has no Convertible class (Standard offering only).
  //   DO NOT use the OLD packed string TermType:"Reserved-1yr-No-Upfront-Standard" — the SPA does
  //   not recognize it and recomputes the RI line to ~15% of stored (instance cost drops out,
  //   only storage/IO remain). See the "Recompute fix" note in Verification.

  "storageAmount":            {"value": "100", "unit": "gb|NA"},          // cluster volume GB. Billed identically for all instances —
                                                                          //   do NOT multiply by Number of Nodes.

  "totalReads_BaseIO":        {"unit": "perSecond", "value": "1"},        // baseline read IOPS. Only billed when edition=auroraStandard.
                                                                          //   SPA converts to per-million-IO/month behind the scenes.
  "totalWrites_PeakIO":       {"unit": "perSecond", "value": "1"},        // baseline + peak write IOPS, same rules.
  "durationPeakWriteId":      {"unit": "perMonth", "value": "1"},         // hours per month at peak write rate (for the peak band only).

  "retentionPeriod":          {"value": "0"},                              // days of continuous backups beyond the free 1-day allocation.
                                                                          //   0 = stay within free tier.
  "additionalBackupStorage":  {"unit": "gb|NA", "value": "100"},          // additional backup storage GB-month over the free allotment.
  "snapshotExport":           {"unit": "perMonth", "value": "100"},       // GB of snapshot data exported to S3 per month.

  "createRDSProxy":           {"value": "1"},                              // "0" off, "1" on. ACU-priced for serverless rows, vCPU-hour for provisioned.
  "DatabaseInsightsSelected": {"value": "1"},                              // "0" standard (free), "1" advanced (paid per vCPU-hr).
  "addRDSExtendedSupport":    {"value": "1"},                              // "0" off, "1" on. Paid per vCPU-hr after the standard-support window.
  "RDSExtendedSupportYear":   {"value": "year12"}                          // year12 (yrs 1-2 rate) | year3 (yr 3 rate).
}
```

### Fields the SPA accepts but the capture didn't exercise

Treat the following as "verify before relying on this" — the captured body uses provisioned `db.r6g.large` Aurora Standard and does not set them:

- **Aurora Serverless v2 / Limitless**: the column-form row's `Instance Type` switches to a Serverless ACU class and the schema typically grows a `serverlessV2_minACU` / `serverlessV2_maxACU` pair (names not yet confirmed from a Serverless capture). Do not invent these — capture a HAR with a Serverless v2 estimate first.
- **Aurora Global Database**: cross-region replication of write I/O. The form usually adds a `globalDatabaseEnabled` flag plus a per-month replicated-write-IO count. Not present in the capture.
- **Performance Insights paid retention**: only Database Insights Advanced is captured. Pure Performance-Insights paid retention (beyond the free 7 days) appears to ride along with `DatabaseInsightsSelected="1"` but the breakout field name is unconfirmed.

When the user asks for any of the above, mark the line item in the breakdown and tell them a Serverless / Global / paid-PI capture is needed before pricing is faithful.

## Pricing API filters

All filters target `--service-code AmazonRDS --filter databaseEngine="Aurora PostgreSQL" --filter regionCode=<region>` plus the ones listed per dimension. Run them in parallel.

### Provisioned DB instance — On-Demand

```
--filter instanceType=<db.r6g.large|db.r6i.xlarge|...>
--filter deploymentOption=Single-AZ
```

Aurora returns **two SKUs per instance type** in the same query — one for Aurora Standard (`storage=EBS Only`) and one for I/O-Optimized (`storage=Aurora IO Optimization Mode`). Pick by `edition`:
- `edition=auroraStandard` → SKU with `storage=EBS Only`
- `edition=auroraIOOptimized` → SKU with `storage=Aurora IO Optimization Mode`

Aurora is always `deploymentOption=Single-AZ` at the pricing layer — read replicas are added by raising `Number of Nodes`, not by switching to Multi-AZ. The other `deploymentOption` values in `get-attribute-values` are for non-Aurora engines.

The matching SKU has one OnDemand priceDimension; `price_per_unit` is the hourly rate (USD/Hr).

### Provisioned DB instance — Reserved (1Y / 3Y, No / Partial / All Upfront)

Same filters as On-Demand. The Aurora Standard (`storage=EBS Only`) SKU carries Reserved terms keyed by `LeaseContractLength` (`1yr`/`3yr`), `PurchaseOption` (`No Upfront`/`Partial Upfront`/`All Upfront`), and `OfferingClass=standard` (Aurora does not offer Convertible RIs). Reserved terms have two priceDimensions:
- one in `Hrs` — recurring hourly charge (multiply by 730)
- one in `Quantity` — upfront one-time fee

The I/O-Optimized SKU sometimes does **not** publish RI terms; if a 1Y/3Y RI is requested with `edition=auroraIOOptimized` and no RI rates are returned, fall back to the Aurora Standard RI discount percentage applied to the I/O-Optimized On-Demand rate and note the fallback in the breakdown.

### Cluster storage

```
--filter productFamily="Database Storage"
```

Returns two SKUs in the same query:
- `volumeType=General Purpose-Aurora` (Aurora Standard) — about $0.10/GB-month in us-east-2
- `volumeType=IO Optimized-Aurora` — about $0.225/GB-month in us-east-2

Pick by `edition`. Single `GB-Mo` OnDemand priceDimension each. Multiply by `storageAmount` once per cluster (storage is shared across nodes; do not multiply by `Number of Nodes`).

### I/O requests (Aurora Standard only)

```
--filter productFamily="System Operation"
--filter group="Aurora I/O Operation"
```

Filter the result set further to the SKU whose `usagetype` ends `:StorageIOUsage` (drop any `-LimitlessPreview` SKUs). The rate is per-IO (priced about $0.20 per million IO in us-east-2). The SPA converts the `totalReads_BaseIO` and `totalWrites_PeakIO` IOPS values to a monthly IO count internally (~`iops * 3600 * 730` per band, with `durationPeakWriteId` controlling how many hours the peak write band runs). Set `totalReads_BaseIO` and `totalWrites_PeakIO` to `"1"` when the user has no IO estimate so the line item builds cleanly with negligible IO cost — verify before relying on this if precise IO cost matters.

When `edition=auroraIOOptimized`, skip this SKU entirely — I/O is bundled into the higher instance and storage rates.

### Backups — additional backup storage

```
--filter productFamily="Storage Snapshot"
```

Pick the SKU whose `usagetype` is `<RegionPrefix>-Aurora:BackupUsage` (drop `-LimitlessPreview` variants). One OnDemand `GB-Mo` priceDimension. Multiply by `additionalBackupStorage`. `retentionPeriod` days is informational only inside this calculator — the SPA uses `additionalBackupStorage` as the billable input.

### Snapshot export to S3

```
--filter productFamily="System Operation"
--filter group="RDS Snapshot Export"
```

One OnDemand `GB` priceDimension. Multiply by `snapshotExport.value`.

### RDS Proxy

```
--filter productFamily="RDSProxy"
```

Two SKUs:
- `usagetype` ending `:ProxyUsage` — vCPU-hour rate for **provisioned** Aurora instances (multiply by vCPU count of the underlying instance type, times `730 * Number of Nodes`).
- `usagetype` ending `:Proxy-ASv2-Usage` — ACU-hour rate for **Serverless v2** Aurora. Multiply by min ACUs allocated to the proxy (the SPA exposes this in a separate field once a Serverless row is added — not yet confirmed; verify before relying on this).

### Database Insights Advanced

```
--filter productFamily="Performance Insights"
```

Pick the SKU whose `usagetype` carries the `PI_LTR_*` substring for the instance family of your provisioned row (`PI_LTR_AMR` for Graviton, `PI_LTR_FMR` for Intel/AMD, `:Serverless` suffix for Serverless v2). Rate is per ACU-month of retention. The SPA's monthly cost is `rate * vCPUs * 730 * Number_of_Nodes` once `DatabaseInsightsSelected="1"` — but the precise conversion between ACU-month and vCPU-hr varies by SKU; verify before relying on this for total cost.

### Aurora Extended Support

```
--filter productFamily="Database Instance"
--filter extendedSupportPricingYear=<year1Andyear2|year3>
```

Returns per-vCPU-hour rate (`year12` for years 1+2, `year3` for year 3). Multiply by `vcpu * 730 * Number_of_Nodes` when `addRDSExtendedSupport="1"`.

### Aurora Global Database (cross-region replicated write IO)

```
--filter productFamily="Aurora Global Database"
```

Per-IO rate. Not exercised in the captured body — verify before relying on this.

### Aurora Limitless

```
--filter productFamily="Limitless"
```

ACU-hour rate (`USE2-Aurora:IO-OptimizedLimitlessACUUsage-Limitless` in us-east-2 — Limitless is I/O-Optimized only). Drop any `-LimitlessPreview` SKUs whose rate is $0.00. Use only when the user has explicitly chosen Aurora Limitless; verify before relying on this — no captured working POST yet.

## Multipliers / formula

```
# Pull these once based on edition:
inst_hr      = instance_hourly_rate(edition, instance_type, region)
storage_rate = storage_per_gb_month(edition, region)         # General Purpose-Aurora OR IO Optimized-Aurora
io_rate      = io_per_million(region) if edition == "auroraStandard" else 0
backup_rate  = backup_per_gb_month(region)
export_rate  = snapshot_export_per_gb(region)
proxy_rate   = proxy_per_vcpu_hour(region)                   # for provisioned rows
insight_rate = pi_advanced_per_acu_month(region, family)
ext_rate     = extended_support_per_vcpu_hour(region, year_band)

util_fraction = utilization_unit_to_fraction("undefined".value)   # 100 / 100 for %Utilized/Month
nodes         = int(columnFormIPM[row].Number_of_Nodes)
vcpu          = vcpu_of(instance_type)
hours_per_mo  = 730

# Provisioned compute (per row, sum across rows):
compute_monthly = inst_hr * hours_per_mo * util_fraction * nodes

# Cluster storage (once per cluster, not per node):
storage_monthly = storage_rate * storageAmount

# I/O requests (Aurora Standard only):
read_io_per_mo  = totalReads_BaseIO * 3600 * hours_per_mo
peak_write_io   = totalWrites_PeakIO * 3600 * durationPeakWriteId           # peak hours only
base_write_io   = totalWrites_PeakIO * 3600 * (hours_per_mo - durationPeakWriteId) * 0.5  # rough base estimate
io_monthly      = io_rate * (read_io_per_mo + peak_write_io + base_write_io)
# WARNING: the SPA's exact IO model is NOT reverse-engineered (note the `* 0.5` "rough base
# estimate" above). For write/read-heavy clusters, Aurora Standard I/O can be the dominant cost,
# so an unverified model can be off by large factors. Do ONE of:
#   (a) keep totalReads_BaseIO / totalWrites_PeakIO at "1" (near-zero IO) when the user has no
#       IO estimate, and state that IO is excluded; or
#   (b) steer the user to edition=auroraIOOptimized, where per-IO is bundled (io_rate=0) and this
#       whole risk disappears (compare total cost both ways); or
#   (c) capture a HAR with real IO values and re-derive before quoting an IO-heavy Standard cluster.
# Do not hand off a computed IO cost for a non-trivial IO workload as if it were accurate.

# Backups & exports:
backup_monthly  = backup_rate * additionalBackupStorage
export_monthly  = export_rate * snapshotExport

# Add-ons (only when their flag == "1"):
proxy_monthly   = proxy_rate * vcpu * hours_per_mo * nodes       if createRDSProxy=="1"           else 0
insight_monthly = insight_rate * vcpu * hours_per_mo * nodes     if DatabaseInsightsSelected=="1" else 0
ext_monthly     = ext_rate * vcpu * hours_per_mo * nodes         if addRDSExtendedSupport=="1"    else 0

serviceCost.monthly = sum_of_all_of_the_above
serviceCost.upfront = sum of any RI All/Partial Upfront amounts across rows
```

For Reserved rows, replace `inst_hr * hours_per_mo` with the Reserved `Hrs` priceDimension times 730 and add the `Quantity` upfront fee to `serviceCost.upfront`. For 1Y All Upfront the `Hrs` rate is 0 and the full term cost lives in the upfront fee. The Reserved selection is encoded in the `columnFormIPM` row as the three split fields `TermType:"Reserved"` + `LeaseContractLength` + `PurchaseOption` (see the calculationComponents shape) — NOT a single packed `TermType` string.

## configSummary template

Match the captured phrasing style so the saved estimate's card title renders normally:

```
Aurora PostgreSQL Cluster Configuration Option (<Aurora Standard|Aurora I/O-Optimized>), Quantity (<N>), Instance type (<db.x.y>), Utilization (<N> %Utilized/Month), Pricing strategy (<OnDemand|Reserved 1yr ...>), Storage amount (<N> GB), Total Size of Backup Processed for Export (GB) (<N> per month), Additional backup storage (<N> GB)
```

The captured body uses exactly this layout — keep the parenthetical phrasing and units. Append `, RDS Proxy enabled` / `, Database Insights Advanced` / `, Aurora Extended Support` only if the SPA writes those into the summary; the captured example does not even though all three flags are set, so leave them out unless a later capture proves otherwise — verify before relying on this.

## Defaults

| Field | Default | Why |
|---|---|---|
| `edition` | `auroraStandard` | Matches the calculator's UI default; cheaper for low-IO workloads. Flag in the breakdown so the user can switch to I/O-Optimized for write-heavy workloads. |
| `Instance Type` | `db.r6g.large` | Graviton2 mid-size; same class the capture uses. |
| `Number of Nodes` | `"1"` | Single writer, no read replicas. |
| `TermType` | `OnDemand` | No commitment. |
| `undefined` (utilization) | `{selectedId: "%Utilized/Month", unit: "100"}` | Full utilization. |
| `storageAmount` | `"100"` GB | Modest baseline matching the captured body. |
| `totalReads_BaseIO` | `"1"` per second | Placeholder so the field is well-formed; near-zero cost. Flag for users with real IOPS data. |
| `totalWrites_PeakIO` | `"1"` per second | Same. |
| `durationPeakWriteId` | `"1"` hour/month | Same. |
| `retentionPeriod` | `"0"` | Stay within the free 1-day continuous-backup allocation. |
| `additionalBackupStorage` | `"0"` GB | Don't bill backups unless the user asks. (Capture uses 100; the calculator accepts 0.) |
| `snapshotExport` | `"0"` GB/month | No exports unless requested. |
| `createRDSProxy` | `"0"` | Off — Proxy adds meaningful cost. |
| `DatabaseInsightsSelected` | `"0"` | Standard (free) insights only. |
| `addRDSExtendedSupport` | `"0"` | Off; only relevant on legacy major versions past EOL. |
| `RDSExtendedSupportYear` | `"year12"` | Cheaper of the two bands; only used when Extended Support is on. |

## Verification

### Recompute fix (2026-06, live-SPA verified)

The prior module encoded Reserved Instance pricing as a single packed field `TermType: {"value": "Reserved-1yr-No-Upfront-Standard"}`. The SPA does **not** recognize that string: on "Update estimate" Aurora RI lines recomputed to ~15% of stored (e.g. $2600.26 → $404.61 — instance cost dropped out, only storage/IO survived). The live form splits RI pricing into **three** separate fields inside each `columnFormIPM` row: `TermType: "Reserved"`, `LeaseContractLength: "1yr"` (or `"3yr"`), `PurchaseOption: "No Upfront"` (or `"Partial Upfront"`/`"All Upfront"`). 1yr/No-Upfront Reserved IS offered for provisioned r6g classes (terms 1yr/3yr; payment All/Partial/No Upfront). The three-field shape above is now the verified, recompute-safe encoding. (One-line reminder: the OLD packed-string form recomputes to ~15% of stored.)

Verified against four fragments captured from the LIVE AWS Pricing Calculator SPA (all recompute-safe, all 1yr / No Upfront / Reserved). The `/tmp/rbm_frags/*.json` paths below were ephemeral (path was ephemeral; file lost — re-capture needed):
- `/tmp/rbm_frags/31.json` — eu-west-1, 2× `db.r6g.4xlarge` Multi-AZ (`Number of Nodes`=2), 3000 GB, `totalReads_BaseIO`≈129.2211913657119 preserved for ~$75/mo I/O; `serviceCost.monthly` = $2599.87.
- `/tmp/rbm_frags/56.json` — eu-west-1, 1× `db.r6g.xlarge` Single-AZ, 250 GB; `serviceCost.monthly` = $302.49.
- `/tmp/rbm_frags/60.json` — eu-west-1, 1× `db.r6g.large`, 100 GB; `serviceCost.monthly` = $148.82.
- `/tmp/rbm_frags/115.json` — eu-central-1, 1× `db.r6g.4xlarge` (Aurora Global Database secondary), 3000 GB; `serviceCost.monthly` = $1716.55.

Note on I/O: idx31 preserves `totalReads_BaseIO` ≈ 129.22 (per second) which the SPA prices at ~$75/mo. Keep real captured IO values verbatim — do not reset them to the `"1"` placeholder when a fragment carries a measured rate.

- **Ground-truth HAR file**: `/home/fahadmustafa/src/aws-calc/captures/saveAs/per-service/amazonRDSAuroraPostgreSQLCompatibleDB.json` — provisioned `db.r6g.large` Aurora Standard in `us-east-2`, single node, 100% utilization, 100 GB cluster storage, 100 GB additional backup, 100 GB/month snapshot export, RDS Proxy on, Database Insights Advanced on, Aurora Extended Support on (year1+2), IO placeholders at `1/sec`. captured `serviceCost.monthly` = $243.58, `upfront` = $0.
- **Verified end-to-end** (captures are real working POSTs): provisioned-instance shape, Aurora Standard edition, both OnDemand and the 3-field Reserved pricing strategy, cluster storage field, backup-storage and snapshot-export fields, all three add-on flags, the `"undefined"` utilization key, the preserved measured-IO value, and the configSummary phrasing.
- **Verify before relying on this**:
  - Aurora Serverless v2 / Limitless row shape (min/max ACU field names not captured)
  - Aurora Global Database flag and replicated-write-IO field
  - Performance Insights paid retention field separate from `DatabaseInsightsSelected`
  - The SPA's exact IO accounting from `totalReads_BaseIO` / `totalWrites_PeakIO` / `durationPeakWriteId` to monthly IO count
  - Whether RDS Proxy / Database Insights / Extended Support are reflected in `configSummary` when enabled (they are not in the capture despite being on)
  - I/O-Optimized RI rates when the I/O-Optimized SKU has no published Reserved terms
  - Aurora Standard vs I/O-Optimized RI parity (Convertible offering class is not available for Aurora)

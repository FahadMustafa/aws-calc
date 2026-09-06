# RDS for PostgreSQL (`amazonRDSPostgreSQLDB`)

Single-line-item service with one or more DB instance entries inside a column-form list. Covers the DB instance(s), storage, RDS Proxy, Database Insights, backups, and Extended Support add-ons.

## Line-item header

```json
{
  "serviceCode":  "amazonRDSPostgreSQLDB",
  "estimateFor":  "rdsForPostgreSQL",
  "version":      "0.0.111",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon RDS for PostgreSQL",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  "createRDSProxy":            {"value": "0"},                      // "0" = no, "1" = yes
  "DatabaseInsightsSelected":  {"value": "0"},                      // "0" = standard, "1" = advanced
  "addRDSExtendedSupport":     {"value": "0"},                      // "0" off, "1" on
  "RDSExtendedSupportYear":    {"value": "year12"},                 // year12 (yrs 1+2) / year3 (yr 3)
  "retentionPeriod":           {"value": "0"},                      // backup retention days
  "storageAmount":             {"value": "100", "unit": "gb|NA"},
  "storageVolume":             {"value": "General Purpose"},        // see the corrected option list below — **"Aurora" is NOT a value of this field**
  "columnFormIPM": {                                                // one entry per DB-instance row
    "value": [
      {
        "Number of Nodes":    {"value": "1"},
        "Instance Type":      {"value": "db.m5.large"},
        "undefined": {                                              // utilization (key is literally "undefined")
          "value": {
            "unit":       "100",
            "selectedId": "%Utilized/Month"
          }
        },
        "Deployment Option":  {"value": "Multi-AZ"},                // Single-AZ | Multi-AZ | Multi-AZ (readable standby) | Multi-AZ Cluster
        "TermType":           {"value": "OnDemand"}                 // OnDemand only is verified here — see the Reserved warning below
      }
    ]
  }
}
```

The `columnFormIPM.value` is an array — push one entry per distinct (instance type × deployment × term) combination. Use `Number of Nodes` to multiply within a row.

The `"undefined"` key is unfortunate but literal — the SPA's form schema uses it as the column id for utilization. Do not rename.

### `storageVolume` values — **correction**

> **`"Aurora"` is not a legal `storageVolume` value.** This module previously listed `General Purpose | Provisioned IOPS | Aurora`. Form 0.0.111's dropdown has exactly five option ids, and Aurora is not among them — Aurora is a different `serviceCode` entirely (`amazonRDSAuroraPostgreSQLCompatibleDB`, see `aurora-postgres.md`). Sending `"Aurora"` here gives the SPA a value it cannot resolve.

| UI label | `storageVolume.value` |
|---|---|
| General Purpose SSD (gp2) | `General Purpose` (form default) |
| General Purpose SSD (gp3) | `General Purpose-GP3` |
| Provisioned IOPS SSD (io1) | `Provisioned IOPS` |
| Provisioned IOPS SSD (io2) | `Provisioned IOPS-IO2` |
| Magnetic (previous generation) | `Magnetic` |

### Fields present in form 0.0.111 that no capture exercised

Read from the live form definition — **inferred, not capture-verified**. Emit only when the gating condition holds, and recompute-validate.

```jsonc
{
  // Storage sizing companions to storageVolume. Each is gated on the matching
  // storageVolume value; the sibling rds-sqlserver.md has capture-verified gp3Iops /
  // gp3Throughput on its own form, so those two are the safest of this group.
  "gp3Iops":            {"value": "12000"},                // storageVolume == "General Purpose-GP3"; form default 12000
  "gp3Throughput":      {"value": "500", "unit": "mbps"},  // same gate; form default 500
  "provisioningIOPS":   {"value": "1000"},                 // storageVolume == "Provisioned IOPS"     (io1); form default 1000
  "provisionedIOPSIO2": {"value": "1000"},                 // storageVolume == "Provisioned IOPS-IO2" (io2); form default 1000

  "dedicatedLogVolume": {"value": "0"},                    // "1" yes / "0" no; form default "0"
  "numberOfHoursOnES":  {"value": "730", "unit": "perMonth"},  // hours running on RDS Extended Support (frequency field)
  "additionalBackupStorage": {"value": "0", "unit": "gb|NA"},  // backup storage beyond the retention window
  "snapshotExport":     {"value": "0", "unit": "perMonth"}     // total GB of backup processed for export
}
```

Note the gp3 form defaults here (12000 IOPS / 500 MiBps) differ from SQL Server's (3000 / 125) — do not copy the SQL Server baselines onto a Postgres line.

### Reserved TermType encoding — WARNING (recompute-unsafe pattern; unverified here)

> **Do not emit a Reserved line without recompute-validating it first.** A single packed `TermType` string such as `"Reserved-1yr-No-Upfront-Standard"` (or `-Partial-Upfront-`, `-All-Upfront-`, `-3yr-` variants) is the **exact pattern proven recompute-unsafe** on the shared RDS/Oracle form family. See `rds-sqlserver.md` ("Recompute fragility & combo validation" and the Verification section): three fragments captured from the live calculator.aws SPA confirm that the packed string is unrecognized and the line **silently recomputes to $0.00** on "Update estimate". The sibling `aurora-postgres.md` documents the same packed pattern collapsing Reserved lines to ~15% of stored on recompute. Only `TermType: "OnDemand"` is verified on this Postgres form — On-Demand lines are unaffected by this bug.

**PostgreSQL uses its own form (`estimateFor: "rdsForPostgreSQL"`), not the shared `rdsForOracle` form**, so the packed encoding here is **UNVERIFIED — not proven-broken** (no captured Postgres saveAs exercises Reserved). It is unsafe to assume it works; treat it as likely-broken until proven otherwise.

**Likely-correct alternative (also UNVERIFIED for Postgres).** The recompute-safe encoding that `rds-sqlserver.md` and `aurora-postgres.md` verified on their forms is three separate sibling fields inside the `columnFormIPM` row, not a packed string:

```jsonc
"TermType":            {"value": "Reserved"},          // OnDemand | Reserved
"LeaseContractLength": {"value": "1yr"},               // Reserved only: "1yr" | "3yr"
"PurchaseOption":      {"value": "No Upfront"}         // Reserved only: "No Upfront" | "Partial Upfront" | "All Upfront"
```

For On-Demand, emit `TermType: "OnDemand"` and **omit** `LeaseContractLength` / `PurchaseOption` entirely (as the verified shape above shows). This three-field shape is the *likely* correct Postgres encoding by analogy to the sibling forms, but it has **not** been captured or recompute-validated on `rdsForPostgreSQL`.

**Instruction: do NOT emit Reserved PostgreSQL lines unless you have recompute-validated the encoding** by driving the live SPA's "Update estimate" click (per `SKILL.md` step 7) or by capturing a fresh HAR with a Reserved Postgres estimate. If you cannot validate, drop to `TermType: "OnDemand"` or refuse the Reserved request — do not guess. On-Demand lines need no such validation.

## Pricing API filters

### DB instance OnDemand

```
--service-code AmazonRDS
--filter instanceType=<db.m5.large>
--filter databaseEngine=PostgreSQL
--filter deploymentOption=<Single-AZ|Multi-AZ|Multi-AZ (readable standbys)>
--filter regionCode=<region>
```

`get-attribute-values --service-code AmazonRDS --attribute deploymentOption` enumerates the valid display strings (note the parentheses for "Multi-AZ (readable standbys)").

### DB instance Reserved

Same filters as above; the returned SKU includes Reserved terms keyed by `LeaseContractLength` and `PurchaseOption` and `OfferingClass=standard|convertible`.

### Storage (gp2 / gp3 / io1)

```
--service-code AmazonRDS
--filter productFamily="Database Storage"
--filter regionCode=<region>
--filter "volumeName=General Purpose|General Purpose-GP3|Provisioned IOPS"
```

### Backups (after free tier)

```
--service-code AmazonRDS
--filter productFamily="Storage Snapshot"
--filter regionCode=<region>
```

### RDS Proxy

```
--service-code AmazonRDS
--filter productFamily="DB Proxy"
--filter regionCode=<region>
```

### Database Insights (advanced)

```
--service-code AmazonRDS
--filter productFamily="Database Insights"
--filter regionCode=<region>
```

(Capture a HAR for these add-ons before claiming high accuracy — they're rarely-exercised endpoints.)

## Multipliers / formula

```
db_compute_monthly = hourly * 730 * (utilization_pct / 100) * Number_of_Nodes
db_storage_monthly = gp_per_gb_month * storageAmount             # per the storageVolume class
db_backup_monthly  = 0   # see warning below — NOT a defined days->GB-month conversion
proxy_monthly      = proxy_per_hour * 730 * Number_of_Nodes      # if createRDSProxy=="1"
insights_monthly   = insights_per_vcpu_hr * 730 * vcpu * Number_of_Nodes  # if DatabaseInsightsSelected=="1"
extended_monthly   = ext_per_vcpu_hr * 730 * vcpu                # if addRDSExtendedSupport=="1"

serviceCost.monthly = sum
serviceCost.upfront = sum of any RI All/Partial Upfront amounts
```

> **Backup is not modeled.** Unlike the SQL Server module (which has an explicit `additionalBackupStorage` GB field), the Postgres form exposes only `retentionPeriod` (days). There is **no defined conversion from retention days to billable GB-months** — backup storage equal to 100% of provisioned DB storage is free, and the chargeable amount depends on DB size and change rate, which the form does not collect here. The SPA's own derivation is not captured. So: keep `retentionPeriod: "0"` (the default) and treat backup as `$0` unless you capture a retention>0 estimate to learn the SPA's formula. If a user needs backup-over-free-tier priced, flag that this module cannot derive it and offer to capture a HAR.

## configSummary template

```
Storage amount (<N> GB), Storage volume (<volume display>), Nodes (<N>), Instance Type (<type>), Utilization (On-Demand only) (<N> %Utilized/Month), Deployment Option (<option>), Pricing Model (<term>)
```

## Defaults

| Field | Default | Why |
|---|---|---|
| storageVolume | General Purpose | gp2/gp3 default in RDS UI |
| storageAmount | 100 GB | Modest baseline |
| createRDSProxy | "0" | Off |
| DatabaseInsightsSelected | "0" | Standard insights only |
| addRDSExtendedSupport | "0" | Off |
| retentionPeriod | "0" | No backup over free tier |
| Number of Nodes | "1" | Single node |
| Deployment Option | Single-AZ | Cheaper baseline; flag for production |
| utilization | 100% | Full utilization |
| TermType | OnDemand | No commitment |

## Verification

**Captured ground truth**: the captured estimate uses `db.m4.2xlarge Multi-AZ` with all add-ons enabled — read it for a working sample shape. The reconciliation of that captured estimate is the basis for the field names and On-Demand shape below.

**Verified** (from the captured On-Demand estimate):
- Top-level header (`serviceCode`, `estimateFor: "rdsForPostgreSQL"`, `version`, `serviceName`).
- `calculationComponents` field names, nesting, and value types for the On-Demand shape shown above.
- The `columnFormIPM` row shape for `TermType: "OnDemand"` (including the literal `"undefined"` utilization key).

**Inferred / NOT yet verified — `verify before relying on this`**:
- **Reserved `TermType` encoding.** No captured Postgres saveAs exercises a Reserved line. The packed `"Reserved-…"` string is the pattern *proven recompute-unsafe* on the sibling `rdsForOracle` form (`rds-sqlserver.md`) and *proven to collapse to ~15%* on Aurora (`aurora-postgres.md`); the three-field `TermType`/`LeaseContractLength`/`PurchaseOption` alternative is verified on those sibling forms but **not** on `rdsForPostgreSQL`. Recompute-validate via the live SPA "Update" click or a fresh HAR before emitting any Reserved Postgres line (see the Reserved warning above).
- **Backup over free tier.** No defined retention-days → billable GB-month conversion is captured (see the backup warning under Multipliers). Keep `retentionPeriod: "0"` and treat backup as `$0` until a retention>0 estimate is captured.
- **Add-on endpoints** (RDS Proxy, Database Insights advanced): rarely-exercised — capture a HAR before claiming high accuracy on their rates.

- **Form 0.0.110 → 0.0.111 (2026-09-06).** Diffed against the live form definition (`data/amazonRDSPostgreSQLDB/en_US.json`, version `0.0.111`). Every documented cc key still exists with the same id: `createRDSProxy`, `DatabaseInsightsSelected`, `addRDSExtendedSupport`, `RDSExtendedSupportYear`, `retentionPeriod`, `storageAmount`, `storageVolume`, `columnFormIPM`. **No cc-relevant change** to the documented shape: fields added: none, renamed: none, removed: none.
- Two corrections from the same read, neither caused by this bump. (1) **`storageVolume` never had an `"Aurora"` option** — the live list is gp2/gp3/io1/io2/Magnetic; the old prose was wrong and is now flagged above. (2) Eight live input ids were undocumented (`gp3Iops`, `gp3Throughput`, `provisioningIOPS`, `provisionedIOPSIO2`, `dedicatedLogVolume`, `numberOfHoursOnES`, `additionalBackupStorage`, `snapshotExport`); they are now documented as inferred-only. Since only one form version elapsed, these almost certainly predate 0.0.110 and were simply absent from the one capture behind this module — treat them as a documentation gap being closed, not as a 0.0.111 change.
- **`references/examples/sample-saveas-body.json` was bumped to 0.0.111.** Its Postgres line uses only `createRDSProxy`, `DatabaseInsightsSelected`, `addRDSExtendedSupport`, `RDSExtendedSupportYear`, `retentionPeriod`, `storageAmount`, `storageVolume`, `columnFormIPM` — all of which exist unchanged in 0.0.111, so the bump carries no cc risk. The example's stored `serviceCost.monthly` was not re-derived.
- Only `TermType: "OnDemand"` remains verified on this form; the Reserved warning above is unchanged.
## Notes

- For other RDS engines (MySQL, MariaDB, Oracle, MS SQL, Aurora variants) the SPA uses a different `serviceCode` per engine. Add a sibling module before pricing those.

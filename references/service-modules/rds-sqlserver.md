# RDS for SQL Server (`amazonRDSForSQLServer`)

Sibling of `rds-postgres.md`. Same column-form list pattern, but the row carries three extra fields (license model, database edition, unbundled-licensing flag) and the top-level shape adds an `optimize` toggle. There is **no** Extended Support row — SQL Server pricing rolls support into the licensed editions, so `RDSExtendedSupportYear` / `addRDSExtendedSupport` from the PostgreSQL module are intentionally absent.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| Reserved 3-field encoding (`TermType: "Reserved"` + `LeaseContractLength` + `PurchaseOption`) | recompute-verified | live-SPA fragments 20.json / 105.json (2026-06); the packed string recomputes to $0.00 on Update |
| On-Demand row (`TermType: "OnDemand"`, no Lease/Purchase fields) | recompute-verified | live-SPA fragment 30.json (2026-06, db.t3.large Web LI, $155.34) |
| Instance + gp2 storage + Proxy + Insights + backup total (db.m6i.12xlarge BYOL) | capture-verified | captured $6,232.05 reconciled to the cent (capture file lost — re-capture needed) |
| gp3 storage with `gp3Iops` / `gp3Throughput` | capture-verified | live-SPA fragment 20.json (4800 GB gp3) |
| Database Insights Advanced rate ($0.0125/vCPU-hr) | inferred | reverse-derived from the captured total; not returned by the Pricing API |
| `optimize` toggle (vCPU cores/threads) | inferred | form 0.0.134 labels contradict the older "Optimized Reads/Writes" prose; not exercised |
| `Unbundled Licensing` value | inferred | no observed effect on cost in standard configs — treat as a label |
| Fields the captures never exercised (`vcpuThread`, `vcpuCores`, `provisioningIOPS`, `provisionedIOPSIO2`, `additionalBackupStorage`) | inferred | form 0.0.134 definition (2026-09-06) |
| Three captured shapes re-validated against form 0.0.134 | inferred | validated against 0.0.123 only; not re-run |
| Oracle on the shared `rdsForOracle` form | inferred | editions/license models not captured — refuse Oracle line items |

## Line-item header

```json
{
  "serviceCode":  "amazonRDSForSQLServer",
  "estimateFor":  "rdsForOracle",
  "version":      "0.0.134",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon RDS for SQL server",
  "description":  null
}
```

`estimateFor` is literally `"rdsForOracle"` — the SPA reuses the Oracle form template for SQL Server. Preserve verbatim; do not "fix" it. `serviceName` is captured exactly as `Amazon RDS for SQL server` (lowercase "server").

## Recompute fragility & combo validation (read before emitting)

> **Recompute fix (2026-06, live-SPA verified).** Reserved pricing must be encoded as **three separate row fields** — `TermType: "Reserved"`, `LeaseContractLength: "1yr"`, `PurchaseOption: "No Upfront"` — exactly as the live form emits them. The earlier module documented a single packed string `TermType: "Reserved-1yr-No-Upfront-Standard"`; the SPA does **not** recognize that value, so on "Update estimate" the line silently recomputed to **$0.00**. This was confirmed against three fragments captured from the live calculator.aws SPA (`20.json` Multi-AZ, `105.json` Single-AZ, `30.json` On-Demand). Other corrections from the same capture, now reflected throughout this module: `storageAmount.unit` is `"gb|NA"` (it was previously thought to be `"gb"`); the form emits `gp3Iops` and `gp3Throughput` components when `storageType` is GP3; `createRDSProxy` and `DatabaseInsightsSelected` are present even when off; and `version` was `0.0.123` at the time (the live form has since moved to `0.0.134` — see the Verification section). Note that `estimateFor: "rdsForOracle"` was **correct** and was never the bug — do not "fix" it.

This is the most recompute-fragile service in the skill. Oracle **and** SQL Server share the one `rdsForOracle` form, so a single brittle code path breaks both. Three structural traps make the recipient's "Update" fail (either with *"This service in your estimate isn't compatible with your original inputs"*, or silently recomputing to **$0.00**):

1. **No-id utilization column.** The live form's utilization column has no `id`/`selectorId` (only `type: "utilization"`, `exportValueAs: "utilizationOut"`), so it serializes to the literal key `"undefined"` with the value under `unit` and the unit under `selectedId` (see the row shape below). This is correct and must be copied verbatim — but it means the column round-trips only if every *other* field in the row resolves cleanly.
2. **Deep dependent dropdown chains.** `Database Edition` depends on `Deployment Option` + `TermType` + `License Model`; `Unbundled Licensing` depends on all four. If the stored combination is not a currently-valid dependent path, the SPA cannot resolve the dropdown on Update and throws.
3. **Reserved term encoding (the verified $0 bug).** Reserved pricing is **not** a single packed `TermType` string. It is three sibling fields in the row: `TermType: "Reserved"`, `LeaseContractLength: "1yr"`, `PurchaseOption: "No Upfront"`. The OLD packed form `TermType: "Reserved-1yr-No-Upfront-Standard"` is unrecognized and recomputes the line to **$0.00** on Update. SQL Server License-included offers **only a 1yr Reserved term** — there is no 3yr option, so never emit `LeaseContractLength: "3yr"` for SQL Server LI. For On-Demand, emit `TermType: "OnDemand"` and **omit** `LeaseContractLength`/`PurchaseOption` entirely (see `30.json`).

**Validate the combination before building the line item. Refuse (or fall back) on:**

- **BYOL + Web** — illegal; Web edition is License-included only.
- **BYOL + Express** — AWS often returns no SKU. Fall back to Standard pricing or refuse, per the filters section.
- **License-included + Enterprise Developer** — Enterprise Developer is BYOL-only (dev/test); LI is invalid.
- **Any Reserved `TermType` where the Pricing API returns no RI SKU** for that exact `instanceType` × `databaseEdition` × `deploymentOption` × `region`. Do the `get-products` RI lookup first; if it's empty, do not emit a Reserved line — drop to OnDemand or refuse. For SQL Server LI, only `LeaseContractLength: "1yr"` exists; a 3yr Reserved line will recompute to $0.
- **A `databaseEdition` not offered for that `instanceType` + license model.** Edition availability is gated by instance type. From the live capture: `db.m5.4xlarge` + License-included offers **Enterprise / Standard / Web**; `db.t3.large` + License-included offers **Express / Web** (the burstable t3 class does not offer Enterprise/Standard LI). Pick an edition the instance type actually supports, or the dropdown will not resolve on Update.
- **An `instanceType` not offered for that engine/edition/region** — confirm the OnDemand SKU exists before emitting.

Prefer `TermType: OnDemand` and a common edition (Standard / Enterprise) unless the brief forces otherwise. After saving, recompute-validate per `SKILL.md` step 7 (drive the SPA's "Update" headlessly) — the load-endpoint check will not catch these.

**Oracle RDS is not supported** — it shares this form but has different editions/license models that are not captured. Refuse Oracle line items; do not route them through this module.

## calculationComponents (verified shape)

Two captured shapes follow, copied from the live SPA. **A) Reserved + GP3 + Multi-AZ** (from `20.json`, `db.m5.4xlarge` SQL Server Standard LI 1yr-Reserved-No-Upfront, 4800 GB gp3, RDS Proxy + Database Insights on, eu-west-1, `serviceCost.monthly` = 7929.36):

```jsonc
{
  "optimize":                  {"value": "0"},                       // Optimized Reads/Writes flag — "0" off, "1" on
  "createRDSProxy":            {"value": "1"},                       // "0" no, "1" yes
  "storageAmount":             {"value": "4800", "unit": "gb|NA"},   // unit is literally "gb|NA", not "gb"
  "DatabaseInsightsSelected":  {"value": "1"},                       // "0" standard, "1" advanced
  "retentionPeriod":           {"value": "0"},                       // backup retention days
  "columnFormIPM": {                                                 // one entry per DB-instance row
    "value": [
      {
        "Number of Nodes":     {"value": "1"},
        "Instance Type":       {"value": "db.m5.4xlarge"},
        "undefined": {                                               // utilization (the key really is "undefined")
          "value": {
            "unit":       "100",
            "selectedId": "%Utilized/Month"
          }
        },
        "TermType":            {"value": "Reserved"},                // OnDemand | Reserved
        "Deployment Option":   {"value": "Multi-AZ"},                // Single-AZ | Multi-AZ
        "License Model":       {"value": "License included"},        // "Bring your own license" | "License included"
        "Database Edition":    {"value": "Standard"},                // Enterprise | Enterprise Developer | Standard | Web | Express (gated by instance type)
        "Unbundled Licensing": {"value": "FALSE"},                   // "TRUE" only when separating Microsoft licensing (License Mobility through SA); usually "FALSE"
        "LeaseContractLength": {"value": "1yr"},                     // Reserved ONLY — SQL Server LI offers 1yr only (no 3yr)
        "PurchaseOption":      {"value": "No Upfront"}               // Reserved ONLY — "No Upfront" | "Partial Upfront" | "All Upfront"
      }
    ]
  },
  "storageType":               {"value": "General Purpose-GP3"},     // General Purpose | General Purpose-GP3 | Provisioned IOPS | Provisioned IOPS-IO2 | Magnetic
  "gp3Iops":                   {"value": "3000"},                    // GP3 only — baseline 3000
  "gp3Throughput":             {"value": "125", "unit": "mbps"}      // GP3 only — baseline 125 MiBps
}
```

**Reserved is THREE fields, not one.** `TermType: "Reserved"` plus sibling `LeaseContractLength` and `PurchaseOption`. The Single-AZ variant (`105.json`) is identical except `Deployment Option: "Single-AZ"` (eu-central-1, monthly = 4278.40). Do **not** emit the old packed string `TermType: "Reserved-1yr-No-Upfront-Standard"` — the SPA does not recognize it and the line recomputes to **$0.00**.

`gp3Iops` and `gp3Throughput` are emitted **only** when `storageType` is `"General Purpose-GP3"`; omit both for any other storage type. `gp3Throughput.unit` is `"mbps"`.

**B) On-Demand + gp2 + Single-AZ** (from `30.json`, `db.t3.large` SQL Server Web LI On-Demand 84 Hours/Week, 200 GB gp2, eu-west-1, monthly = 155.34):

```jsonc
{
  "optimize":                  {"value": "0"},
  "createRDSProxy":            {"value": "1"},
  "storageAmount":             {"value": "200", "unit": "gb|NA"},
  "DatabaseInsightsSelected":  {"value": "1"},
  "retentionPeriod":           {"value": "0"},
  "columnFormIPM": {
    "value": [
      {
        "Number of Nodes":     {"value": "1"},
        "Instance Type":       {"value": "db.t3.large"},
        "undefined": {
          "value": {
            "unit":       "84",
            "selectedId": "Hours/Week"                               // utilization can be an absolute Hours/Week, not just %Utilized/Month
          }
        },
        "TermType":            {"value": "OnDemand"},                // On-Demand: NO LeaseContractLength / PurchaseOption fields
        "Deployment Option":   {"value": "Single-AZ"},
        "License Model":       {"value": "License included"},
        "Database Edition":    {"value": "Web"},                     // db.t3.large + LI offers Express / Web only
        "Unbundled Licensing": {"value": "FALSE"}
      }
    ]
  },
  "storageType":               {"value": "General Purpose"}          // gp2; NO gp3Iops / gp3Throughput
}
```

For On-Demand, the row has **no** `LeaseContractLength` and **no** `PurchaseOption` — omit them entirely. With gp2 storage there are **no** `gp3Iops`/`gp3Throughput` components.

Shared with `rds-postgres.md`: `createRDSProxy`, `DatabaseInsightsSelected`, `retentionPeriod`, `storageAmount`, `columnFormIPM` row shape (`Number of Nodes`, `Instance Type`, `undefined` utilization, `Deployment Option`, `TermType`). Read that module if any of those need explanation.

SQL-Server-specific:
- `optimize` — top-level boolean string toggling Optimized Reads/Writes; leave `"0"` unless the brief asks for it.
- `TermType` / `LeaseContractLength` / `PurchaseOption` — Reserved is encoded as three separate row fields (`TermType: "Reserved"` + `LeaseContractLength` + `PurchaseOption`), NOT a packed string. SQL Server LI offers `LeaseContractLength: "1yr"` only. For `TermType: "OnDemand"` omit the other two fields. (See the verified-shape blocks above.)
- `License Model` — `"Bring your own license"` keeps the MS licensing off the bill (you supply it under SA / License Mobility). `"License included"` bundles MS licensing into the instance hourly rate (substantially higher).
- `Database Edition` — `Enterprise`, `Enterprise Developer` (BYOL-only dev/test), `Standard`, `Web` (License-included only), `Express` (free). Availability is gated by instance type: `db.m5.4xlarge`+LI → Enterprise/Standard/Web; `db.t3.large`+LI → Express/Web.
- `Unbundled Licensing` — almost always `"FALSE"`. `"TRUE"` corresponds to the "Unbundled" SKU group the Pricing API exposes under `unbundledLicensing=TRUE`; it does not appear to change the visible monthly in standard configurations, but record it literally from the brief.
- `storageType` replaces postgres's `storageVolume` (same role, different field name). Accepted display values match the Pricing API `volumeType` strings.
- `gp3Iops` / `gp3Throughput` — emitted only when `storageType` is `"General Purpose-GP3"`. Baselines are `"3000"` IOPS and `"125"` mbps (`gp3Throughput.unit` is `"mbps"`). Omit both entirely for gp2/io1/io2/magnetic.
- `storageAmount.unit` is the literal `"gb|NA"`, not `"gb"`.
- `additionalBackupStorage` did not appear in any of the live captures; the SPA derives backup from `retentionPeriod`. It **does** exist in form 0.0.134 (subType `fileSize`, `defaultOption {size: "gb", frequency: "NA"}` → unit `"gb|NA"`, no displayIf gate), so the field name is real — but no capture has ever round-tripped it. Send it only when the user has backup storage beyond the retention window, and recompute-validate.

### Fields present in form 0.0.134 that no capture exercised

These are read from the live form definition, **inferred, not capture-verified**. Emit them only when the condition that gates them is true, and recompute-validate the line afterwards.

```jsonc
{
  // Optimize CPU — only rendered when `optimize` is "1". The `optimize` dropdown's real
  // labels are "Configure the number of vCPUs" ("1") and "Default CPU options" ("0"),
  // so it is a CPU-configuration toggle, not the Optimized Reads/Writes flag the prose
  // above calls it. Both fields have form default 0.
  "vcpuThread":         {"value": "2"},    // threads per CPU core
  "vcpuCores":          {"value": "8"},    // CPU cores

  // Provisioned-IOPS inputs, each gated on the matching `storageType` value.
  // Both have form default 1000.
  "provisioningIOPS":   {"value": "1000"}, // only when storageType == "Provisioned IOPS"   (io1)
  "provisionedIOPSIO2": {"value": "1000"}, // only when storageType == "Provisioned IOPS-IO2" (io2)

  "additionalBackupStorage": {"value": "0", "unit": "gb|NA"}
}
```

`storageType`'s five live option ids are `General Purpose` (gp2), `General Purpose-GP3`, `Provisioned IOPS` (io1), `Provisioned IOPS-IO2` (io2), `Magnetic` — matching the values already documented above. Form default is `General Purpose`.

## Pricing API filters

### DB instance OnDemand

```
--service-code AmazonRDS
--filter instanceType=<db.m6i.12xlarge>
--filter databaseEngine="SQL Server"
--filter databaseEdition=<Enterprise | Enterprise Developer | Standard | Web | Express>
--filter licenseModel=<"Bring your own license" | "License included">
--filter deploymentOption=<Single-AZ | Multi-AZ>
--filter regionCode=<region>
```

`get-attribute-values --service-code AmazonRDS --attribute databaseEdition` enumerates the editions; `Enterprise Developer` is the verbatim string for the captured config (NOT "Developer" alone — that value exists but is a different Oracle edition).

For BYOL Web is not a legal combo (Web edition is License-included only). For BYOL Express, AWS sometimes returns no SKU — fall back to Standard pricing or surface the mismatch.

### DB instance Reserved

Same filters; Reserved terms come back keyed by `LeaseContractLength`, `PurchaseOption`, `OfferingClass=standard|convertible`. These map 1:1 onto the row's three Reserved fields: `TermType: "Reserved"`, `LeaseContractLength` (SQL Server LI: `1yr` only), `PurchaseOption` (`No Upfront` | `Partial Upfront` | `All Upfront`). Look up the RI SKU before emitting; if empty for the exact instance/edition/deployment/region, drop to OnDemand.

### Storage (gp2 / gp3 / io1 / io2 / magnetic)

```
--service-code AmazonRDS
--filter productFamily="Database Storage"
--filter databaseEngine="SQL Server"
--filter databaseEdition=<edition>
--filter deploymentOption=<Single-AZ | Multi-AZ>
--filter regionCode=<region>
--filter volumeType="General Purpose"   # or General Purpose-GP3 | Provisioned IOPS | Provisioned IOPS-IO2 | Magnetic
```

Storage SKUs are edition-scoped in the API; filter `databaseEdition` to avoid pulling another edition's SKU by accident.

### Backups (over free tier)

```
--service-code AmazonRDS
--filter productFamily="Storage Snapshot"
--filter databaseEngine="SQL Server"
--filter regionCode=<region>
```

Returns ~$0.095/GB-month in us-east-2.

### RDS Proxy

```
--service-code AmazonRDS
--filter productFamily="RDSProxy"
--filter regionCode=<region>
```

Engine-agnostic in practice (`$0.015/vCPU-hour`). RDS Proxy bills a minimum of 8 vCPUs per proxy; for `Number of Nodes > 1` it bills against the sum of vCPUs of associated instances.

### Database Insights (advanced)

There is no `productFamily="Database Insights"` in the Pricing API. The published rate is **$0.0125 per vCPU-hour** in us-east-2 (matches the captured estimate to the cent). If you need to source it from the API, fall back to the `Performance Insights` family — but the FMR/AMR vCPU-month rates returned there are PI legacy and do NOT reproduce the Database Insights line. Hard-code or pull from the marketing page until AWS exposes it.

## Multipliers / formula

```
vcpu               = lookup from instanceType (db.m6i.12xlarge → 48)

db_compute_monthly = hourly_for(edition, license, deployment) * 730 * (utilization_pct/100) * Number_of_Nodes
storage_monthly    = per_gb_month_for(storageType, edition, deployment) * storageAmount
backup_monthly     = additionalBackupStorage * backup_per_gb_month            # over free tier
proxy_monthly      = 0.015 * vcpu * 730 * Number_of_Nodes                     # if createRDSProxy == "1"
insights_monthly   = 0.0125 * vcpu * 730 * Number_of_Nodes                    # if DatabaseInsightsSelected == "1"
optimize_monthly   = optimized_io_per_hour * 730 * Number_of_Nodes            # if optimize == "1"; verify rate before charging

serviceCost.monthly = sum
serviceCost.upfront = sum of any RI All/Partial Upfront amounts
```

Multi-AZ doubles compute. BYOL Enterprise Developer is dev/test-only and has the same hourly across all instance sizes as Enterprise BYOL on identical iron — but always verify the SKU; AWS occasionally publishes a separate Enterprise Developer rate.

## configSummary template

```
Storage amount (<N> GB), Nodes (<N>), Instance type (<type>), Utilization (On-Demand only) (<N> %Utilized/Month), Deployment option (<option>), License (<license>), Database edition (<edition>), Unbundled Licensing (<TRUE|FALSE>), Pricing strategy (<term>), Storage for each RDS instance (<volume display>), Additional backup storage (<N> GB)
```

Note the small differences from postgres: `Instance type` (lowercase t), `Deployment option`, `Pricing strategy` (not "Pricing Model"), and the trailing storage/backup pair. The SPA reads this literally — match the casing. `configSummary` is a display label only; it does not affect recompute (the row fields above do).

Captured On-Demand example (`30.json`):

```
Storage amount (200 GB), Nodes (1), Instance type (db.t3.large), Utilization (On-Demand only) (84 Hours/Week), Deployment option (Single-AZ), License (License included), Database edition (Web), Pricing strategy (OnDemand), Storage for each RDS instance (General Purpose SSD (gp2))
```

Captured Reserved + GP3 example (`20.json`) — note the Reserved pricing strategy text and the explicit gp3 IOPS/Throughput tail:

```
Engine (SQL Server Standard), License (License Included), Deployment (Multi-AZ), Instance type (db.m5.4xlarge, 16 vCPU, 64 GiB), Pricing strategy (1yr Standard Reserved No Upfront - 3yr not available for SQL Server LI), Storage (4800 GB GP3), General Purpose SSD (gp3) - IOPS (3000), General Purpose SSD (gp3) - Throughput (125 MiBps)
```

For gp2 the captured display is `General Purpose SSD (gp2)`. Map `storageType` → display:

| storageType value | Display in configSummary |
|---|---|
| General Purpose | General Purpose SSD (gp2) |
| General Purpose-GP3 | General Purpose SSD (gp3) |
| Provisioned IOPS | Provisioned IOPS SSD (io1) |
| Provisioned IOPS-IO2 | Provisioned IOPS SSD (io2) |
| Magnetic | Magnetic |

## Defaults

| Field | Default | Why |
|---|---|---|
| optimize | "0" | Optimized Reads/Writes off |
| storageType | General Purpose | gp2 is the RDS UI default |
| storageAmount | 100 GB | Modest baseline |
| createRDSProxy | "0" | Off |
| DatabaseInsightsSelected | "0" | Standard insights only |
| retentionPeriod | "0" | No backup over free tier |
| additionalBackupStorage | "0" | No backup over free tier |
| Number of Nodes | "1" | Single node |
| Deployment Option | Single-AZ | Cheaper baseline; flag for production |
| utilization | 100% | Full utilization |
| TermType | OnDemand | No commitment; Reserved needs the LeaseContractLength + PurchaseOption siblings (1yr only for SQL Server LI) |
| License Model | License included | Matches RDS UI default; switch to BYOL only if the brief says so or mentions SA / License Mobility |
| Database Edition | Standard | Lowest-cost production edition; do NOT default to Enterprise Developer (dev/test-only) |
| Unbundled Licensing | "FALSE" | Default RDS SKUs |

## Verification

Reproduced the captured `serviceCost.monthly` of **$6232.05** in us-east-2 for `db.m6i.12xlarge` Single-AZ BYOL Enterprise Developer with gp2 100 GB, RDS Proxy on, Database Insights Advanced on, 10 GB extra backup:

| Component | Rate | Qty | Monthly |
|---|---|---|---|
| Instance (db.m6i.12xlarge, BYOL, Enterprise Developer, Single-AZ) | $7.20/hr | 730 hr | $5,256.00 |
| Storage gp2 (Enterprise Developer, Single-AZ) | $0.115/GB-mo | 100 GB | $11.50 |
| RDS Proxy | $0.015/vCPU-hr | 48 vCPU * 730 hr | $525.60 |
| Database Insights Advanced | $0.0125/vCPU-hr | 48 vCPU * 730 hr | $438.00 |
| Additional backup | $0.095/GB-mo | 10 GB | $0.95 |
| **Total** | | | **$6,232.05** |

Captured shape lives in `/tmp/aws_calc_onboard/rds_sqlserver.json` (path was ephemeral; file lost — re-capture needed). End-to-end matches to the cent.

### Live-SPA verified captures (2026-06)

Three fragments captured directly from the calculator.aws SPA confirm the recompute-safe shape (see the verified-shape blocks above). These are the authoritative reference for the row encoding:

| Fragment | Config | Region | Reserved encoding | `serviceCost.monthly` |
|---|---|---|---|---|
| `20.json` | db.m5.4xlarge, Standard, LI, Multi-AZ, 4800 GB gp3, Proxy+Insights on | eu-west-1 | `TermType: Reserved` + `LeaseContractLength: 1yr` + `PurchaseOption: No Upfront` | 7929.36 |
| `105.json` | same as 20.json but Single-AZ | eu-central-1 | (same three fields) | 4278.40 |
| `30.json` | db.t3.large, Web, LI, Single-AZ, 200 GB gp2, On-Demand 84 Hours/Week | eu-west-1 | `TermType: OnDemand` (no Lease/Purchase fields) | 155.34 |

The earlier packed-string encoding (`TermType: "Reserved-1yr-No-Upfront-Standard"`) is unrecognized by the SPA and recomputes Reserved lines to **$0.00**. `version` in all three is `0.0.123`.

Inferred (verify before relying):
- `Unbundled Licensing` value doesn't appear to change monthly cost in standard configs; treat as a label until you capture a non-default estimate.
- `optimize` Optimized Reads/Writes rate is not exercised here.
- Database Insights Advanced rate ($0.0125/vCPU-hr) was reverse-derived from the captured total and matches AWS public pricing; it is NOT directly returned by the Pricing API under a "Database Insights" product family today.

- **Form 0.0.123 → 0.0.134 (2026-09-06).** Diffed against the live form definition (`data/amazonRDSForSQLServer/en_US.json`, version `0.0.134`). Every documented cc key still exists with the same id: `optimize`, `createRDSProxy`, `storageAmount`, `DatabaseInsightsSelected`, `retentionPeriod`, `columnFormIPM`, `storageType`, `gp3Iops` (form default 3000), `gp3Throughput` (form default 125). Renamed: none. Removed: none.
- Fields the live form defines that this module did not carry: `vcpuThread`, `vcpuCores` (both gated on `optimize == "1"`), `provisioningIOPS` (io1), `provisionedIOPSIO2` (io2), `additionalBackupStorage`, plus three display-only blocks (`alertId`, `alertId2`, `ebsThroughputRatioAlert`). They are now documented in a separate "not capture-verified" block above. **Eleven form versions elapsed between the pin and the live file, so these cannot be attributed to 0.0.134 specifically** — some or all may predate 0.0.123 and simply never appeared in a capture. Do not read their presence as "new in this bump".
- Correction from the same read: the `optimize` dropdown's live labels are "Configure the number of vCPUs" / "Default CPU options", i.e. it gates the CPU-core/thread inputs. The prose above describes it as an "Optimized Reads/Writes flag"; that reading is not supported by the form definition. Left the field's documented default (`"0"`) alone — it is still the right thing to send.
- The three captured shapes ($7929.36 / $4278.40 / $155.34) were validated against form 0.0.123 and have **not** been re-run against 0.0.134. The Reserved three-field encoding and the `"undefined"` utilization column are unchanged in the live definition.

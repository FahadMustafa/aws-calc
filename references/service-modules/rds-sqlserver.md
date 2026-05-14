# RDS for SQL Server (`amazonRDSForSQLServer`)

Sibling of `rds-postgres.md`. Same column-form list pattern, but the row carries three extra fields (license model, database edition, unbundled-licensing flag) and the top-level shape adds an `optimize` toggle. There is **no** Extended Support row — SQL Server pricing rolls support into the licensed editions, so `RDSExtendedSupportYear` / `addRDSExtendedSupport` from the PostgreSQL module are intentionally absent.

## Line-item header

```json
{
  "serviceCode":  "amazonRDSForSQLServer",
  "estimateFor":  "rdsForOracle",
  "version":      "0.0.123",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon RDS for SQL server",
  "description":  null
}
```

`estimateFor` is literally `"rdsForOracle"` — the SPA reuses the Oracle form template for SQL Server. Preserve verbatim; do not "fix" it. `serviceName` is captured exactly as `Amazon RDS for SQL server` (lowercase "server").

## calculationComponents (verified shape)

```jsonc
{
  "optimize":                  {"value": "0"},                       // Optimized Reads/Writes flag — "0" off, "1" on
  "createRDSProxy":            {"value": "0"},                       // "0" no, "1" yes
  "DatabaseInsightsSelected":  {"value": "0"},                       // "0" standard, "1" advanced
  "retentionPeriod":           {"value": "0"},                       // backup retention days
  "storageAmount":             {"value": "100", "unit": "gb|NA"},
  "storageType":               {"value": "General Purpose"},         // General Purpose | General Purpose-GP3 | Provisioned IOPS | Provisioned IOPS-IO2 | Magnetic
  "additionalBackupStorage":   {"value": "10",  "unit": "gb|NA"},    // GB over the free tier
  "columnFormIPM": {                                                 // one entry per DB-instance row
    "value": [
      {
        "Number of Nodes":     {"value": "1"},
        "Instance Type":       {"value": "db.m6i.12xlarge"},
        "undefined": {                                               // utilization (the key really is "undefined")
          "value": {
            "unit":       "100",
            "selectedId": "%Utilized/Month"
          }
        },
        "TermType":            {"value": "OnDemand"},                // OnDemand | Reserved-1yr-No-Upfront-Standard | etc.
        "Deployment Option":   {"value": "Single-AZ"},               // Single-AZ | Multi-AZ
        "License Model":       {"value": "Bring your own license"},  // "Bring your own license" | "License included"
        "Database Edition":    {"value": "Enterprise Developer"},    // Enterprise | Enterprise Developer | Standard | Web | Express
        "Unbundled Licensing": {"value": "FALSE"}                    // "TRUE" only when separating Microsoft licensing (License Mobility through SA); usually "FALSE"
      }
    ]
  }
}
```

Shared with `rds-postgres.md`: `createRDSProxy`, `DatabaseInsightsSelected`, `retentionPeriod`, `storageAmount`, `columnFormIPM` row shape (`Number of Nodes`, `Instance Type`, `undefined` utilization, `Deployment Option`, `TermType`). Read that module if any of those need explanation.

SQL-Server-specific:
- `optimize` — top-level boolean string toggling Optimized Reads/Writes; leave `"0"` unless the brief asks for it.
- `License Model` — `"Bring your own license"` keeps the MS licensing off the bill (you supply it under SA / License Mobility). `"License included"` bundles MS licensing into the instance hourly rate (substantially higher).
- `Database Edition` — `Enterprise`, `Enterprise Developer` (BYOL-only dev/test), `Standard`, `Web` (License-included only), `Express` (free).
- `Unbundled Licensing` — almost always `"FALSE"`. `"TRUE"` corresponds to the "Unbundled" SKU group the Pricing API exposes under `unbundledLicensing=TRUE`; it does not appear to change the visible monthly in standard configurations, but record it literally from the brief.
- `storageType` replaces postgres's `storageVolume` (same role, different field name). Accepted display values match the Pricing API `volumeType` strings.
- `additionalBackupStorage` is an explicit top-level GB count rather than a derived field; postgres infers it from `retentionPeriod`.

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

Same filters; Reserved terms come back keyed by `LeaseContractLength`, `PurchaseOption`, `OfferingClass=standard|convertible`.

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

Note the small differences from postgres: `Instance type` (lowercase t), `Deployment option`, `Pricing strategy` (not "Pricing Model"), and the trailing storage/backup pair. The SPA reads this literally — match the casing.

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
| TermType | OnDemand | No commitment |
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

Captured shape lives in `/tmp/aws_calc_onboard/rds_sqlserver.json`. End-to-end matches to the cent.

Inferred (verify before relying):
- `Unbundled Licensing` value doesn't appear to change monthly cost in standard configs; treat as a label until you capture a non-default estimate.
- `optimize` Optimized Reads/Writes rate is not exercised here.
- Database Insights Advanced rate ($0.0125/vCPU-hr) was reverse-derived from the captured total and matches AWS public pricing; it is NOT directly returned by the Pricing API under a "Database Insights" product family today.

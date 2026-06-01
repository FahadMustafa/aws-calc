# RDS for PostgreSQL (`amazonRDSPostgreSQLDB`)

Single-line-item service with one or more DB instance entries inside a column-form list. Covers the DB instance(s), storage, RDS Proxy, Database Insights, backups, and Extended Support add-ons.

## Line-item header

```json
{
  "serviceCode":  "amazonRDSPostgreSQLDB",
  "estimateFor":  "rdsForPostgreSQL",
  "version":      "0.0.110",
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
  "storageVolume":             {"value": "General Purpose"},        // General Purpose | Provisioned IOPS | Aurora
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
        "TermType":           {"value": "OnDemand"}                 // OnDemand | Reserved-1yr-No-Upfront-Standard | etc.
      }
    ]
  }
}
```

The `columnFormIPM.value` is an array — push one entry per distinct (instance type × deployment × term) combination. Use `Number of Nodes` to multiply within a row.

The `"undefined"` key is unfortunate but literal — the SPA's form schema uses it as the column id for utilization. Do not rename.

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

## Notes

- The captured estimate uses `db.m4.2xlarge Multi-AZ` with all add-ons enabled — read it for a working sample shape.
- For other RDS engines (MySQL, MariaDB, Oracle, MS SQL, Aurora variants) the SPA uses a different `serviceCode` per engine. Add a sibling module before pricing those.

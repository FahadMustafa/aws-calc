# AWS Backup (`awsBackup` group)

AWS Backup is a **group** service: the line item has `subServices: [...]` rather than top-level `calculationComponents`. Each backup source (EFS, EBS, S3, RDS, DynamoDB, etc.) is its own sub-service with its own `calculationComponents`, even when the user only configures one source. The unused sub-services should still be present with `annualGrowthOfPrimaryUsage` and `dailyChangeOfPrimaryUsage` set to `"0"` — see the captured body for the exact shape.

## Group-level header

```json
{
  "serviceCode":  "awsBackup",
  "estimateFor":  "awsBackupSelector",
  "version":      "0.0.101",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Backup",
  "description":  null,
  "subServices":  [ ... see below ... ],
  "serviceCost":  { "monthly": <sum of subServices.serviceCost.monthly> },
  "configSummary": "<concatenation of per-subservice phrases — see below>"
}
```

Note: in the captured body the group-level `serviceCost` has only `monthly` (no `upfront`). AWS Backup has no upfront component.

## subService catalog

Every supported source maps to a `(serviceCode, estimateFor, version)` triple. These come straight from the captured `awsBackup.json`; do not invent values for ones not listed.

| Source service | subService.serviceCode | subService.estimateFor | version | Notes |
|---|---|---|---|---|
| EFS | `amazonEfsBackup` | `efsBackup` | `0.0.44` | Warm + Cold tiers |
| VMware | `vMwareBackup` | `vmwareBackup` | `0.0.18` | Warm + Cold tiers |
| Timestream | `timestreamBackup` | `TsBackup` | `0.0.47` | Minimal shape; only growth + change in the capture |
| Storage Gateway | `storageGatewayBackup` | `sgwBackup` | `0.0.8` | Warm-only in capture |
| FSx | `fsxBackup` | `fsxBackup` | `0.0.10` | Warm-only in capture |
| S3 | `s3Backup` | `sssBackup` | `0.0.18` | Includes `Continuous_backups_warm_retention_period` |
| Redshift | `redshiftBackup` | `redshiftBackup` | `0.0.36` | Warm-only in capture |
| RDS | `rdsBackup` | `rdsBackup` | `0.0.11` | Includes continuous backups field |
| EBS | `ebsBackup` | `ebsBackup` | `0.0.31` | Warm + monthly cold in capture |
| DynamoDB | `backupDynamoDb` | `ddbBackup` | `0.0.45` | Warm + Cold tiers |
| Aurora | `auroraBackup` | `AuroraBackup` | `0.0.14` | Includes continuous backups field |
| Neptune | `neptuneBackup` | `neptuneBackup` | `0.0.34` | Warm-only in capture |
| DocumentDB | `docDbBackup` | `docdbBackup` | `0.0.37` | Minimal "no data" shape in capture |
| SAP HANA | `sapHanaBackup` | `saphanaBackup` | `0.0.46` | Warm + Cold tiers with continuous |
| Aurora DSQL | `auroraDsqlBackup` | `ddbBackup` | `0.0.45` | Empty `calculationComponents: {}` in capture; **verify before relying on this** — the `estimateFor` collision with DynamoDB is suspicious but reproduced verbatim from the capture |

## subService shape (verified)

Each entry is a flat object with the same envelope. The richest variant — appearing on EFS, DynamoDB, SAP HANA, EBS — looks like this:

```jsonc
{
  "serviceCode":  "amazonEfsBackup",          // see catalog above
  "estimateFor":  "efsBackup",                // see catalog above
  "version":      "0.0.44",                   // see catalog above
  "region":       "us-east-2",
  "description":  null,
  "calculationComponents": {
    "annualGrowthOfPrimaryUsage": {"value": "1"},          // percent, string. "0" disables sub-service charges
    "dailyChangeOfPrimaryUsage":  {"value": "1"},          // percent, string. "0" disables sub-service charges
    "dataSize":                   {"value": "10", "unit": "gb|NA"},   // primary data backed up (GB)
    "hourlyPlansWarmDays":        {"value": "10", "unit": "day"},     // retention in warm tier per plan
    "dailyPlansWarmDays":         {"value": "10", "unit": "day"},
    "weeklyPlansWarmDays":        {"value": "10", "unit": "week"},
    "monthlyPlansWarmDays":       {"value": "10", "unit": "month"},
    "hourlyPlansColdDays":        {"value": "10", "unit": "day"},     // retention in cold tier per plan (sources that support cold)
    "dailyPlansColdDays":         {"value": "10", "unit": "day"},
    "weeklyPlansColdDays":        {"value": "10", "unit": "week"},
    "monthlyPlansColdDays":       {"value": "1",  "unit": "month"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

Sources that support continuous backups (S3, RDS, Aurora, SAP HANA) include an additional field:

```jsonc
"Continuous_backups_warm_retention_period": {"value": "1", "unit": "day"}
```

The key uses snake_case with a capital `C` exactly as shown — this is the SPA's field name; deviating breaks the SPA recompute.

Sources without cold tier (S3, RDS, Aurora, Neptune, FSx, Storage Gateway in the captured body) **omit** the `*PlansColdDays` keys entirely rather than setting them to `"0"`. Follow the capture: present the keys only when the user actually configures a cold tier for a source that supports it.

To represent "user did not configure this source," include the sub-service with just:

```jsonc
"calculationComponents": {
  "annualGrowthOfPrimaryUsage": {"value": "0"},
  "dailyChangeOfPrimaryUsage":  {"value": "0"}
}
```

…and `serviceCost: {"monthly": 0}`. Timestream and DocumentDB use this shape in the capture. Aurora DSQL has `calculationComponents: {}` (fully empty); **verify before relying on this** — it's reproduced from the capture but no working configured DSQL example has been observed.

## Pricing API filters

Pricing API service code: `AWSBackup`.

### Warm / cold backup storage (per source, per region)

```
--service-code AWSBackup
--filter backup_service=<EFS|EBS|DDB|S3|SAP HANA|VMware|Timestream|Storage Gateway|FSx|FSx-Windows|FSx-Lustre|FSx-OpenZFS|FSx-Windows-MAZ|FSx-OpenZFS-MAZ|Aurora|Aurora DSQL|Neptune|DocumentDB|EKS>
--filter regionCode=<region>
--filter operation=Storage
--filter vaulttype=BackupVault
--filter storagetype=<Warm|Cold>
```

The matching SKU has one OnDemand `GB-month` priceDimension. **Note `storagetype` is the lowercase attribute name** — the uppercase `storageType` attribute exists too but distinguishes restore/data-transfer/search SKUs, not the storage rate. Both names are exposed by the API; pick `storagetype`.

`backup_service` enumerates exactly as: `Aurora DSQL`, `Aurora`, `DDB`, `DocumentDB`, `EBS`, `EFS`, `EKS`, `FSx-Lustre`, `FSx-OpenZFS-MAZ`, `FSx-OpenZFS`, `FSx-Windows-MAZ`, `FSx-Windows`, `FSx`, `Neptune`, `S3`, `SAP HANA`, `Storage Gateway`, `Timestream`, `VMware`. Run `get-attribute-values --service-code AWSBackup --attribute backup_service` if you need to confirm.

### Restores (per source, per region)

```
--service-code AWSBackup
--filter backup_service=<source>
--filter regionCode=<region>
--filter backupaction=Restore
```

Restore SKUs are present for sources where AWS Backup charges per restored GB (e.g., VMware: `$0.02 per GB for restore from warm storage for VMware`). EFS uses a separate `productFamily=AWS Backup Restore Data Size EFS`. The captured saveAs body has **no field for restore volume** in any sub-service's `calculationComponents` — restores are not modeled in the calculator's AWS Backup form; **verify before relying on this** if a user asks for restore costs.

### Cross-region copy (LAGVault data transfer)

```
--service-code AWSBackup
--filter backup_service=<source>
--filter regionCode=<source-region>
--filter toRegionCode=<dest-region>
--filter operation=DataTransfer
```

Returns flat per-GB cross-region copy prices (typically $0.02/GB, $0.01/GB for intra-US peers). The captured body has **no field for cross-region copy volume** in `calculationComponents`; the calculator's AWS Backup form does not appear to expose cross-region copy as a configurable input. **Verify before relying on this** if the user asks for cross-region copy.

### Cross-account copy

The Pricing API does not expose a separate cross-account copy SKU — cross-account copy within the same region is free, cross-region cross-account uses the same LAGVault data-transfer rate above. The calculator form has no cross-account toggle in the captured body.

## Per-source pricing coverage (gotchas)

| Source | Warm rate via API | Cold rate via API | Notes |
|---|---|---|---|
| EFS | yes ($0.05/GB-mo us-east-2) | yes ($0.01/GB-mo) | Clean |
| DDB | yes ($0.10) | yes ($0.03) | Clean |
| S3 | yes | n/a (no cold tier) | Continuous backups field present |
| SAP HANA | yes ($0.06) | yes | Clean |
| Timestream | yes ($0.10) | yes ($0.03) | Clean |
| VMware | yes | yes | Clean |
| EBS | **only LAGVault rate exposed** | not exposed | Standard BackupVault EBS backup is billed as EBS snapshot storage under `AmazonEC2` service code (`productFamily="Storage Snapshot"`). **Verify before relying on this** — fall back to the EBS snapshot price for the warm rate. |
| Aurora | **only LAGVault rate exposed** | not exposed | Same pattern: standard backup rolls into Aurora's own backup storage SKU under `AmazonRDS`. **Verify before relying on this**. |
| Neptune | **only LAGVault rate exposed** | not exposed | Same pattern, under `AmazonNeptune`. **Verify before relying on this**. |
| DocumentDB | **only LAGVault rate exposed** | not exposed | Same pattern, under `AmazonDocDB`. **Verify before relying on this**. |
| Storage Gateway | **only LAGVault rate exposed** | not exposed | Storage Gateway snapshot storage under `AmazonStorageGateway`. **Verify before relying on this**. |
| FSx (and variants) | **no AWS Backup Storage SKU in us-east-2** | **none** | All FSx entries are `DataTransfer` (LAGVault). FSx backup storage is billed under `AmazonFSx`. **Verify before relying on this**. |
| RDS | **no AWSBackup SKUs at all** | **none** | RDS backup storage is billed under `AmazonRDS` (snapshot pricing). **Verify before relying on this**. |
| Redshift | **no AWSBackup SKUs at all** | **none** | Redshift snapshot storage is billed under `AmazonRedshift`. **Verify before relying on this**. |
| Aurora DSQL | partial (Cold + DataTransfer only) | yes ($0.03) | No standard warm BackupVault SKU. **Verify before relying on this**. |
| EKS | n/a (`backupresourcetype=EKS-Namespace` only) | n/a | The calculator's AWS Backup form does not appear to expose EKS; **verify before relying on this** |

For any source flagged "verify before relying on this": surface the gap in the breakdown rather than silently substituting a guess. If the user insists on a number, fall back to the source service's own snapshot/backup storage SKU and call out the substitution explicitly.

## Multipliers / formula

The calculator's AWS Backup form models a retention schedule, not a single GB-month figure. For one source with one plan kind (e.g. daily backups, 7-day warm retention, 0 cold):

```
monthly_backup_count   ≈ 30 / interval_days        # 30 for daily, 4 for weekly, ~720 for hourly, 1 for monthly
average_warm_gb_month  ≈ dataSize * (1 + (annualGrowth/100)/12 * months_in_window/2)
                         * dailyChange/100 * monthly_backup_count
                         * warm_retention_days / 30
average_cold_gb_month  ≈ similar, using cold_retention bracket beyond warm window
monthly_for_source     = average_warm_gb_month * warm_rate_per_gb_month
                       + average_cold_gb_month * cold_rate_per_gb_month
```

The captured body does not expose the exact retention formula the SPA uses — `serviceCost.monthly` is a seed value the SPA recomputes on load from the per-plan retention fields. For the seed, a reasonable approximation is:

```
seed_monthly = dataSize_gb
             * (warm_rate * sum_of_warm_retention_weighted_by_plan_frequency
                + cold_rate * sum_of_cold_retention_weighted_by_plan_frequency)
             * (dailyChange/100)
```

Use a Python helper rather than computing this in tokens — small errors compound across 4 retention buckets (hourly/daily/weekly/monthly) × 2 tiers (warm/cold).

`serviceCost.upfront` is always omitted (not 0) at the sub-service level in the capture. The group-level `serviceCost` is also `{"monthly": ...}` only — no upfront key.

## configSummary template

Match the captured concatenation style: each configured source contributes a comma-separated phrase, and phrases for different sources are separated by a single space (no leading conjunction). Per the capture, the per-source phrase is built from configured fields in this order:

```
Estimated daily change of primary data (%) (<value>), Estimated annual increase in primary data (%) (<value>), Amount of primary data to be backed up (<value> GB), Continuous backups warm retention period (<value> Days), Hourly backups warm retention period (<value> Days), Daily backups warm retention period (<value> Days), Weekly backups warm retention period (<value> Weeks), Monthly backups warm retention period (<value> Months), Hourly backups cold retention period (<value> Days), Daily backups cold retention period (<value> Days), Weekly backups cold retention period (<value> Weeks), Monthly backups cold retention period (<value> Months)
```

Include only the keys actually present in that source's `calculationComponents`. For sources that have nothing configured (growth=0, change=0), include just:

```
Estimated annual increase in primary data (%) (0), Estimated daily change of primary data (%) (0)
```

The capture sometimes orders `daily change` before `annual growth` and sometimes the reverse — the SPA does not appear to be strict about ordering within a source, but be consistent within one estimate.

## Defaults to apply when the user is silent

| Field | Default | Why |
|---|---|---|
| Sub-services not mentioned | growth=0, change=0, no other keys | Match capture — every source must be present in `subServices` |
| `annualGrowthOfPrimaryUsage` | `"0"` (configured: `"1"`) | Calculator default in capture is 1% for configured sources |
| `dailyChangeOfPrimaryUsage` | `"0"` (configured: `"1"`) | Same — 1% baseline |
| `dataSize` | `"1"` GB | Smallest unit — flag in breakdown |
| Warm retention (any plan) | `"1"` Days/Weeks/Months | Calculator's minimum |
| Cold retention | omitted unless source supports cold AND user asked | Don't add cold keys to sources that lack cold tier in capture |
| Continuous backup retention | omitted unless source supports continuous (S3/RDS/Aurora/SAP HANA) | Field name is `Continuous_backups_warm_retention_period` |
| `region` | inherit group region | Sub-services share region |
| `serviceCost.upfront` | omitted | Group has no upfront component |

## Verification

- **Captured HAR / saveAs body**: `/home/fahadmustafa/src/aws-calc/captures/saveAs/per-service/awsBackup.json` — region us-east-2, 16 sub-services, group `serviceCost.monthly: 10.47`. All `serviceCode` / `estimateFor` / `version` triples in the catalog table above come from this file.
- **Round-trip tested**: Not end-to-end. Header values and shape are verbatim from a real captured save, so the SPA load is expected to accept them, but the formula for `serviceCost.monthly` is approximated (the SPA recomputes it from `calculationComponents` on load, so the seed value is informational only).
- **Pricing API verified for**: EFS warm/cold ($0.05 / $0.01 GB-mo us-east-2), DDB warm/cold ($0.10 / $0.03), SAP HANA warm ($0.06), Timestream warm/cold ($0.10 / $0.03), S3 BackupVault (verified present), VMware (restore SKU verified).
- **Marked "verify before relying on this"** (do not invent rates for these without falling back to the source service's own snapshot/backup SKU and flagging it in the breakdown):
  - EBS warm/cold rates (only LAGVault SKU exposed under `AWSBackup`)
  - Aurora, Neptune, DocumentDB, Storage Gateway warm/cold rates (only LAGVault SKU exposed)
  - FSx (all variants) warm/cold rates (no `Storage` operation SKU at all)
  - RDS, Redshift (no `AWSBackup` SKUs at all in us-east-2)
  - Aurora DSQL warm rate (only Cold + DataTransfer SKUs exposed); the capture's empty `calculationComponents: {}` for this sub-service
  - Restore volumes (no `calculationComponents` field present in capture)
  - Cross-region copy volumes (no `calculationComponents` field present in capture)
  - Cross-account copy (no `calculationComponents` field present in capture)
  - EKS as a source (Pricing API has `backupresourcetype=EKS-Namespace` but the calculator form does not expose EKS in the capture)

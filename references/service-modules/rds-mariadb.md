# RDS for MariaDB (`amazonRDSMariaDB`)

Single line item per DB instance (the form holds one `columnFormIPM` row). Covers the instance, storage (gp2/gp3/io1/io2/Magnetic), gp3 IOPS/throughput above baseline, RDS Proxy, Database Insights, Dedicated Log Volume, extra backup storage and snapshot export. The SPA tells you to add each **read replica as its own line item**, so do that.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| On-Demand instance + gp3 storage, Multi-AZ and Single-AZ (`db.r7g.2xlarge`, `db.m7g.large`, `db.t4g.medium`, eu-central-1) | recompute-verified | live SPA 2026-09-24: 33-line reference estimate (customer engagement, ID withheld; shapes in `references/fixtures/`), "Update estimate" reproduced all 5 lines to the cent |
| Same path on x86 types (`db.r7i.2xlarge` Multi-AZ and Single-AZ, `db.m7i.large` Multi-AZ and Single-AZ, `db.t3.medium` Multi-AZ, eu-central-1) | recompute-verified | live SPA 2026-09-24, second 33-line reference estimate (x86 variant, ID withheld): all 5 lines reproduced to the cent. The calculator does not model T3 Unlimited CPU-credit surcharges |
| cc shape (incl. `LeaseContractLength`/`PurchaseOption` present on an On-Demand row) | capture-verified | `references/fixtures/amazonRDSMariaDB.json` (SPA saveAs, db.r7g.2xlarge Multi-AZ 500 GB gp3, $1,837.17) |
| gp3 at baseline (`gp3Iops`/`gp3Throughput` = 12000/500 for >= 400 GB, 3000/125 below) | recompute-verified | same estimate — no IOPS/throughput surcharge on recompute |
| gp3 IOPS / throughput above baseline | inferred | form maths `billableGp3IOPS` / `billableProvisionedThroughput` exist; not exercised |
| Reserved (`TermType: "Reserved"` + `LeaseContractLength` + `PurchaseOption`) | inferred | the three fields are in the On-Demand capture; a Reserved row was never saved or recomputed |
| RDS Proxy, Database Insights, Dedicated Log Volume, `additionalBackupStorage`, `snapshotExport` | inferred | form 0.0.132 fields; captured only in their off state |
| Database Savings Plans pricing model | inferred | form maps `dsp-join-with-rds-mariadb-calc`; not exercised |

## Line-item header

```json
{
  "serviceCode":  "amazonRDSMariaDB",
  "estimateFor":  "rdsForMariaDB",
  "version":      "0.0.132",
  "region":       "<code>",
  "regionName":   "<SPA display, e.g. Europe (Frankfurt)>",
  "serviceName":  "Amazon RDS for MariaDB",
  "description":  null
}
```

`regionName` in 2026 captures is the SPA display string ("Europe (Frankfurt)"), not the Price List location ("EU (Frankfurt)"). Either loads; copy the capture.

## calculationComponents (verified shape)

Verbatim from the SPA saveAs (`fixtures/amazonRDSMariaDB.json`):

```jsonc
{
  "createRDSProxy":           {"value": "0"},                 // "0" no, "1" yes. UI default is YES — set "0" explicitly
  "DatabaseInsightsSelected": {"value": "0"},                 // "0" standard (free), "1" advanced. UI default is YES
  "storageAmount":            {"value": "500", "unit": "gb|NA"},
  "storageVolume":            {"value": "General Purpose-GP3"},   // General Purpose (gp2) | General Purpose-GP3 | Provisioned IOPS (io1) | Provisioned IOPS-IO2 | Magnetic
  "gp3Iops":                  {"value": "12000"},             // only with gp3; set to the RDS baseline to avoid a surcharge (see below)
  "gp3Throughput":            {"value": "500", "unit": "mbps"},
  "columnFormIPM": {"value": [{
      "Number of Nodes":     {"value": "1"},
      "Instance Type":       {"value": "db.r7g.2xlarge"},
      "undefined":           {"value": {"unit": "100", "selectedId": "%Utilized/Month"}},  // literal "undefined" key = utilization
      "Deployment Option":   {"value": "Multi-AZ"},           // Single-AZ | Multi-AZ (others per form dropdown)
      "TermType":            {"value": "OnDemand"},
      "LeaseContractLength": {"value": "1yr"},                // the SPA writes these two even for OnDemand; keep them
      "PurchaseOption":      {"value": "No Upfront"}
  }]}
}
```

No `retentionPeriod`, `additionalBackupStorage` or `snapshotExport` keys appear when left empty; omit them.

### gp3 baseline

The form's gp3 IOPS/throughput defaults are 12000 / 500 MiBps, which is the included baseline for volumes of 400 GB or more. Below 400 GB the RDS baseline is 3000 / 125, so set `gp3Iops: "3000"` and `gp3Throughput: "125"` for small volumes. The 50 GB line in the anchor estimate used 3000/125 and recomputed with no surcharge.

## Pricing API filters

```
--service-code AmazonRDS --filter regionCode=<region> --filter databaseEngine=MariaDB
--filter instanceType=<db.x> --filter deploymentOption=<Single-AZ|Multi-AZ>
```

Storage (note `volumeType`, not `volumeName`; `volumeName` returns zero SKUs with these values):

```
--service-code AmazonRDS --filter regionCode=<region> --filter productFamily="Database Storage"
--filter volumeType=General Purpose-GP3 --filter databaseEngine=MariaDB
```

Two SKUs: `<P>-RDS:GP3-Storage` (Single-AZ) and `<P>-RDS:Multi-AZ-GP3-Storage` (2x). eu-central-1: $0.137 / $0.274 per GB-month. The Reserved terms (1yr/3yr, No/Partial/All Upfront) come back on the instance SKU.

## Multipliers / formula

```
monthly = hourly(instance, deployment) * 730 * (util/100) * nodes
        + storage_rate(deployment) * storageAmount
        + gp3 surcharges above baseline (not exercised)
```

Anchor: db.r7g.2xlarge Multi-AZ eu-central-1 = 2.329 x 730 + 0.274 x 500 = $1,837.17 (SPA capture and recompute agree).

## configSummary template

```
Storage amount (<GB> GB), Nodes (<N>), Instance type (<type>), Utilization (On-Demand only) (100 %Utilized/Month), Deployment selection (<Single-AZ|Multi-AZ>), Pricing strategy (OnDemand 1yr No Upfront), Storage volume (General Purpose SSD (gp3)), General Purpose SSD (gp3) - IOPS (<iops>), General Purpose SSD (gp3) - Throughput (<mbps> MiBps)
```

"OnDemand 1yr No Upfront" is what the SPA writes for an On-Demand row; it is display-only.

## Defaults

| Field | Default | Why |
|---|---|---|
| createRDSProxy | "0" | UI defaults to Yes; nobody asked for a proxy |
| DatabaseInsightsSelected | "0" | UI defaults to Yes (advanced, paid) |
| storageVolume | General Purpose-GP3 | Current default for new RDS volumes |
| gp3Iops / gp3Throughput | baseline for the size | Avoids an unrequested surcharge |
| Deployment Option | Multi-AZ for production, Single-AZ for replicas/non-prod | Flag in the breakdown |
| TermType | OnDemand | Reserved is not recompute-verified here |

## Verification

- Captured 2026-09-24 by driving calculator.aws headlessly (Playwright): region eu-central-1, db.r7g.2xlarge, Multi-AZ, OnDemand, proxy No, gp3 500 GB, Database Insights No. The saveAs POST was intercepted and not persisted. SPA total $1,837.17 = Pricing API math.
- Recompute: a 33-line reference estimate (customer engagement, ID withheld) carries five MariaDB lines (r7g.2xlarge Multi-AZ 500 GB, r7g.2xlarge Single-AZ 500 GB, m7g.large Multi-AZ 600 GB, t4g.medium Multi-AZ 50 GB at 3000/125, m7g.large Single-AZ 500 GB). "Update estimate" in the live SPA reproduced every stored cost to the cent, no incompatibility error.
- Not verified: Reserved rows, gp3 above baseline, proxy/insights/DLV/backup/export add-ons.

# EBS (`amazonElasticBlockStore`) — standalone line item

This is the **dedicated** EBS calculator form (its own line-item card on the
left-hand service picker), distinct from the EBS pricing bundled inside the
`ec2Enhancement` line item. Use this module when the user wants EBS broken out
on its own — e.g. shared volumes, snapshot-heavy archive workloads, or storage
not tied to a specific EC2 fleet. If the user is already building an EC2 line
item with attached storage, prefer the `ec2Enhancement` module.

Notable form quirks vs. the EC2 module's EBS section:

- Has its own snapshot-management fields (`snapshotAmount`,
  `numberOfSnapshotsToRestore`, EBS direct API request counts) that the
  bundled EC2 form does not expose.
- `storageType` uses different display strings than the EC2 module
  (`"Storage General Purpose GB Mo"` instead of
  `"Storage General Purpose gp3 GB Mo"`). The standalone form does not expose
  gp3-only throughput / IOPS surcharges as discrete fields; gp3 throughput and
  IOPS surcharges fall back to defaults.

## Line-item header

```json
{
  "serviceCode":  "amazonElasticBlockStore",
  "estimateFor":  "elasticBlockStore",
  "version":      "0.0.159",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Elastic Block Store (EBS)",
  "description":  null
}
```

`estimateFor`, `version`, and `serviceName` are taken verbatim from the
captured saveAs body. If the SPA bumps the form version, refresh from a new
capture before relying on cached numbers.

## calculationComponents (verified shape)

Copied directly from the capture, then annotated:

```jsonc
{
  // Hours per month the volume is provisioned (730 = always-on).
  // Stored as string; the unit is fixed to "hours".
  "durationOfInstanceRuns": {
    "unit":  "hours",
    "value": "730"
  },

  // EBS direct API request counts per month — only relevant if the workload
  // reads/writes snapshots via the EBS direct APIs (Lambda backup tools,
  // some DR products). Leave at "0" / empty if not used.
  "numberOfDirectAPIListRequests": { "unit": "perMonth", "value": "101" },
  "numberOfDirectAPIPUTRequests":  { "unit": "perMonth", "value": "10"  },
  "numberOfGETAPIRequests":        { "unit": "perMonth", "value": "10"  },

  // Count of EBS volumes, as string.
  "numberOfInstances": { "value": "1" },

  // For Fast Snapshot Restore + restore-cost modeling. Per the form copy
  // "Number of snapshots to restore" — number of restore operations per
  // month, not the FSR-enabled snapshot count. Stored as string.
  "numberOfSnapshotsToRestore": { "value": "10" },

  // Change-rate per snapshot in GB. Snapshots are incremental, so the
  // calculator charges for snapshotAmount × snapshotFrequency rather than
  // full-volume size per snapshot. unit "gb|NA" matches the captured body.
  "snapshotAmount": { "unit": "gb|NA", "value": "3" },

  // Snapshot count per month, stored as a stringified float. The SPA's UI
  // exposes presets ("2x Daily", "Daily", "Weekly", "Monthly") that map to
  // 60, 30, ~4.33, 1; users can also type a raw number. The captured value
  // "59.83" is 2 × 29.915 (calculator's days-per-month constant) — i.e.
  // "2x Daily" expanded. Treat as a number, not an enum string.
  "snapshotFrequency": { "value": "59.83" },

  // Provisioned volume size per volume in GB, stringified. "gb|NA" unit is
  // a calculator-internal token (gb with no quantity-axis qualifier).
  "storageAmount": { "unit": "gb|NA", "value": "30" },

  // Volume type — one of the display strings the SPA's bundle defines.
  // See "storageType values" below for the verified set.
  "storageType": { "value": "Storage General Purpose GB Mo" }
}
```

### storageType values (extracted from the SPA bundle)

| User intent | `storageType.value` | Maps to volumeApiName |
|---|---|---|
| Magnetic (legacy `standard`) | `Storage Magnetic GB Mo` | `standard` |
| General Purpose SSD — legacy / default | `Storage General Purpose GB Mo` | `gp2` (legacy default) |
| General Purpose SSD gp2 | `Storage General Purpose gp2 GB Mo` | `gp2` |
| General Purpose SSD gp3 | `Storage General Purpose gp3 GB Mo` | `gp3` |
| Provisioned IOPS — legacy | `Storage Provisioned IOPS GB Mo` | `io1` (legacy default) |
| Provisioned IOPS io1 | `Storage Provisioned IOPS io1 GB Mo` | `io1` |
| Throughput Optimized HDD | `Storage Throughput Optimized HDD GB Mo` | `st1` |
| Cold HDD | `Storage Cold HDD GB Mo` | `sc1` |

The standalone EBS form does **not** appear to expose `io2`, `io2 Block
Express`, or gp3 throughput/IOPS surcharges as dedicated fields — the bundle
contains no matching display strings. If the user asks for io2 explicitly,
prefer the `ec2Enhancement` line item or surface this gap. Mark this:
**verify before relying on this** for io2 / io2 Block Express requests.

## Pricing API filters

Run every call through `scripts/pricing_client.py --profile <profile>
get-products`. EBS lives under `AmazonEC2`.

### Volume storage (`$/GB-month`)

```
--service-code AmazonEC2
--filter productFamily=Storage
--filter regionCode=<region>
--filter volumeApiName=<gp2|gp3|io1|io2|st1|sc1|standard>
```

Returns one SKU with a single OnDemand `GB-Mo` priceDimension. Multiply by
`storageAmount` × `numberOfInstances`.

### Snapshot storage (`$/GB-month`)

```
--service-code AmazonEC2
--filter productFamily="Storage Snapshot"
--filter regionCode=<region>
```

Returns multiple SKUs differentiated by `usagetype`. The standard incremental
snapshot rate is the SKU whose `usagetype` ends in `:SnapshotUsage`
(e.g. `USE2-EBS:SnapshotUsage` for us-east-2). The archive-tier rate is the
SKU whose `usagetype` ends in `:SnapshotArchiveStorage`; snapshot-archive
retrieval is `:SnapshotArchiveRetrieval` (priced per GB retrieved, not per
GB-month). The standalone form does not surface archive-tier separately, so
default to the `SnapshotUsage` rate unless the user explicitly asks for
archive — **verify before relying on this** for archive-tier modeling.

### EBS direct API requests

```
--service-code AmazonEC2
--filter productFamily="EBS direct API Requests"
--filter regionCode=<region>
```

Returns three SKUs keyed by `usagetype`:

| Field | Match `usagetype` ending | Unit |
|---|---|---|
| `numberOfDirectAPIPUTRequests` | `directAPI.snapshot.Put`  | per 1000 SnapshotAPIUnits |
| `numberOfGETAPIRequests`       | `directAPI.snapshot.Get`  | per 1000 SnapshotAPIUnits |
| `numberOfDirectAPIListRequests`| `directAPI.snapshot.List` | per 1000 Requests |

**Mind the unit.** These SKUs are priced **per 1000** requests/SnapshotAPIUnits
(see the `unit` column and the SKU's `unit` field). Compute
`(request_count / 1000) * price_per_unit` — do **not** multiply the raw count by
`price_per_unit`, or you over-charge by 1000×. (Impact is usually tiny because
request volumes are small, but get it right.)

### Fast Snapshot Restore (optional, surfaced via `numberOfSnapshotsToRestore` / DSU-hours)

```
--service-code AmazonEC2
--filter productFamily="Fast Snapshot Restore"
--filter regionCode=<region>
```

Returns one SKU billed per DSU-hour. The standalone EBS form does not expose
FSR hours as a distinct field — it only collects "Number of snapshots to
restore". The SPA's exact derivation from that count to DSU-hours is opaque
in the bundle; **verify before relying on this** if you need a precise FSR
charge. Treat `numberOfSnapshotsToRestore` as a count of restore operations
the user wants to model.

### Snapshot data transfer (cross-region copy)

```
--service-code AmazonEC2
--filter productFamily="System Operation"
--filter regionCode=<source-region>
```

Returns the `TimeBasedSnapshotCopy.tier{1,2,3}` SKUs ($0.020 / $0.018 / $0.016
per GB in us-east-2 for ≤15 min / 30–59 min / 60–119 min completion). The
standalone EBS form does not collect a "cross-region snapshot copy GB" field,
so cross-region copy is **not modeled** by this line item out of the box.
**Verify before relying on this** — if the user wants snapshot-copy costs,
either add a separate Data Transfer line item or note that the EBS line item
under-counts.

## Multipliers / formula

```
monthly_storage   = storage_per_gb_mo
                    * storageAmount
                    * numberOfInstances
                    * (durationOfInstanceRuns / 730)   # prorate part-month volumes

monthly_snapshot  = snap_per_gb_mo
                    * snapshotAmount
                    * snapshotFrequency                # incremental, per-snapshot delta

monthly_api       = put_rate  * numberOfDirectAPIPUTRequests
                  + get_rate  * numberOfGETAPIRequests
                  + list_rate * numberOfDirectAPIListRequests

monthly_fsr       = 0   # NOT MODELED — see the hard warning below

serviceCost.monthly = monthly_storage + monthly_snapshot + monthly_api + monthly_fsr
serviceCost.upfront = 0   # EBS is on-demand only
```

> **Do NOT ship a standalone EBS estimate when `numberOfSnapshotsToRestore > 0` (or FSR is involved) without modeling restore.** `monthly_fsr = 0` means this formula returns near-zero for restore-heavy workloads while the real cost is orders of magnitude higher. The capture proves it: 30 GB / 3 GB delta / 2× Daily / 10 restores has `serviceCost.monthly = $5,484.14`, but storage + incremental snapshot + direct-API alone is only ~$5. Restore/FSR is the entire bill. Until the DSU-hour/restore derivation is reverse-engineered, either (a) source the restore charge from a HAR and add it, or (b) **refuse the standalone EBS line** and tell the user it can't be priced accurately with restores — do not hand off the ~$5 number as if it were the cost. This also trips the `serviceCost > 0` sanity check only weakly (the line is non-zero but wildly low), so it must be caught here, not by that backstop.

Notes:

- The SPA's actual snapshot math is more nuanced than `snap_per_gb_mo *
  snapshotAmount * snapshotFrequency`. The storage + incremental snapshot +
  EBS direct-API portion of the formula is calculator-canonical; the FSR/restore
  portion is the gap (above).
- `durationOfInstanceRuns` defaults to 730 (full month). Lower values
  prorate. Stored as string.
- All numeric values in `calculationComponents` are stored as **strings**, not
  numbers — the SPA parses them on load.

## configSummary template

Match the captured phrasing — the SPA renders this as the line-item card
subtitle, and deviation produces odd display:

```
Number of volumes (<N>), Average duration of volume (<D> hours per month), Storage amount per volume (<S> GB), Snapshot Frequency (<freq label>), Amount changed per snapshot (<C> GB), Number of snapshots to restore (<R>)
```

`<freq label>` follows the SPA's preset names: `2x Daily`, `Daily`, `Weekly`,
`Monthly`. If the user supplies a raw `snapshotFrequency` number, pick the
closest preset for display and store the numeric value in
`calculationComponents.snapshotFrequency.value`.

## Defaults to apply when the user is silent

| Field | Default | Why |
|---|---|---|
| `numberOfInstances` | `"1"` | One volume |
| `durationOfInstanceRuns` | `"730"` | Always-on full month |
| `storageAmount` | `"100"` | Reasonable modest default; flag in breakdown |
| `storageType` | `"Storage General Purpose gp3 GB Mo"` | gp3 is the AWS-recommended default for new SSD volumes |
| `snapshotFrequency` | `"0"` | Disabled (no snapshot cost) until user asks for backups |
| `snapshotAmount` | `"0"` | No snapshot delta when frequency is 0 |
| `numberOfSnapshotsToRestore` | `"0"` | No restore charges by default |
| `numberOfDirectAPIPUTRequests` | `"0"` | Direct APIs off by default |
| `numberOfGETAPIRequests` | `"0"` | Direct APIs off by default |
| `numberOfDirectAPIListRequests` | `"0"` | Direct APIs off by default |

When applying any default that affects price (storageType / storageAmount /
snapshotFrequency), list it in the breakdown so the user can correct.

## Verification

- **Ground truth**: `/home/fahadmustafa/src/aws-calc/captures/saveAs/per-service/amazonElasticBlockStore.json`
  — captured saveAs POST body from the calculator.aws SPA.
- **Verified end-to-end**:
  - Top-level shape (`serviceCode`, `estimateFor`, `version`, `serviceName`,
    `regionName`) — copied verbatim from the capture.
  - `calculationComponents` field set, key names, unit strings, and the
    string-typed numeric values — copied verbatim.
  - Pricing-API filter combinations for volume storage, snapshot storage,
    and EBS direct API requests — confirmed against
    `pricing_client.py get-products` in us-east-2.
- **Inferred / unverified — verify before relying on this**:
  - The `storageType` → `volumeApiName` mapping table is reconstructed from
    bundle.js display strings; only `Storage General Purpose GB Mo` is
    present in the capture. The legacy unmarked variants (`Storage General
    Purpose GB Mo`, `Storage Provisioned IOPS GB Mo`) probably map to gp2 /
    io1 respectively per AWS's documented form evolution, but this is not
    confirmed by a fresh capture for each.
  - **io2, io2 Block Express, gp3 IOPS surcharge, gp3 throughput surcharge**
    have no matching display strings in the bundle for the standalone form —
    they appear to be unsupported here. If the user needs them, route to
    `ec2Enhancement` or capture a fresh HAR to validate.
  - **Snapshot archive tier** — present in Pricing API but no dedicated
    field in the captured `calculationComponents`. Out of scope for this
    line item until a capture shows otherwise.
  - **Fast Snapshot Restore** — `numberOfSnapshotsToRestore` is captured but
    the SPA's derivation from that count to a DSU-hour charge is not visible
    in the bundle scrape. The formula above sets `monthly_fsr = 0`; the
    captured estimate's $5484.14 serviceCost suggests the SPA computes more
    than the formula does. Treat absolute serviceCost as approximate when
    FSR or restore counts are non-zero.
  - **Cross-region snapshot copy** — Pricing API SKUs exist
    (`System Operation` → `TimeBasedSnapshotCopy.tier*`) but the standalone
    form does not expose a GB field for it. Model cross-region copy as a
    separate data-transfer line item.
- **Tested config**: filters verified against `us-east-2`. Other regions use
  the same filter shape with the matching `regionCode`.

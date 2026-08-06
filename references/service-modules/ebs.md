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

> **Two distinct line shapes — pick the right one.** This form is used for two
> very different intents, and the recompute-safe `calculationComponents` shape
> is **not** the same for both:
>
> - **gp3 (or other) volume line** — provisioned block storage. Uses a gp3
>   `storageType` and a real `storageAmount`, with snapshot fields zeroed. See
>   the gp3 volume documentation below; this shape recomputes correctly.
> - **EBS snapshot-storage line** — incremental snapshot storage cost only.
>   Uses the **gp2** `storageType` string, a *minimal* `storageAmount`, and the
>   `snapshotFrequency` / `snapshotAmount` pair. See **"EBS Snapshots
>   (recompute-safe shape)"** below. A snapshot line built with a gp3
>   `storageType` recomputes to **$0.00** on "Update estimate" — see the
>   recompute-fix note.

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

## EBS Snapshots (recompute-safe shape)

> **Recompute fix (2026-06, live-SPA verified).** Earlier versions of this
> module represented snapshot-storage lines with a gp3 `storageType`
> (`"Storage General Purpose gp3 GB Mo"`), the EBS direct-API request fields
> (`numberOfDirectAPIListRequests`, `numberOfGETAPIRequests`,
> `numberOfDirectAPIPUTRequests`), `numberOfSnapshotsToRestore`, and
> `storageAmount: "0"`. **That shape recomputes to `$0.00`** when the user hits
> "Update estimate" in the SPA: the gp3 storageType has **no snapshot-pricing
> path**, and with `storageAmount` 0 there is nothing for the gp3 volume path
> to charge either. The corrected shape below was captured from the **live AWS
> Pricing Calculator SPA** and is verified recompute-safe.

EBS *snapshot storage* is **not** modeled by setting a gp3 volume to size 0 and
filling in snapshot deltas. The SPA computes snapshot cost through the **gp2**
storage path plus the `snapshotFrequency` / `snapshotAmount` pair. The
recompute-safe shape is:

```jsonc
{
  // One "volume" — the snapshot line still rides on a volume row.
  "numberOfInstances": { "value": "1" },

  // Always-on full month.
  "durationOfInstanceRuns": { "unit": "hours", "value": "730" },

  // MUST be the gp2 string. The gp3 string has no snapshot-pricing path and
  // recomputes the whole line to $0.00.
  "storageType": { "value": "Storage General Purpose GB Mo" },

  // Minimal volume — the SPA requires a volume but the snapshot cost does not
  // come from it. Use the 1 GB minimum. (Its gp2 GB-mo cost is negligible and
  // is part of the captured serviceCost; see worked example.)
  "storageAmount": { "unit": "gb|NA", "value": "1" },

  // "1" == Monthly. This is what triggers the snapshot-storage term. See the
  // 50%-discount quirk below — frequency "1" applies a hardcoded partial-month
  // discount to the snapshot term.
  "snapshotFrequency": { "value": "1" },

  // The changed-GB-per-snapshot input. To hit a target of G GB of snapshot
  // storage at the regional snapshot rate, set this to ~2×G (see back-solve).
  "snapshotAmount": { "unit": "gb|NA", "value": "<~2×target-GB>" }
}
```

Note what is **absent** vs. the volume/blended shape: there are **no**
`numberOfDirectAPIListRequests`, `numberOfGETAPIRequests`,
`numberOfDirectAPIPUTRequests`, or `numberOfSnapshotsToRestore` keys. Do not
add them to a snapshot line — they are the stale fields from the broken shape.

### The 50% partial-storage-month discount (quirk)

With `snapshotFrequency: "1"` (Monthly) the SPA applies a **hardcoded 50%
partial-storage-month discount** to the incremental snapshot term. The snapshot
term is therefore:

```
monthly_snapshot = snap_per_gb_mo * snapshotAmount * 0.5
```

There is **no frequency value that yields the full, undiscounted
`GB × rate`** for the snapshot term — the discount is baked into the Monthly
path used by the recompute-safe shape. This is why the captured `snapshotAmount`
values are roughly **double** the GB of snapshot storage actually being
represented.

### Back-solving `snapshotAmount` to hit a target snapshot-storage cost

Given a target of `G` GB of snapshot storage at regional snapshot rate
`snap_per_gb_mo` (the `:SnapshotUsage` SKU, typically $0.05/GB-mo in
eu-west-1, ~$0.054/GB-mo in eu-central-1):

```
target_cost   = G * snap_per_gb_mo          # what G GB "should" cost
snapshotAmount = target_cost / (snap_per_gb_mo * 0.5)
              = 2 * G                        # because the 0.5 discount halves the term
```

So **`snapshotAmount ≈ 2 × G`**. Equivalently, to land a specific dollar target
directly: `snapshotAmount = target_cost / (snap_per_gb_mo * 0.5)`.

The captured `serviceCost.monthly` also includes the negligible 1 GB gp2
volume term, so verify the total against `snap_per_gb_mo * snapshotAmount * 0.5
+ gp2_per_gb_mo * 1`.

### Worked example (from captures idx51 / idx88)

**idx51 — eu-west-1, snapshot rate $0.05/GB-mo**, representing **9,044 GB** of
snapshot storage:

```
snapshotAmount = 2 × 9044 = 18083 (capture used 18083.0)
monthly_snapshot = 0.05 × 18083 × 0.5 = $452.075
captured serviceCost.monthly = $452.24   # ≈ above + ~1 GB gp2 volume term
```

**idx88 — eu-central-1, snapshot rate ~$0.054/GB-mo**, representing
**12,239 GB-equivalent** of snapshot storage (DRS staging snapshots, 3-day
retention):

```
snapshotAmount = 24471.73   # ≈ 2 × 12239 (capture used 24471.73)
monthly_snapshot = 0.054 × 24471.73 × 0.5 ≈ $660.7
captured serviceCost.monthly = $660.91
```

Both captures use `storageType: "Storage General Purpose GB Mo"` (gp2),
`storageAmount: "1"`, `snapshotFrequency: "1"`, and carry **none** of the
direct-API / restore fields. The gp3 *volume* capture (idx87) keeps its gp3
`storageType` with a real `storageAmount` (10 TB) and snapshot fields zeroed —
that line always recomputed fine and is documented separately below; do not
conflate the two.

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
(e.g. `USE2-EBS:SnapshotUsage` for us-east-2). This is the
`snap_per_gb_mo` used by the recompute-safe snapshot shape and back-solve
above (~$0.05/GB-mo eu-west-1, ~$0.054/GB-mo eu-central-1). The archive-tier rate is the
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
                    * 0.5                              # snapshotFrequency "1" (Monthly):
                                                       # SPA applies a hardcoded 50% partial-
                                                       # storage-month discount. See
                                                       # "EBS Snapshots (recompute-safe shape)".

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

- **Ground truth**: `captures/saveAs/per-service/amazonElasticBlockStore.json`
  — captured saveAs POST body from the calculator.aws SPA.
- **Snapshot-shape ground truth (live-SPA, recompute-safe)** — the `/tmp/rbm_frags/*.json` paths below were ephemeral (path was ephemeral; file lost — re-capture needed):
  - `/tmp/rbm_frags/51.json` — eu-west-1 EBS snapshot storage,
    `snapshotAmount` 18083, `serviceCost.monthly` $452.24.
  - `/tmp/rbm_frags/88.json` — eu-central-1 DRS staging snapshots,
    `snapshotAmount` 24471.73, `serviceCost.monthly` $660.91.
  - `/tmp/rbm_frags/87.json` — eu-central-1 gp3 *volume* line (10 TB,
    $2718.72); always recomputed fine. Confirms only the *snapshot*
    representation was broken, not the gp3 volume one.
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
  - **Snapshot storage** — IS modeled by this line item, but **not** via a
    gp3 volume. Use the recompute-safe shape in
    "EBS Snapshots (recompute-safe shape)" above: gp2 `storageType`, 1 GB
    `storageAmount`, `snapshotFrequency: "1"`, and `snapshotAmount ≈ 2×target-GB`
    (the SPA applies a hardcoded 50% partial-month discount). Verified against
    live-SPA captures idx51 (eu-west-1, $452.24) and idx88 (eu-central-1,
    $660.91). The previously documented shape (gp3 `storageType` +
    direct-API/restore fields + `storageAmount: 0`) recomputed to **$0.00** and
    is wrong — see the 2026-06 recompute-fix note.
  - **Snapshot archive tier** — present in Pricing API
    (`:SnapshotArchiveStorage`) but no dedicated field in the captured
    `calculationComponents`. The standalone form models warm/incremental
    snapshot storage only (via the shape above), not the archive tier. Out of
    scope for this line item until a capture shows otherwise.
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

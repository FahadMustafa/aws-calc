# DynamoDB (`amazonDynamoDb`)

Covers Amazon DynamoDB end-to-end. Unlike EC2 or Kinesis, the calculator models DynamoDB as a **group** line item: the parent envelope (`serviceCode: amazonDynamoDb`) holds `serviceCost` and `configSummary`, and the actual configuration lives in an array of `subServices[]`. Each `subService` is its own form bundle with its own `serviceCode`, `estimateFor`, `version`, and `calculationComponents`. Include only the sub-services the user actually configured — the calculator omits the rest entirely (not as empty objects).

## Line-item header (parent envelope)

```json
{
  "serviceCode":  "amazonDynamoDb",
  "estimateFor":  "simpleStorageServiceClassesGroup",
  "version":      "0.0.65",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon DynamoDB",
  "description":  null
}
```

`serviceCost.monthly` / `serviceCost.upfront` on the parent are the **sum** of all `subServices[*].serviceCost`. `configSummary` on the parent is a single string formed by concatenating the per-sub-service summaries with `" "` separators in the order they appear in `subServices[]` (see configSummary template).

The `estimateFor` value on the parent is literally `"simpleStorageServiceClassesGroup"` — this is a calculator-internal form id reused by group services, not a typo. Verified from the capture.

## subServices catalogue

| `subService.serviceCode` | `subService.estimateFor` | `version` | What it bills |
|---|---|---|---|
| `dynamoDbOnDemand` | `dynamoDBOnDemand` | `0.0.132` | On-demand (PayPerRequest) read/write request units + storage |
| `amazonDynamoDbProvisionedThroughputCapacity` | `dynamoDBProvisioned` | `0.0.192` | Provisioned RCU/WCU (incl. reserved capacity 1yr) + storage |
| `amazonDynamoDbDaxClusters` | `dynamoDBDaxNodes` | `0.0.82` | DAX cluster node-hours |
| `amazonDynamoDbStreams` | `dynamoDBOnDemandStreams` | `0.0.84` | DynamoDB Streams GetRecords requests |
| `dynamoDbBackup` | `dynamoDBOnBackup` | `0.0.74` | On-demand backup storage + PITR storage + restore size |
| `dynamoDbChangeDateCapture` | `dynamoDBChangeDataCapture` | `0.0.16` | Change data capture units (Kinesis Data Streams output) — typo `Date` in `serviceCode` is intentional, matches capture |
| `dynamoDbDataExportToAmazonS3` | `dynamoDBDataExportS3` | `0.0.26` | Full + incremental export to S3 |
| `dynamoDbDataImportFromAmazonS3` | `dynamoDBDataImportS3` | `0.0.13` | Import from S3 by source bytes |

Both **on-demand** and **provisioned** can co-exist as separate sub-services in the same line item — the captured body has both. The calculator does not enforce mutual exclusion; whichever the user describes, emit that sub-service.

## calculationComponents (verified shape)

### `dynamoDbOnDemand` — on-demand capacity + storage

```jsonc
{
  "selectTableClass":               {"value": "standard"},                     // "standard" | "standardInfrequentAccess"
  "averageItemSizeForAllAttributes":{"value": "1",  "unit": "kb|NA"},          // average item size, KB
  "dataStorageSize":                {"value": "10", "unit": "gb|NA"},          // baseline table size in GB
  "writeRateId":                    {"value": "10", "unit": "millionPerMonth"},// total writes per month (millions)
  "readRateId":                     {"value": "10", "unit": "millionPerMonth"},// total reads per month (millions)
  "standardWritesId":               {"value": "100"},                           // % of writes that are standard
  "transactionalWritesId":          {"value": "0"},                             // % of writes that are transactional
  "eventuallyConsistentId":         {"value": "100"},                           // % of reads that are eventually consistent
  "stronglyConsistentId":           {"value": "0"},                             // % of reads that are strongly consistent
  "transactionalId":                {"value": "0"}                              // % of reads that are transactional
}
```

The three write split fields must sum to 100; the three read split fields must sum to 100. The calculator validates this on load — emit it correctly or the line item displays blank.

### `amazonDynamoDbProvisionedThroughputCapacity` — provisioned capacity + storage

```jsonc
{
  "selectTableClassProvisioned":           {"value": "standard"},                  // "standard" | "standardInfrequentAccess"
  "averageItemSizeForAllAttributesProvisioned": {"value": "1",  "unit": "kb|NA"},
  "provisionedDataStorageSize":            {"value": "10", "unit": "gb|NA"},

  "baselineWriteRateId":                   {"value": "100", "unit": "perSecond"},  // sustained writes per second
  "peakWriteRateId":                       {"value": "400", "unit": "perSecond"},
  "durationPeakWriteId":                   {"value": "72",  "unit": "hoursPerMonth"},
  "baselineReadRateId":                    {"value": "100", "unit": "perSecond"},
  "peakReadRateId":                        {"value": "400", "unit": "perSecond"},
  "durationPeakReadId":                    {"value": "72",  "unit": "hoursPerMonth"},

  "standardWritesId":                      {"value": "100"},                       // write mix %
  "transactionalWriteId":                  {"value": "0"},                         // note singular "Write" here vs plural in on-demand block
  "eventuallyConsistentId":                {"value": "100"},                       // read mix %
  "stronglyConsistentId":                  {"value": "0"},
  "transactionalId":                       {"value": "0"},

  "percentWriteReservedCapacity":          {"value": "100"},                       // 0..100 — share of WCU on reserved capacity
  "reservedCapacityTermWrite":             {"value": "1yr"},                       // "1yr" only — see verification
  "percentReservedCapacity":               {"value": "100"},                       // share of RCU on reserved
  "reservedCapacityTermRead":              {"value": "1yr"}
}
```

Field-name traps the SPA is strict about and that diverge from on-demand:
- `selectTableClassProvisioned` (not `selectTableClass`)
- `averageItemSizeForAllAttributesProvisioned` (not `…ForAllAttributes`)
- `provisionedDataStorageSize` (not `dataStorageSize`)
- `transactionalWriteId` — singular `Write`, matches the capture exactly. The read-side stays `transactionalId`.

### `amazonDynamoDbDaxClusters` — DAX nodes

```jsonc
{
  "columnFormIPM": {
    "value": [
      {
        "Instance Type":   {"value": "r5.large"},   // DAX node type, no "dax." prefix
        "Number of nodes": {"value": "3"}
      }
      // repeat the object to mix node types in one cluster
    ]
  }
}
```

`columnFormIPM` is an array; each entry is one node-type group. Whitespace-bearing keys (`"Instance Type"`, `"Number of nodes"`) are literal — verified from capture.

### `amazonDynamoDbStreams` — Streams reads

```jsonc
{
  "streamReadRequests": {"value": "10", "unit": "perMonth"}   // GetRecords API requests (raw count, not millions)
}
```

### `dynamoDbBackup` — backup + PITR + restore

```jsonc
{
  "onDemandDataStorage":   {"value": "10", "unit": "gb|NA"},  // on-demand backup retained, GB-months
  "continuousDataStorage": {"value": "10", "unit": "gb|NA"},  // PITR continuous backup size, GB-months
  "restoreSize":           {"value": "10", "unit": "gb|NA"}   // total restored data this month, GB
}
```

### `dynamoDbChangeDateCapture` — CDC for Kinesis Data Streams output

```jsonc
{
  "KDS_writesCaptured": {"value": "10", "unit": "perMonth"},   // total captured writes per month (raw count)
  "KDS_AvgDataSize":    {"value": "10", "unit": "kb|NA"}       // average pre-Kinesis write size, KB
}
```

Note the underscore-prefixed `KDS_` keys, literal from the capture. The `serviceCode` is `dynamoDbChangeDateCapture` (typo `Date` not `Data`) — keep it.

### `dynamoDbDataExportToAmazonS3` — full + incremental export

```jsonc
{
  "exportS3_tableSize":            {"value": "10", "unit": "gb|NA"},  // full export GB per month
  "IncrementexportS3_tableSize":   {"value": "10", "unit": "gb|NA"}   // incremental export GB per month; literal "Increment" prefix, no "al"
}
```

### `dynamoDbDataImportFromAmazonS3` — import from S3

```jsonc
{
  "importS3_tableSize": {"value": "10", "unit": "gb|NA"}   // uncompressed source file size in GB
}
```

## Pricing API filters

All DynamoDB rates live under `--service-code AmazonDynamoDB` except DAX, which is `AmazonDAX`. The `group` and `volumeType` attributes partition SKUs cleanly.

### On-demand request units (per million)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter operation=PayPerRequestThroughput
--filter group=DDB-ReadUnits          # or DDB-WriteUnits / DDB-ReadUnitsIA / DDB-WriteUnitsIA / DDB-ReplicatedWriteUnits / DDB-ReplicatedWriteUnitsIA
```

Returns one OnDemand SKU per group with a single priceDimension. Verified rates in us-east-2:
- Standard: `$0.125 per million read RU` (raw `1.25e-07`), `$0.625 per million write RU` (raw `6.25e-07`), `$0.625 per million replicated write RU`.
- IA table class: `$0.155 per million IA read RU`, `$0.78 per million IA replicated write RU`. (The IA write RU rate has the same group structure — query with `group=DDB-WriteUnitsIA`.)

Transactional reads bill at 2× standard read RU; transactional writes at 2× standard write RU (the multiplier is applied by the calculator from the `transactionalId` / `transactionalWritesId` percent splits — not a separate SKU).

### Provisioned capacity (RCU / WCU hour)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter operation=CommittedThroughput
--filter group=DDB-ReadUnits           # or DDB-WriteUnits, plus -IA variants and DDB-ReplicatedWriteUnits for Global Tables
```

Each SKU returns:
- One `OnDemand` priceDimension in `ReadCapacityUnit-Hrs` / `WriteCapacityUnit-Hrs` (the rate billed for un-reserved capacity, after free-tier band). Verified us-east-2: `$0.00013 per RCU-hr`, `$0.00065 per WCU-hr`, `$0.00065 per replicated WCU-hr`. Each has a `[0, 18600]` free-tier band at `$0`.
- For RCU and WCU groups, additional `Reserved` priceDimensions keyed by `LeaseContractLength=1yr`, `PurchaseOption=Heavy Utilization`, `OfferingClass=standard`:
    - One in `ReadCapacityUnit-Hrs` / `WriteCapacityUnit-Hrs` — recurring rate (multiply by 730). Verified us-east-2: `$0.000025/RCU-hr`, `$0.000128/WCU-hr`.
    - One in `Quantity` — upfront fee per reserved unit. Verified us-east-2: `$0.30/RCU upfront`, `$1.50/WCU upfront`.

**3-year reserved capacity is not currently published by the Price List API** for DynamoDB (`--filter LeaseContractLength=3yr` returns zero SKUs in us-east-2 as of 2026-05). The calculator UI does not actually expose a 3yr reserved-capacity option for DynamoDB either — `reservedCapacityTermRead` / `reservedCapacityTermWrite` only accept `"1yr"`. If a user asks for 3yr DDB reserved capacity, default to `"1yr"` and flag it.

### Storage (per GB-month)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter productFamily="Database Storage"
```

Two SKUs returned:
- `volumeType=Amazon DynamoDB - Indexed DataStore` → Standard table class. The Price List API exposes a tiered SKU (`[0, 25]` GB-Mo @ `$0`, `[25, Inf]` GB-Mo @ `$0.25` in us-east-2), **but the calculator does NOT apply the 25 GB free tier** — it bills storage flat at `$0.25/GB-Mo` from the first GB.
- `volumeType=Amazon DynamoDB - Indexed DataStore - IA` → Standard-IA table class. Flat `$0.10/GB-Mo` in us-east-2.

> **Do not subtract the 25 GB free tier from DynamoDB storage.** Verified against two captures: the on-demand line bills `10 GB × $0.25 = $2.50` (not `max(0, 10-25)×$0.25 = $0`). Applying the free-tier band under-states every table < 25 GB by up to $6.25/mo per sub-service and makes the totals fail to reconcile with the SPA. Use the flat per-GB rate in `storage_monthly()`; keep the `[0,25]@$0` band only as an API note, never in the cost path.

Storage is charged once per table — not duplicated across the `dynamoDbOnDemand` / `amazonDynamoDbProvisionedThroughputCapacity` sub-services even when both are present in the body. Whichever sub-service the user is sizing carries the storage field; if both are present, the storage value should match across them in the capture (both `"10"` GB in the reference body).

### On-demand backup storage (per GB-month)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter productFamily="Amazon DynamoDB On-Demand Backup Storage"
```

Single SKU, single dimension. Verified us-east-2: `$0.10/GB-Mo`.

### PITR storage (per GB-month)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter volumeType="Amazon DynamoDB - Point-In-Time-Restore (PITR) Backup Storage"
```

Verified us-east-2: `$0.20/GB-Mo`.

### Restore size (per GB)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter volumeType="Amazon DynamoDB - Backup Restore Size"
```

One-off per-GB charge for each restore operation. Verify per region.

### Streams GetRecords requests

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter group=DDB-StreamsReadRequests
```

Single SKU with a tiered priceDimension: `[0, 2_500_000]` @ `$0` (free tier), `[2_500_000, Inf]` @ `$2e-07 per request` in us-east-2. The `streamReadRequests` field is raw request count — multiply directly.

### Change data capture units (DDB → Kinesis Data Streams)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter group=DDB-Kinesis
```

Verified us-east-2: `$0.10 per million change data capture units` (raw `1e-07` per unit). A CDC unit covers up to 1 KB of write; `ceil(KDS_AvgDataSize / 1)` units per captured write. `KDS_writesCaptured` is raw count, not millions.

### Export to S3 (per GB)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter volumeType="Amazon DynamoDB - Export Size"               # full export
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter volumeType="Amazon DynamoDB - Incremental Export"        # incremental
```

Verified us-east-2: `$0.10/GB` full, `$0.10/GB` incremental.

### Import from S3 (per GB)

```
--service-code AmazonDynamoDB
--filter regionCode=<region>
--filter volumeType="Amazon DynamoDB - Import Size"
```

Verified us-east-2: `$0.15/GB`. The unit is uncompressed source size — match the calculator's "Uncompressed source file size for Import from Amazon S3" wording.

### DAX node-hours

```
--service-code AmazonDAX
--filter regionCode=<region>
--filter instanceType=<r5.large|r5.xlarge|r5.2xlarge|...>
```

`AmazonDAX` is its own service-code. Instance types are bare (`r5.large`, not `dax.r5.large`) — the `dax.` prefix only appears in `usagetype`. Single OnDemand `Hrs` priceDimension per SKU. Verified us-east-2: `r5.large` is `$0.255/hr` (3 nodes × 730 hr × $0.255 = $558.45/mo — matches the captured `dynamoDBDaxNodes.serviceCost.monthly = 558.45`).

DAX has no Reserved Instance SKUs published via the Price List API as of 2026-05; the calculator UI only exposes on-demand. **Verify before claiming RI pricing for DAX.**

## Multipliers / formula

`hours = 730`. Use the `month_secs = 730 * 3600 = 2_628_000` constant for any per-second rate conversions if needed (most DynamoDB fields are already monthly).

### On-demand sub-service

```
writes_mo  = writeRateId * 1_000_000
reads_mo   = readRateId  * 1_000_000

# Write-side: split by mix, multiplied for transactional, IA-aware
write_units_std   = writes_mo * (standardWritesId      / 100)
write_units_txn   = writes_mo * (transactionalWritesId / 100) * 2   # transactional = 2x
write_units_total = write_units_std + write_units_txn

# Read-side: standard = 1 RU per 4 KB rounded up; eventually consistent = 0.5x; transactional = 2x
ru_per_read = ceil(averageItemSizeForAllAttributes / 4)             # 4 KB per RRU; size in KB
reads_std_strong = reads_mo * (stronglyConsistentId   / 100) * ru_per_read * 1.0
reads_std_eventu = reads_mo * (eventuallyConsistentId / 100) * ru_per_read * 0.5
reads_std_txn    = reads_mo * (transactionalId        / 100) * ru_per_read * 2.0
read_units_total = reads_std_strong + reads_std_eventu + reads_std_txn

# Write request units are 1 WRU per 1 KB rounded up
wu_per_write = ceil(averageItemSizeForAllAttributes / 1)
write_units_total *= wu_per_write

# Pick rates by selectTableClass — look up the IA rates live; do not assume a fixed multiplier.
# (The IA replicated-write SKU is ~1.25x standard, not the ~2.4x implied by an old note here;
#  query group=DDB-WriteUnitsIA / DDB-ReadUnitsIA for the region rather than scaling.)
rate_write_per_unit = $6.25e-07  if standard else <DDB-WriteUnitsIA rate for region>
rate_read_per_unit  = $1.25e-07  if standard else $1.55e-07   # IA read $0.155/M us-east-2

monthly_ondemand = (write_units_total * rate_write_per_unit)
                 + (read_units_total  * rate_read_per_unit)
                 + storage_monthly(dataStorageSize, selectTableClass)

# storage_monthly = dataStorageSize * per_gb_rate  (NO 25 GB free-tier subtraction — the SPA bills flat)
#   Standard: $0.25/GB-Mo;  Standard-IA: $0.10/GB-Mo (us-east-2)
```

Reconciled against the capture: `dynamoDBOnDemand` = `$9.38` = 10M writes × 1 WRU × $6.25e-07 ($6.25) + 10M reads × 0.5 RU × $1.25e-07 ($0.625) + 10 GB × $0.25 ($2.50) = `$9.375`. The **flat** storage (no free tier) is what closes the cent — and it confirms the read/write split formula above.

Replicated write request units (for Global Tables) use `DDB-ReplicatedWriteUnits` — same shape, replace the rate.

### Provisioned sub-service

```
wcu_required = ceil( max(baselineWriteRateId, peakWriteRateId) * wu_per_write )   # peak drives sizing
rcu_required = ceil( max(baselineReadRateId,  peakReadRateId)  * ru_per_read * 0.5_if_eventual_else_1 )  # the calculator weights by consistency mix

# Reserved fraction and on-demand fraction
wcu_reserved   = wcu_required * (percentWriteReservedCapacity / 100)
wcu_ondemand   = wcu_required - wcu_reserved
rcu_reserved   = rcu_required * (percentReservedCapacity     / 100)
rcu_ondemand   = rcu_required - rcu_reserved

monthly_provisioned = wcu_reserved * hours * $0.000128                   # reserved WCU hourly (1yr Heavy std)
                    + rcu_reserved * hours * $0.000025                   # reserved RCU hourly (1yr Heavy std)
                    + wcu_ondemand * hours * $0.00065                    # on-demand provisioned WCU
                    + rcu_ondemand * hours * $0.00013                    # on-demand provisioned RCU
                    + storage_monthly(provisionedDataStorageSize, selectTableClassProvisioned)

upfront_provisioned = wcu_reserved * $1.50                                # 1yr Heavy std upfront per WCU
                    + rcu_reserved * $0.30                                # 1yr Heavy std upfront per RCU
```

`baseline*/peak*/durationPeak*` together model autoscaling shape; the calculator's exact peak-blending math is *believed* to be `ceil(baseline + (peak - baseline) * (durationPeakHrs / 730))` for each of read and write.

> **Do NOT quote a non-trivial provisioned peak/baseline split without a HAR.** This formula is not reconciled to the capture: at baseline 100 / peak 400 / 72 hrs the documented blend gives ~$30.75 while the captured recurring is `$28.64`, and the **upfront** ($180) cleanly matches a *baseline-100* sizing — i.e. upfront and recurring use **different** capacity bases. Reserved-only at baseline (no peak) is too low; the blend is too high. Until this is reverse-engineered, restrict provisioned DynamoDB estimates to baseline-only (peak = baseline) configs, or capture a HAR for the exact peak/baseline split and re-derive. Flag the uncertainty in the breakdown.

### DAX

```
monthly_dax = sum over node_groups of (Number_of_nodes * hours * node_hourly_rate)
```

Per-instance-type lookup via `AmazonDAX`. No upfront.

### Streams

```
billable_requests = max(0, streamReadRequests - 2_500_000)
monthly_streams   = billable_requests * $2e-07
```

The captured 10 requests → $0 is consistent with the free-tier band.

### Backup

```
monthly_backup = onDemandDataStorage   * $0.10        # on-demand backup
               + continuousDataStorage * $0.20        # PITR
               + restoreSize           * <region restore /GB>
```

Captured 10 + 10 + 10 GB in us-east-2 → 10×$0.10 + 10×$0.20 + 10×$0.15 = `$4.50`, matching the captured `dynamoDBOnBackup.serviceCost.monthly = 4.5`. Restore rate inferred from the capture math; **verify the restore-per-GB rate against the Price List API** for non-`us-east-2` regions.

### Change data capture

```
units_per_write = ceil(KDS_AvgDataSize / 1)            # 1 KB per CDC unit
total_units     = KDS_writesCaptured * units_per_write
monthly_cdc     = total_units * $1e-07                  # = $0.10 per million
```

### Export + import

```
monthly_export = exportS3_tableSize * $0.10 + IncrementexportS3_tableSize * $0.10
monthly_import = importS3_tableSize * $0.15
```

The captured 10+10 GB export → $2.00 and 10 GB import → $1.50 both match.

### Parent envelope

```
parent.serviceCost.monthly = sum of subServices[*].serviceCost.monthly
parent.serviceCost.upfront = sum of subServices[*].serviceCost.upfront   # only the provisioned sub-service contributes upfront for reserved capacity
```

Round each sub-service to two decimals before summing, matching the captured precision.

## configSummary template

The parent `configSummary` concatenates per-sub-service phrases in `subServices[]` order, separated by single spaces. Reproduce the captured ordering and exact phrasing — the SPA renders this directly on the card. From the reference capture (us-east-2, all 8 sub-services present):

```
Table class (Standard), Average item size (all attributes) (1 KB), Data storage size (10 GB) Table class (Standard), Average item size (all attributes) (1 KB), Write reserved capacity term (1 year), Read reserved capacity term (1 year), Data storage size (10 GB) DAX nodes (3), DAX instance type (r5.large) Number of DynamoDB Streams GetRecord API requests (10 per month) On-demand backup data storage (10 GB), Point-In-Time Recovery (PITR) data storage (10 GB), Table data restored (10 GB) Number of writes captured (10 per month), Average write size (10 KB) Full export to Amazon S3 (10 GB), Incremental export to Amazon S3 (10 GB) Uncompressed source file size for Import from Amazon S3 (10 GB)
```

Per sub-service phrase fragments to use when assembling:

| sub-service | summary fragment |
|---|---|
| `dynamoDbOnDemand` | `Table class (<Standard\|Standard-IA>), Average item size (all attributes) (<N> KB), Data storage size (<N> GB)` |
| `amazonDynamoDbProvisionedThroughputCapacity` | `Table class (<Standard\|Standard-IA>), Average item size (all attributes) (<N> KB), Write reserved capacity term (<1 year>), Read reserved capacity term (<1 year>), Data storage size (<N> GB)` |
| `amazonDynamoDbDaxClusters` | `DAX nodes (<N>), DAX instance type (<type>)` |
| `amazonDynamoDbStreams` | `Number of DynamoDB Streams GetRecord API requests (<N> per month)` |
| `dynamoDbBackup` | `On-demand backup data storage (<N> GB), Point-In-Time Recovery (PITR) data storage (<N> GB), Table data restored (<N> GB)` |
| `dynamoDbChangeDateCapture` | `Number of writes captured (<N> per month), Average write size (<N> KB)` |
| `dynamoDbDataExportToAmazonS3` | `Full export to Amazon S3 (<N> GB), Incremental export to Amazon S3 (<N> GB)` |
| `dynamoDbDataImportFromAmazonS3` | `Uncompressed source file size for Import from Amazon S3 (<N> GB)` |

Note the **single-space** separator between sub-service fragments (not `", "`) — the capture is explicit about this, and the SPA's parser depends on the boundary.

## Defaults

Apply when the user is silent. Always emit only the sub-services the user actually mentioned — do not default in DAX or backups just because the schema supports them.

| Field | Default | Why |
|---|---|---|
| capacity mode | `dynamoDbOnDemand` | On-demand is the safer default for unspecified workloads; no commitment risk |
| `selectTableClass` / `selectTableClassProvisioned` | `standard` | Cheapest baseline reads; flag if user mentions IA |
| `averageItemSizeForAllAttributes` | `1` KB | Calculator default; flag this — RU/WRU math is linear in item size |
| `dataStorageSize` / `provisionedDataStorageSize` | `10` GB | Matches calculator UI default |
| `writeRateId` / `readRateId` (on-demand) | `10` million/mo each | Calculator UI default |
| `standardWritesId` / `eventuallyConsistentId` | `100` | All writes standard, all reads eventually consistent |
| `transactionalWritesId` / `transactionalId` / `stronglyConsistentId` / `transactionalWriteId` | `0` | Match calculator default |
| `baseline*RateId` (provisioned) | `100` per second | Calculator UI default |
| `peak*RateId` | `400` per second | Calculator UI default |
| `durationPeak*Id` | `72` hours/month | Calculator UI default (≈ 10% of month) |
| `percentReservedCapacity` / `percentWriteReservedCapacity` | `100` if user says "reserved", else `0` | Reserved capacity is opt-in |
| `reservedCapacityTermRead` / `reservedCapacityTermWrite` | `1yr` | The only term the Price List API publishes |
| `streamReadRequests` | omit sub-service entirely | Streams are opt-in |
| backup / CDC / export / import sub-services | omit entirely | Opt-in |
| DAX | omit entirely | Opt-in; if requested without node count, flag and assume 3 × `r5.large` to match the captured shape |

## Verification

- **Source capture**: `captures/saveAs/per-service/amazonDynamoDb.json` — a full DynamoDB line item with all 8 sub-services in `us-east-2`, parent `serviceCost = {"monthly": 604.47, "upfront": 180}`.
- **Region tested end-to-end**: `us-east-2` / `US East (Ohio)`. Rates pulled live via `pricing_client.py --profile <your-profile>`, service-codes `AmazonDynamoDB` and `AmazonDAX`.
- **Reproduced sub-service monthlies** (against the capture):
  - `dynamoDBDaxNodes`: captured `$558.45` → 3 × 730 × $0.255 = `$558.45`. Exact.
  - `dynamoDBOnBackup`: captured `$4.50` → 10×$0.10 + 10×$0.20 + 10×$0.15 = `$4.50`. Exact.
  - `dynamoDBDataExportS3`: captured `$2.00` → (10 + 10) × $0.10 = `$2.00`. Exact.
  - `dynamoDBDataImportS3`: captured `$1.50` → 10 × $0.15 = `$1.50`. Exact.
  - `dynamoDBOnDemandStreams`: captured `$0` → 10 requests is below the 2.5M free-tier band. Consistent.
  - `dynamoDBChangeDataCapture`: captured `$0` → 10 writes × 10 CDC units × $1e-07 ≈ $1e-05, rounds to `$0.00`. Consistent.
  - `dynamoDBOnDemand`: captured `$9.38` → **reconciled to the cent** as 10M writes × 1 WRU × $6.25e-07 ($6.25) + 10M reads × 0.5 RU × $1.25e-07 ($0.625) + 10 GB × $0.25 **flat** storage ($2.50) = `$9.375`. The key was using flat storage with **no** 25 GB free tier (see the Storage section). This also confirms the read/write split formula.
  - `dynamoDBProvisioned`: captured `$28.64 / $180 upfront` — the upfront cleanly matches 100% reserved at baseline 100 RCU + 100 WCU (100×$0.30 + 100×$1.50 = $180). The recurring `$28.64` is consistent with the reserved hourly rates plus a small storage charge, but the **exact peak/baseline blending used to size committed capacity has not been re-derived from the SPA's bundle** — verify before relying on this for non-trivial peak/baseline configurations.
- **Inferred and not yet verified — verify before relying on this**:
  - The provisioned peak-blend formula (`ceil(baseline + (peak - baseline) * (durationPeakHrs / 730))`).
  - The exact RU multipliers the SPA applies for transactional / eventually-consistent / IA splits — captured here from public DynamoDB pricing docs but not reproduced field-by-field from the SPA bundle.
  - The restore-size per-GB rate (`$0.15` in us-east-2 was inferred to match the captured `$4.50` backup total; query `volumeType="Amazon DynamoDB - Backup Restore Size"` for each region to confirm).
  - 3-year reserved capacity: not exposed by the Price List API or the calculator UI. Map any user request for "3-year DDB reserved" to `1yr` and flag in the breakdown.
  - DAX reserved-instance pricing: no `Reserved` term in `AmazonDAX` SKUs. Treat all DAX as on-demand.
  - The `configSummary` for the **provisioned** sub-service when the user opts for 0% reserved capacity — the captured example only exercises 100% reserved. The "Write/Read reserved capacity term" fragments may be omitted in the 0%-reserved case; verify with a fresh capture before producing one.

# Kinesis Data Streams (`amazonKinesisDataStreams`)

Covers Amazon Kinesis Data Streams in three distinct modes that share one `serviceCode`. The mode is picked by the `estimateFor` value, and the calculator uses a **different set of `calculationComponents` field names per mode** (suffixes: `*` for Provisioned, `*OnDemand`, `*Advantage`). Don't mix them.

## Line-item header

```json
{
  "serviceCode":  "amazonKinesisDataStreams",
  "estimateFor":  "<see Modes table>",
  "version":      "0.0.95",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Kinesis Data Streams",
  "description":  null
}
```

`estimateFor` is the one knob that switches modes. `version` is the same form-bundle version across all three.

## Modes

| `estimateFor` | When to use | Notes |
|---|---|---|
| `amazonKinesisDataStreams` | User has a shard plan / explicitly mentions "provisioned" / wants the cheapest option for steady, predictable throughput | Provisioned mode. Charges per shard-hour + payload units. EFO billed separately. |
| `amazonKinesisDataStreamsOnDemand` | User says "on-demand" without further qualification, or wants auto-scaling with classic per-GB pricing | Classic On-Demand. Per-stream-hour + per-GB-in + per-GB-out + per-GB-out-EFO. No shard math. |
| `amazonKinesisDataStreamsOnDemandAdvantage` | User wants the newer cost-optimized auto-scaling tier — typically for larger records and steady throughput | On-Demand Advantage. **Account-level 25 MB/s minimum** charged on both ingest and retrieval (shortfall billed at the same per-GB rate). No stream-hour. EFO is free. |

When the brief is vague, default to **classic On-Demand** — it's the safest match for "Kinesis" without further detail and reproduces the calculator's default page.

## calculationComponents (verified shape)

### Provisioned (`estimateFor: amazonKinesisDataStreams`)

```json
{
  "percentBuffer":                  {"value": "20"},
  "numberOfRetentionDays":          {"value": "1",  "unit": "day"},
  "baselineNumberOfRecords":        {"value": "10", "unit": "perSecond"},
  "numberOfRecords":                {"value": "10", "unit": "perSecond"},
  "averageRecordSize":              {"value": "10", "unit": "kb|NA"},
  "numberOfConsumerApplications":   {"value": "10"},
  "numberOfEnhancedFanoutConsumers":{"value": "10"}
}
```

- `baselineNumberOfRecords` is the steady-state rate; `numberOfRecords` is the peak. The calculator sizes shards from the peak.
- `percentBuffer` is the headroom applied on top of the peak before shard count is rounded up.
- `numberOfConsumerApplications` are GetRecords (shared-throughput) consumers; they don't add shard cost but do consume read bandwidth (and may force extra shards if read demand exceeds `2 MB/s/shard`).
- `numberOfEnhancedFanoutConsumers` triggers consumer-shard-hour + EFO data-retrieval charges.

### On-Demand classic (`estimateFor: amazonKinesisDataStreamsOnDemand`)

```json
{
  "numberOfRetentionDaysOnDemand":          {"value": "1",  "unit": "day"},
  "numberOfRecordsOnDemand":                {"value": "10", "unit": "perSecond"},
  "averageRecordSizeOnDemand":              {"value": "10", "unit": "kb|NA"},
  "numberOfConsumerApplicationsOnDemand":   {"value": "10"},
  "numberOfEnhancedFanoutConsumersOnDemand":{"value": "10"}
}
```

No baseline/peak split — On-Demand auto-scales. No `percentBuffer`.

### On-Demand Advantage (`estimateFor: amazonKinesisDataStreamsOnDemandAdvantage`)

```json
{
  "averageRecordSizeAdvantage":            {"value": "200", "unit": "kb|NA"},
  "numberOfConsumerApplicationsAdvantage": {"value": "2"},
  "numberOfRetentionDaysAdvantage":        {"value": "1",   "unit": "day"},
  "numberOfRecordsAdvantage":              {"value": "3",   "unit": "perSecond"}
}
```

No EFO field — EFO is free in Advantage. The calculator handles the 25 MB/s account minimum internally.

## Pricing API filters

All Kinesis Data Streams rates live under `--service-code AmazonKinesis`, `productFamily=Kinesis Streams`. The `group` attribute partitions the SKUs cleanly by mode and dimension.

### Provisioned shard hour
```
--service-code AmazonKinesis
--filter regionCode=<region>
--filter group="Provisioned shard hour"
```
One OnDemand priceDimension in `ShardHour` (verified $0.015 in us-east-2).

### Payload units (PUT requests, 25 KB each, Provisioned mode)
```
--service-code AmazonKinesis
--filter regionCode=<region>
--filter group="Payload Units"
```
Returns `$0.014 per 1 million payload units` (raw `price_per_unit` is `1.4e-08` per unit).

### Addon shard hour (extended retention, Provisioned, 1–7 days)
```
--service-code AmazonKinesis
--filter regionCode=<region>
--filter group="Addon shard hour"
```
$0.020/ShardHour in us-east-2. The calculator only invokes this when `numberOfRetentionDays > 1`.

### On-Demand classic (stream-hour + ingest + retrieval + EFO + retention)
```
--service-code AmazonKinesis
--filter regionCode=<region>
--filter group="OnDemand"
```
Returns 6 SKUs by `operation`:
- `OnDemandStreamHr` — $0.04 / stream-hour
- `OnDemandDataIngested` — $0.08 / GB ingested
- `OnDemandDataRetrieval` — $0.04 / GB read (GetRecords / standard consumers)
- `OnDemandEFODataRetrieval` — $0.05 / GB read via EFO
- `OnDemandExtendedRetentionByteHrs` — $0.10 / GB-month (1–7 day extended retention)
- `OnDemandLongTermRetentionByteHrs` — $0.023 / GB-month (beyond 7 days)

### On-Demand Advantage
```
--service-code AmazonKinesis
--filter regionCode=<region>
--filter group="OnDemand Advantage"
```
Returns SKUs keyed by `kinesisAdvantageOperation`:
- `AdvantageDataIngested` — $0.032 / GB ingested
- `AdvantageDataIngestionShortfall` — $0.032 / GB (same rate, applied to the 25 MB/s gap)
- `AdvantageDataRetrieval` — $0.016 / GB retrieved (standard or EFO)
- `AdvantageDataRetrievalShortfall` — $0.016 / GB (same rate, applied to the 25 MB/s gap)
- `AdvantageEFODataRetrieval` — $0.016 / GB (EFO is the same rate as standard)
- `AdvantageExtRetentionByteHrs` — $0.023 / GB-month (extended retention)
- `AdvantageLTRetentionByteHrs` — $0.023 / GB-month (long-term retention)

There is **no** stream-hour or consumer-shard-hour SKU in `OnDemand Advantage` — both are folded into the per-GB rates with the 25 MB/s minimum.

### Enhanced fan-out (Provisioned mode only)
```
--service-code AmazonKinesis --filter regionCode=<region> --filter group="Enhanced fan-out consumer-shard hour"
--service-code AmazonKinesis --filter regionCode=<region> --filter group="Enhanced fan-out GB of data retrieved"
```
- `ConsumerHour` — $0.015 / consumer-shard-hour
- `EnhancedFanoutDataRetrieval` — $0.013 / GB

## Multipliers / formula

Let `hours = 730`, `secs = 730 * 3600 = 2,628,000`. Convert KB↔GB via `/1024/1024`.

### Provisioned

```
ingest_kb_s   = numberOfRecords * averageRecordSize
required_in   = ceil(ingest_kb_s / 1024)                  # shards for ingest (1 MB/s each)
read_kb_s     = ingest_kb_s * (numberOfConsumerApplications + numberOfEnhancedFanoutConsumers)
required_out  = ceil(read_kb_s / 2048)                    # shards for read (2 MB/s each)
shards        = ceil(max(required_in, required_out) * (1 + percentBuffer/100))
ingest_gb_mo  = ingest_kb_s * secs / (1024*1024)
records_mo    = numberOfRecords * secs
payload_units = records_mo * ceil(averageRecordSize / 25) # 25 KB per PU
ext_days      = max(0, numberOfRetentionDays - 1)         # day 1 included

monthly = shards * hours * 0.015                          # provisioned shard-hour
        + payload_units * 1.4e-08                         # payload units
        + (shards * hours * 0.020 if ext_days > 0 else 0) # extended retention shard-hour (≤7d)
        + numberOfEnhancedFanoutConsumers * shards * hours * 0.015
        + numberOfEnhancedFanoutConsumers * ingest_gb_mo * 0.013
```

### On-Demand classic

```
ingest_gb_mo  = (numberOfRecordsOnDemand * averageRecordSizeOnDemand) * secs / (1024*1024)

monthly = hours * 0.04                                                          # stream-hour
        + ingest_gb_mo * 0.08                                                   # ingest
        + numberOfConsumerApplicationsOnDemand    * ingest_gb_mo * 0.04         # GetRecords
        + numberOfEnhancedFanoutConsumersOnDemand * ingest_gb_mo * 0.05         # EFO retrieval
        + retention_charges_if_days_gt_1
```

EFO in classic On-Demand has **no separate consumer-shard-hour** charge — the $0.05/GB EFO rate is all-in.

### On-Demand Advantage

The defining trick: a per-account **25 MB/s minimum** on both ingest and retrieval. Below the floor, you pay the shortfall at the same per-GB rate.

```
ingest_mb_s        = numberOfRecordsAdvantage * averageRecordSizeAdvantage / 1024
retrieval_mb_s     = ingest_mb_s * numberOfConsumerApplicationsAdvantage
billed_ingest_mb_s = max(ingest_mb_s, 25)
billed_read_mb_s   = max(retrieval_mb_s, 25)

monthly = (billed_ingest_mb_s * secs / 1024) * 0.032                            # ingest + shortfall
        + (billed_read_mb_s   * secs / 1024) * 0.016                            # retrieval + shortfall
        + retention_charges_if_days_gt_1
```

The 25 MB/s minimum dominates tiny workloads — that's why the captured 3 rec/s × 200 KB job comes out to $3079.73 vs. ~$270 in classic.

## configSummary template

Reproduce the captured phrasing per mode (the SPA reads it for the card title):

- **Provisioned** — `"Duration of data retention (<N> days), Baseline number of records (<N> per second), Peak number of records (<N> per second), Number of Consumer Applications (<N>)"`
- **On-Demand classic** — `"Number of days for data retention (<N> days), Number of records (<N> per second), Number of Consumer Applications (<N>)"`
- **On-Demand Advantage** — `"Number of Consumer Applications (<N>), Data retention needed (<N> days), Number of records (<N> per second)"`

## Defaults

| Field | Provisioned | OnDemand classic | OnDemand Advantage |
|---|---|---|---|
| retentionDays | `"1"` (included) | `"1"` | `"1"` |
| baseline/peak records | `"10"` per second | n/a | n/a |
| numberOfRecords (peak / OD / Adv) | `"10"` per second | `"10"` per second | `"3"` per second |
| averageRecordSize | `"10"` kb | `"10"` kb | `"200"` kb |
| consumer applications | `"10"` | `"10"` | `"2"` |
| EFO consumers | `"10"` | `"10"` | — (free, no field) |
| percentBuffer | `"20"` | — | — |

When the user is silent, use **classic On-Demand with 10 rec/s × 10 KB, 1-day retention, 10 standard consumers, 0 EFO consumers**. Flag any assumption (record size, consumer count, mode) in the breakdown so the user can correct it.

## Verification

- Source: `/home/fahadmustafa/src/aws-calc/captures/calculator.aws_new.har` (the `POST /Prod/v2/saveAs` body holds all three line items).
- Region tested end-to-end: `us-east-2` / `US East (Ohio)`.
- Reproduced monthlies (rates pulled live via `pricing_client.py --profile zaintech-cloudtools`, ServiceCode `AmazonKinesis`):
  - Provisioned: **$273.85** captured → computed $273.85 with `shards = ceil(1 × 1.2) = 2`, 10 EFO consumers × 2 shards × 730 hr × $0.015 + 10 × 250.63 GB × $0.013 + 2 × 730 × $0.015 + 26.28 M PU × $1.4e-8.
  - On-Demand classic: **$274.81** captured → computed $274.81 = 730 × $0.04 + 250.63 × $0.08 + 10 × 250.63 × $0.04 + 10 × 250.63 × $0.05.
  - On-Demand Advantage: **$3079.73** captured → computed $3079.69 (≤0.05 rounding drift) = max(0.586, 25) MB/s × 2,628,000 s ÷ 1024 GB × $0.032 + max(1.172, 25) MB/s × 2,628,000 s ÷ 1024 GB × $0.016.
- Inferred but not directly captured:
  - The Provisioned shard formula's exact rounding behaviour at the `percentBuffer` step — verified only at `peak = 10/s × 10 KB` with `buffer = 20%` ⇒ 2 shards. Multi-shard / fractional cases should be HAR-tested before relying on it.
  - Retention beyond 1 day for any mode is not exercised by the captured estimate. The relevant SKUs (`Addon shard hour`, `OnDemandExtendedRetentionByteHrs`, `Advantage*RetentionByteHrs`) are documented but the calculator's day-1-included boundary needs a fresh capture to confirm.
  - Standard consumer reads in **Provisioned** mode appear to be free (no SKU charged separately); the only consumer-driven cost was EFO. Verify before claiming "no charge for `numberOfConsumerApplications` in Provisioned" in user-facing copy.

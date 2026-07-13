# Amazon Data Firehose (`amazonKinesisFirehose`)

Formerly Kinesis Data Firehose. Covers the streaming ingest → transform → delivery path in a single line item: PUT/KDS ingest, format conversion (Parquet/ORC), dynamic partitioning, JQ metadata processing, S3 object delivery, and VPC delivery.

## Line-item header

```json
{
  "serviceCode":  "amazonKinesisFirehose",
  "estimateFor":  "KinesisDataFirehose",
  "version":      "0.0.112",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Data firehose",
  "description":  null
}
```

`serviceName` is literally `"Amazon Data firehose"` (lowercase `f`) — that's what the SPA renders and what the captured saveAs body carries. Don't "fix" it.

## calculationComponents (verified shape)

```jsonc
{
  "sourceType":                  {"value": "direct"},                  // "direct" = Direct PUT; "kds" = Kinesis Data Streams source; "msk" = MSK source
  "numberOfRecordsIngested":     {"value": "10", "unit": "perSecond"}, // record rate; pair with recordMultDI
  "recordMultDI":                {"value": "1000"},                    // record-units multiplier: "1"=records, "1000"=thousands, "1000000"=millions
  "dataPerRecord":               {"value": "5",  "unit": "kb|NA"},     // size per record; unit "kb|NA" or "mb|NA"
  "ratioDataRetry":              {"value": "1.3"},                     // ratio of data processed to VPC vs data ingested (NOT a retry multiplier — only inflates the VPC byte path)
  "dataFormatConversionSelect":  {"value": "1"},                       // "1" enables Parquet/ORC format conversion at $0.018/GB ingested; "0" disables
  "dynamicPartitioningAddOn":    {"value": "1"},                       // "1" enables Dynamic Partitioning at $0.02/GB ingested + per-object delivery charge; "0" disables
  "sizeObjectDelivered":         {"value": "64", "unit": "mb|NA"},     // average delivered object size; drives object-count charge when DP is on
  "DynamicPartitionJQEnable":    {"value": "1"},                       // "1" enables JQ metadata processing at $0.07 per JQ-hour; "0" disables
  "hrsJQprocessing":             {"value": "70"},                      // JQ processing hours per month
  "numberOfSubnets":             {"value": "10"}                       // VPC-delivery AZ count; charged as per-AZ-hour AND drives VPC-bytes path
}
```

The "1"/"0" string values on the four toggles (`dataFormatConversionSelect`, `dynamicPartitioningAddOn`, `DynamicPartitionJQEnable`) are how the SPA encodes its enable checkboxes — booleans encoded as strings.

## Pricing API filters

All Firehose rates live under `--service-code AmazonKinesisFirehose`, `productFamily="Kinesis Firehose"`. The `usagetype` attribute is the cleanest filter; usagetypes are prefixed with the regional code (`USE2-` for us-east-2, `USE1-`, `EUW1-`, etc.). Replace `USE2` with the user's region prefix.

### Direct PUT ingest (tiered)
```
--service-code AmazonKinesisFirehose
--filter regionCode=<region>
--filter usagetype=<PREFIX>-BilledBytes
```
Two SKUs (PutRecord, PutRecordBatch) with the same tiered rate; either works. Tiers in us-east-2: $0.029/GB for 0–500 TB, $0.025/GB for 500–2000 TB, $0.020/GB above 2000 TB. (`begin_range` is in GB.)

### Kinesis Data Streams source ingest (tiered)
```
--filter usagetype=<PREFIX>-StreamsSourceBilledBytes
```
Same three-tier shape ($0.029 / $0.025 / $0.020 per GB). Used when `sourceType="kds"`.

### MSK source ingest
```
--filter usagetype=<PREFIX>-MSKAsSourceBilledBytes
```

### Format conversion (Parquet / ORC)
```
--filter usagetype=<PREFIX>-DFCBilledBytes
```
Single flat rate: $0.018/GB of data ingested when format conversion is enabled.

### Dynamic partitioning — bytes delivered
```
--filter usagetype=<PREFIX>-DPBytesDelivered
```
$0.02/GB of data processed through dynamic partitioning.

### Dynamic partitioning — S3 object count
```
--filter usagetype=<PREFIX>-S3DeliveryObjectCount
```
$0.005 per **thousand** dynamically-partitioned objects delivered (raw `price_per_unit` is `5e-06` per object).

### JQ metadata processing
```
--filter usagetype=<PREFIX>-MetadataProcessingDuration
```
$0.07 per JQ processing hour.

### VPC delivery — bytes
```
--filter usagetype=<PREFIX>-Firehose-VpcDelivery-Bytes
```
$0.01/GB delivered to VPC destination (rate varies by region).

### VPC delivery — AZ-hours
```
--filter usagetype=<PREFIX>-Firehose-VpcDelivery-Hours
```
$0.01 per Hour per AZ for VPC delivery.

## Multipliers / formula

Use a 730-hour month and **binary GB** (`1 GB = 1024 MB = 1024² KB`). Two derived volumes:

```
records_per_sec   = numberOfRecordsIngested * recordMultDI
kb_per_sec        = records_per_sec * dataPerRecord    # treat dataPerRecord in KB; convert if unit is mb
ingest_gb_month   = kb_per_sec * 2628000 / (1024 * 1024)
vpc_gb_month      = ingest_gb_month * ratioDataRetry    # ratio applies ONLY to the VPC path
objects_per_month = (ingest_gb_month * 1024) / sizeObjectDelivered_mb
```

Then sum:

```
monthly =   tiered_put(ingest_gb_month)                                 # PUT or KDS or MSK source — pick by sourceType
          + (ingest_gb_month * 0.018  if dataFormatConversionSelect="1" else 0)
          + (ingest_gb_month * 0.02   if dynamicPartitioningAddOn="1"    else 0)
          + (objects_per_month * 5e-06 if dynamicPartitioningAddOn="1"   else 0)
          + (hrsJQprocessing * 0.07   if DynamicPartitionJQEnable="1"    else 0)
          + (vpc_gb_month * 0.01      if numberOfSubnets > 0             else 0)
          + (730 * numberOfSubnets * 0.01)                              # per-AZ-hour
serviceCost.upfront = 0
```

`tiered_put(gb)` walks the three PUT tiers (0–500000 GB at $0.029, 500000–2000000 GB at $0.025, >2000000 GB at $0.020).

### Worked breakdown that reproduces $10112.96

Inputs from the captured saveAs body: 10 rec/s × 1000 multiplier × 5 KB/rec, ratio 1.3, DFC on, DP on (with 64 MB objects), JQ on at 70 h, 10 VPC subnets, region us-east-2.

```
records_per_sec   = 10 * 1000 = 10,000
kb_per_sec        = 10,000 * 5 = 50,000
ingest_gb_month   = 50,000 * 2,628,000 / 1,048,576 = 125,312.81 GB   (all in Tier 1)
vpc_gb_month      = 125,312.81 * 1.3 = 162,906.65 GB
objects_per_month = 125,312.81 * 1024 / 64 = 2,005,005

PUT ingest (Tier 1 only, $0.029):              125,312.81 * 0.029 = $3,634.07
Format conversion ($0.018/GB):                 125,312.81 * 0.018 = $2,255.63
Dynamic partitioning bytes ($0.02/GB):         125,312.81 * 0.02  = $2,506.26
DP S3 object count ($0.005/1,000):             2,005,005 * 5e-06  = $   10.03
JQ processing ($0.07/hr × 70 hr):                                    $    4.90
VPC delivery bytes ($0.01/GB × 1.3 × ingest):  162,906.65 * 0.01  = $1,629.07
VPC delivery AZ-hours ($0.01 × 730 × 10):                            $   73.00
                                                                     ---------
                                                          TOTAL    = $10,112.96
```

## configSummary template

Match the captured phrasing exactly — the SPA reads it for the line-item card title:

```
Source Type (<Direct PUT or Kinesis Data Stream | Kinesis Data Streams | MSK>), Dynamic Partitioning (Add On) (<Enabled|Disabled>), Average ratio of data processed to VPC vs data ingested (<ratio>), Data records units (<records|thousands|millions>), Record size (<N> KB), Data format conversion (optional) (<Enabled|Disabled>), Number of records for data ingestion (<N> per second), Average size objects delivered (<N> MB), JQ Processing (optional) (<Enabled|Disabled>), Average JQ expected processing hours (<N>), Number of subnets for VPC delivery (<N>)
```

`recordMultDI` maps to the "Data records units" word: `"1"`→`records`, `"1000"`→`thousands`, `"1000000"`→`millions`.

## Defaults

| Field | Default | Why |
|---|---|---|
| sourceType | `direct` | The calculator's UI default; matches "I want to ship logs to S3" briefs. |
| numberOfRecordsIngested | `"1"` per second | Conservative starting volume; flag in the breakdown. |
| recordMultDI | `"1"` | Treat the record count as literal records, not thousands. |
| dataPerRecord | `"5"` kb | Common payload size; flag if record size matters. |
| ratioDataRetry | `"1"` | No VPC-path inflation; only set above 1 if user mentions VPC delivery with overhead. |
| dataFormatConversionSelect | `"0"` | Off — adds $0.018/GB; only enable if user names Parquet/ORC. |
| dynamicPartitioningAddOn | `"0"` | Off — adds $0.02/GB plus per-object charge; only enable if user mentions partition keys. |
| sizeObjectDelivered | `"64"` mb | Calculator's UI default; only matters when DP is on. |
| DynamicPartitionJQEnable | `"0"` | Off; only enable if user mentions JQ expressions. |
| hrsJQprocessing | `"0"` | Zero unless JQ is enabled. |
| numberOfSubnets | `"0"` | No VPC delivery by default; setting >0 adds AZ-hour + bytes charges. |

## Verification

- Source: captured saveAs body at `/tmp/aws_calc_onboard/amazonKinesisFirehose.json` (path was ephemeral; file lost — re-capture needed; region `us-east-2`, full feature set enabled).
- Region tested end-to-end: `us-east-2` / `US East (Ohio)`.
- Reproduced monthly **$10,112.96 within $0.01** using the formula above and rates pulled live via `pricing_client.py --profile zaintech-cloudtools` against ServiceCode `AmazonKinesisFirehose`.
- Inferred but not directly captured:
  - The KDS-source and MSK-source code paths (`sourceType="kds"`, `"msk"`) — only `"direct"` was exercised in the captured estimate. The rate SKUs exist and the formula slot-in is straightforward, but verify the exact `sourceType` string with a fresh capture before promising those modes.
  - The `recordMultDI` mapping for `"1"` and `"1000000"` is inferred from the `"1000"`→`thousands` capture and the configSummary's "Data records units" wording. Verify with a HAR before relying on the literal strings.
  - The unit-string `"mb|NA"` on `dataPerRecord` is assumed to scale the per-record size by 1024 vs the captured `"kb|NA"`. Not exercised in the capture.

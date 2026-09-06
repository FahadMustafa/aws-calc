# AWS CloudTrail (`awsCloudTrail`)

Covers the four CloudTrail metering surfaces in one line item: management/data/network-activity event recording, Insights analysis, and CloudTrail Lake ingestion + retention + query scanning. Pricing is per-Region; emit one line item per active Region.

## Line-item header

```json
{
  "serviceCode":  "awsCloudTrail",
  "estimateFor":  "template",
  "version":      "0.0.46",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS CloudTrail",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  // --- Unit multipliers. "1000000" means the matching count fields are in MILLIONS.
  // The SPA multiplies count * Mult to get raw events. Stick to "1000000" so the
  // captured configSummary phrasing ("units (millions)") stays correct.
  "OpsMult":                {"value": "1000000"}, // management-event unit
  "dataOpsMult":            {"value": "1000000"}, // data-event unit (S3 + Lambda)
  "networkActivityOpsMult": {"value": "1000000"}, // network-activity-event unit
  "eventMult":              {"value": "1000000"}, // insights-event unit

  // --- Trail counts. With "1" the first copy is delivered to one trail;
  // management-event first copy is FREE. Set higher only for multi-trail fan-out.
  "numberOfWriteTrails":           {"value": "1"}, // # of trails recording write management events
  "numberOfReadTrails":            {"value": "1"}, // # of trails recording read management events
  "numberOfS3Trails":              {"value": "1"}, // # of trails recording S3 data events
  "numberOfLambdaTrails":          {"value": "1"}, // # of trails recording Lambda data events
  "numberOfNetworkActivityTrails": {"value": "1"}, // # of trails recording network-activity events
  "numberOfInsightTrails":         {"value": "1"}, // # of trails with Insights enabled

  // --- Event volumes (in units defined by *Mult above). Value "10" + OpsMult
  // "1000000" = 10,000,000 events/month.
  "numberOfWriteEvents":           {"value": "10", "unit": "perMonth"}, // write mgmt events
  "numberOfReadEvents":            {"value": "10", "unit": "perMonth"}, // read mgmt events
  "numberOfS3Ops":                 {"value": "10", "unit": "perMonth"}, // S3 data events
  "numberOfLambdaOps":             {"value": "10", "unit": "perMonth"}, // Lambda data events
  "numberOfNetworkActivityEvents": {"value": "10", "unit": "perMonth"}, // network-activity events
  // Management events fed into Insights (APICallVolume analysis). Independent
  // input from numberOfWriteEvents — Insights only analyzes what the user opts in.
  "numberOfWMEvents":              {"value": "10", "unit": "perMonth"},

  // --- CloudTrail Lake (in GB, unit literal is "gb|NA").
  "dataIngestedCloudtrail":   {"value": "10", "unit": "gb|NA"}, // GB ingested from CloudTrail logs
  "dataIngestedOther":        {"value": "10", "unit": "gb|NA"}, // GB ingested from other sources (Config, audit logs, etc.)
  "dataRetention":            {"value": "10", "unit": "gb|NA"}, // GB held in extended retention (beyond the default 1-year store)
  "dataScannedUsingQueries":  {"value": "10", "unit": "gb|NA"}  // GB scanned by Lake SQL queries / federation
}
```

All numeric values are stringified. The `*Mult` fields are the calculator's per-million scaling pattern. If a dimension is unused, set its count to `"0"` rather than dropping the key — the SPA expects every field.

## Pricing API filters

ServiceCode is `AWSCloudTrail` (capital letters matter). All filters below pinned to `us-east-2`. The usagetype prefix swaps by Region (`USE2-` here, `USE1-` for us-east-1, `EUW1-` for eu-west-1, etc.) — enumerate with `get-attribute-values --service-code AWSCloudTrail --attribute usagetype`.

### Paid management events (write/read, additional trail copies)

```
--service-code AWSCloudTrail
--filter regionCode=us-east-2
--filter usagetype=USE2-PaidEventsRecorded
```

Single OnDemand rate: **$0.00002 / event** ($2.00 per 100k). Applies to every management event *beyond* the first copy across all trails. With one trail, this is $0.

### Free management events (first copy)

```
--filter usagetype=USE2-FreeEventsRecorded
```

Single OnDemand rate: $0. Tracks the free first copy of mgmt events for the first trail — informational only.

### Data events (S3 + Lambda combined)

```
--filter usagetype=USE2-DataEventsRecorded
--filter productFamily="Management Tools - AWS CloudTrail Data Events Recorded"
```

Single OnDemand rate: **$0.000001 / event** ($0.10 per 100k). The Pricing API exposes ONE SKU covering both S3 and Lambda data events at the same per-event rate — the marketing page's "$0.20/100k Lambda" tier refers to *additional trail copies* and isn't surfaced as a separate SKU.

### Network-activity events

```
--filter usagetype=USE2-NetworkEventsRecorded
--filter eventType="Network events"
```

Single OnDemand rate: **$0.000001 / event** ($0.10 per 100k). The captured estimate treats the first trail copy as free (matches mgmt-event semantics), so 10M events × 1 trail contributed $0 — see Verification. Set to `"0"` if the user isn't recording VPC endpoint data plane traffic.

### Insights events (management API call volume)

```
--filter usagetype=USE2-InsightsEvents
--filter insightstype=APICallVolume
```

Single OnDemand rate: **$0.0000035 / event** ($0.35 per 100k). Charged on every management event analyzed for unusual API-call volume.

### Data-event Insights (separate SKU)

`--filter usagetype=USE2-DataInsightsEvents` — flat **$0.0000003 / event**. Not wired to the captured shape; ignore unless extending.

### CloudTrail Lake — ingestion from CloudTrail logs

```
--filter usagetype=USE2-Ingestion-Bytes-1yearstore-Live-CloudTrail-Logs
```

Flat **$0.75 / GB** ingested (one-year default store included). This is the SKU the calculator uses for `dataIngestedCloudtrail`. The base `USE2-Ingestion-Bytes` SKU at $2.50/$1.00/$0.50 per GB (tiered 0–5TB / 5–25TB / 25TB+) is the *legacy* Lake pricing and is not what the captured estimate hits.

### CloudTrail Lake — ingestion from other sources

`--filter usagetype=USE2-Ingestion-Bytes-1yearstore-Other-data-sources` — flat **$0.50 / GB**. Maps to `dataIngestedOther` (AWS Config snapshots, audit logs, Athena imports, etc.).

### CloudTrail Lake — extended retention

`--filter usagetype=USE2-PaidStorage-ByteHrs` — flat **$0.023 / GB-month**. Charged only beyond the default 1-year store. Maps to `dataRetention`.

### CloudTrail Lake — query scanning

`--filter usagetype=USE2-QueryScanned-Bytes` — flat **$0.005 / GB** scanned. Maps to `dataScannedUsingQueries`.

## Multipliers / formula

```
# Event volumes (count fields are in millions because *Mult = 1,000,000):
mgmt_write_events = numberOfWriteEvents * OpsMult                         # 10 * 1e6 = 10M
mgmt_read_events  = numberOfReadEvents  * OpsMult
s3_events         = numberOfS3Ops       * dataOpsMult
lambda_events     = numberOfLambdaOps   * dataOpsMult
network_events    = numberOfNetworkActivityEvents * networkActivityOpsMult
insight_events    = numberOfWMEvents    * eventMult

# Management events: first copy delivered to one trail is free; charge extras.
extra_mgmt_copies = max(0, numberOfWriteTrails - 1) * mgmt_write_events \
                  + max(0, numberOfReadTrails  - 1) * mgmt_read_events
mgmt_cost = extra_mgmt_copies * 0.00002

# Data events: paid from the first copy onward (one SKU covers S3 and Lambda).
data_cost = s3_events * numberOfS3Trails * 0.000001 + lambda_events * numberOfLambdaTrails * 0.000001

# Network-activity events: first trail copy free in the captured estimate.
network_cost = max(0, numberOfNetworkActivityTrails - 1) * network_events * 0.000001

# Insights: rate * events * trails-with-insights-enabled.
insight_cost = insight_events * numberOfInsightTrails * 0.0000035

# CloudTrail Lake.
lake_cost = dataIngestedCloudtrail*0.75 + dataIngestedOther*0.50 + dataRetention*0.023 + dataScannedUsingQueries*0.005

serviceCost.monthly = mgmt_cost + data_cost + network_cost + insight_cost + lake_cost
serviceCost.upfront = 0
```

The `numberOf*Trails = 1` defaults exploit the first-copy-free behavior. Set any trail count to `2+` to surface the additional-copy charges in `extra_mgmt_copies` / `network_cost` (and via the same multiplier in `data_cost`).

## configSummary template

Match the captured phrasing — the SPA reads this for the line-item card title:

```
Management events units (millions), Management event trails (<N>), Read management trails (<N>), Data events units (millions), S3 trails (<N>), Lambda trails (<N>), Network activity events units (millions), Network activity event trails (<N>), Insight events units (millions), Number of trails and/or event data stores where Insights events are enabled (<N>), Number of management events (<N> per month), Read management events (<N> per month), S3 operations (<N> per month), Lambda data events (<N> per month), Number of network activity events (<N> per month), Total number of management API calls (both read and write) to be analyzed for unusual activity (<N> per month)
```

The fragment stops short of the Lake fields in the captured body — keep it that way. The four GB-denominated fields show up in the breakdown view but not the summary line.

## Defaults

| Field | Default | Why |
|---|---|---|
| OpsMult / dataOpsMult / networkActivityOpsMult / eventMult | "1000000" | Matches the captured shape; counts are in millions |
| numberOfWriteTrails / numberOfReadTrails / numberOfS3Trails / numberOfLambdaTrails / numberOfNetworkActivityTrails / numberOfInsightTrails | "1" | Single org-trail is the common case; first-copy-free for mgmt + network events |
| numberOfWriteEvents | "1" | ~1M write mgmt events/month is a small-to-mid account; bump for noisy estates |
| numberOfReadEvents | "5" | Read events outpace writes ~5:1 in typical traffic |
| numberOfS3Ops | "0" | Data events off by default; opt-in costs add up fast |
| numberOfLambdaOps | "0" | Same — opt-in only |
| numberOfNetworkActivityEvents | "0" | Network activity recording (VPC endpoints) is new and rarely on |
| numberOfWMEvents | "0" | Insights off unless the user explicitly mentions anomaly detection |
| dataIngestedCloudtrail | "0" | Lake off by default; needs the user to mention "CloudTrail Lake" or "event data store" |
| dataIngestedOther | "0" | Same |
| dataRetention | "0" | Extended retention only meaningful with Lake on |
| dataScannedUsingQueries | "0" | Same |

If the user just says "we run CloudTrail" without details, the right answer is $0 (first mgmt-event trail is free). Flag that in the breakdown and ask whether data events, Insights, or Lake are involved.

## Verification

Reproduced the captured `serviceCost.monthly = $67.78` exactly in `us-east-2` with all count fields set to `"10"` (which, with the `*Mult` defaults, equals 10M events / 10 GB per dimension):

- Write management events: 10M × 1 trail (free first copy) → **$0.00**
- Read management events:  10M × 1 trail (free first copy) → **$0.00**
- S3 data events:           10M × $0.000001               → **$10.00**
- Lambda data events:       10M × $0.000001               → **$10.00**
- Network-activity events:  10M × 1 trail (free first copy) → **$0.00**
- Insights (APICallVolume): 10M × $0.0000035              → **$35.00**
- Lake ingest (CloudTrail): 10 GB × $0.75                 → **$7.50**
- Lake ingest (other):      10 GB × $0.50                 → **$5.00**
- Lake retention:           10 GB × $0.023                → **$0.23**
- Lake query scanned:       10 GB × $0.005                → **$0.05**

Total: **$67.78** — exact match to the captured saveAs body at `/tmp/aws_calc_onboard/awsCloudTrail.json` (path was ephemeral; file lost — re-capture needed; originally extracted from `captures/calculator.aws_new.har` (local capture, not in repo), request index 346, posted to `dnd5zrqcec4or.cloudfront.net/Prod/v2/saveAs`).

Rates verified via `pricing_client.py get-products` against `AWSCloudTrail` on the date this module was authored. Two surprises worth flagging before relying on this in other Regions: (1) the Pricing API exposes a single `USE2-DataEventsRecorded` SKU at $0.000001/event covering both S3 and Lambda — the marketing page's separate "$0.20/100k Lambda" rate isn't a distinct SKU and appears to apply only to additional trail copies, which the calculator surfaces via the `numberOfLambdaTrails` multiplier; (2) the calculator treats the first trail copy of network-activity events as free (matching management-event semantics), even though AWS docs price them like data events from the first copy. That's the calculator's behavior; it may change.

Open question: `dataIngestedOther` maps to one SKU at $0.50/GB — the SPA doesn't validate the source, so any GB count is charged at that rate.

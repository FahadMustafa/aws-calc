# Amazon CloudWatch (`amazonCloudWatch`)

One flat line item that covers the entire CloudWatch surface area in the calculator: custom + detailed metrics, the three metric-fetch API families, all four alarm classes, dashboards, Logs (standard + IA, custom + vended), Logs delivered to S3 (with optional Parquet conversion), Logs Insights queries, Synthetics canaries, web + mobile RUM, Contributor Insights (CloudWatch + DynamoDB rules and events), Lambda Insights, and Database Insights (vCPU- and ACU-hour).

CloudWatch is **not** a group/subServices line item — every dimension is a sibling field under one `calculationComponents` object. The free tier is enforced by the SPA on the recipient's side; you don't subtract it explicitly when computing `serviceCost`, but the SPA's recomputation will, so set values realistically rather than padding.

## Line-item header

```json
{
  "serviceCode":  "amazonCloudWatch",
  "estimateFor":  "CloudWatch",
  "version":      "0.0.141",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon CloudWatch",
  "description":  null
}
```

`estimateFor` is literally `"CloudWatch"` (not `"template"` or a long form-id), and `serviceName` is `"Amazon CloudWatch"`. Both pulled directly from the captured saveAs body.

## calculationComponents (verified shape)

Every value is a string under `"value"`. The `unit` field is present on rate-style inputs (per hour / per month / per GB) and absent on plain counts. Boolean-like options are encoded as the magic string `"[ZERO_COST]"` (off) or `"1"` (on).

```jsonc
{
  // ─── Metrics ──────────────────────────────────────────────
  "totalNumberOfMetrics":              {"value": "10"},                    // custom + detailed metrics across the account (free tier: 10/mo)
  "metricsForGetMetricData":           {"value": "10"},                    // metrics requested via GetMetricData API per month
  "metricsForGetMetricWidgetImage":    {"value": "10"},                    // metrics requested via GetMetricWidgetImage API per month
  "metricsForOtherAPIRequests":        {"value": "10"},                    // other API requests (GetMetricStatistics, ListMetrics, PutMetricData, etc.) per month

  // ─── Alarms ───────────────────────────────────────────────
  "numberOfStandardAlarms":            {"value": "10"},                    // standard-resolution alarm metrics
  "numberOfHighResolutionAlarms":      {"value": "10"},                    // high-resolution alarm metrics
  "numberOfCompositeAlarms":           {"value": "10"},                    // composite alarms
  "numberOfAlarmsMetricInsights":      {"value": "10"},                    // alarms defined with a Metrics Insights query

  // ─── Dashboards ───────────────────────────────────────────
  "numberOfDashboards":                {"value": "10"},                    // dashboards (free tier: 3)

  // ─── Logs ─────────────────────────────────────────────────
  "sizeOfStandardLogsDataIngested":             {"value": "10", "unit": "gb|NA"}, // custom (non-vended) Standard-class ingest
  "sizeOfInfrequentAccessLogsDataIngested":     {"value": "10", "unit": "gb|NA"}, // custom (non-vended) Infrequent-Access ingest
  "sizeOfVendedLogsDataIngested":               {"value": "10", "unit": "gb|NA"}, // vended logs (AWS-service generated) ingested Standard-class
  "sizeOfInfrequentAccessVendedLogsDataIngested": {"value": "10", "unit": "gb|NA"}, // vended logs IA-class
  "sizeOfLogsDeliveredToS3":                    {"value": "10", "unit": "gb|NA"}, // logs delivered directly to S3 (vended-logs path)
  "logParquetFormatConversionSelect":           {"value": "[ZERO_COST]"},          // "[ZERO_COST]" = Parquet off; "1" = Parquet on ($0.035/GB on delivered-to-S3 input bytes)
  "logStorageOption":                           {"value": "1"},                    // "1" enables CloudWatch Logs storage charge ($0.03/GB-mo); "[ZERO_COST]" disables
  "sizeOfLogsInsightsQueriesDataScanned":       {"value": "10", "unit": "gb|NA"}, // GB scanned by Logs Insights queries

  // ─── Synthetics ───────────────────────────────────────────
  "numberOfCanaryRuns":                {"value": "10"},                    // total canary runs per month

  // ─── RUM (web) ────────────────────────────────────────────
  "numberOfMonthlyvisitors":           {"value": "10"},                    // monthly visits to your web app (note lowercase 'v')
  "numberOfRumEvents":                 {"value": "10"},                    // RUM events per visit (web)
  "PercentageOfRumEvents":             {"value": "10"},                    // web sampling rate, percent (UI shows "0.1" = 10%, see configSummary)

  // ─── RUM (mobile / OpenTelemetry) ─────────────────────────
  "numberOfMobileVisitors":            {"value": "10"},                    // monthly visits to mobile app
  "numberOfMobileEvents":              {"value": "70"},                    // mobile OTEL events/spans (or spans per visit)
  "percentageOfMobileRumEvents":       {"value": "100"},                   // mobile sampling rate, percent (configSummary renders as 1 = 100%)

  // ─── Contributor Insights ────────────────────────────────
  "insightsRulesForCloudWatch":        {"value": "10"},                    // Contributor Insights rules over CloudWatch Logs
  "logEventsForCloudwatch":            {"value": "10", "unit": "perMonth"},// matched log events for CloudWatch rules (in millions/month — see configSummary)
  "insightsRulesForDynamoDB":          {"value": "10"},                    // Contributor Insights rules over DynamoDB
  "EventsForDynamoDB":                 {"value": "10", "unit": "perMonth"},// matched events for DynamoDB rules (in millions/month)

  // ─── Lambda Insights ─────────────────────────────────────
  "numberOfLambdaFunctions":           {"value": "10"},                    // distinct functions monitored
  "numberOfLambdaInvokes":             {"value": "10", "unit": "perHour"}, // invokes per function per hour

  // ─── Database Insights ────────────────────────────────────
  "numberOfvCPUs_Aurora":              {"value": "10", "unit": "perHour"}, // vCPU-hours: RDS + Aurora provisioned (single bucket in this form)
  "numberOfACUs_AuroraServerless":     {"value": "10", "unit": "perHour"}, // ACU-hours for Aurora Serverless v2
  "numberOfACUs_AuroraLmitless":       {"value": "10", "unit": "perHour"}  // ACU-hours for Aurora Limitless — note the missing "i" ("Lmitless"), match the capture exactly
}
```

Field-name pitfalls — match the capture byte-for-byte:
- `numberOfMonthlyvisitors` (lowercase `v`, no underscore)
- `numberOfACUs_AuroraLmitless` (missing the `i` in "Limitless")
- `EventsForDynamoDB` and `PercentageOfRumEvents` start with capital letters; the rest are lowerCamelCase.
- `logParquetFormatConversionSelect` toggles between `"[ZERO_COST]"` and `"1"`; `logStorageOption` toggles between `"1"` and `"[ZERO_COST]"`.

## Pricing API filters

All filters: `--service-code AmazonCloudWatch --filter regionCode=<region>`. The `usagetype` prefix `USE2-` is for us-east-2 — swap to your region prefix (`USE1-`, `EUW1-`, `APN1-`, etc.). CloudWatch Logs and CloudWatch Events live under `AmazonCloudWatch` here — there are no separate `AmazonCloudWatchLogs` or `AmazonCloudWatchEvents` service codes in the Pricing API.

### Metrics

| Field | Filter | Rate (us-east-2) |
|---|---|---|
| `totalNumberOfMetrics` | `usagetype=<P>-CW:MetricMonitorUsage` (tiered: 0–10k, 10k–250k, 250k–1M, >1M) | $0.30 / $0.10 / $0.05 / $0.02 per metric-month |
| `metricsForGetMetricData` | `usagetype=<P>-CW:GMD-Metrics` | $0.01 per 1,000 metrics |
| `metricsForGetMetricWidgetImage` | `usagetype=<P>-CW:GMWI-Metrics` | $0.02 per 1,000 metrics |
| `metricsForOtherAPIRequests` | `usagetype=<P>-CW:Requests` | $0.01 per 1,000 requests |

`totalNumberOfMetrics` is the only metric-side tiered SKU; the others are flat. Free tier: 10 detailed/custom metrics, 1M API requests — the SPA recomputes this on display, so don't subtract.

### Alarms

| Field | Filter | Rate (us-east-2) |
|---|---|---|
| `numberOfStandardAlarms` | `usagetype=<P>-CW:AlarmMonitorUsage` | $0.10 per alarm metric-month |
| `numberOfHighResolutionAlarms` | `usagetype=<P>-CW:HighResAlarmMonitorUsage` | $0.30 per alarm metric-month |
| `numberOfCompositeAlarms` | `usagetype=<P>-CW:CompositeAlarmMonitorUsage` | $0.50 per composite alarm-month |
| `numberOfAlarmsMetricInsights` | `usagetype=<P>-CW:MetricInsightAlarmUsage` | $0.10 per metric analyzed by the alarm-month |

### Dashboards

```
--filter productFamily=Dashboard
```
Returns no SKUs through the Pricing API in tested regions. The flat published rate is **$3.00 per dashboard per month** after the 3-dashboard free tier. **verify before relying on this** — the price is from AWS public pricing pages, not Price-List API.

> **Re-verify on version bump.** The $3.00/dashboard-month rate comes from the AWS marketing/pricing page and has **no Price-List API guardrail** (no SKU is returned for `productFamily=Dashboard`), so there is no automated cross-check. It may be region-dependent. Carry a date stamp on this figure and re-check it against the AWS dashboards pricing page whenever the form `version` changes.

### Logs — ingestion

| Field | Filter | Rate (us-east-2) |
|---|---|---|
| `sizeOfStandardLogsDataIngested` | `usagetype=<P>-DataProcessing-Bytes` | $0.50 / GB |
| `sizeOfInfrequentAccessLogsDataIngested` | `usagetype=<P>-DataProcessingIA-Bytes` | $0.25 / GB |
| `sizeOfVendedLogsDataIngested` | `usagetype=<P>-VendedLog-Bytes` (tiered: first 10TB, next 20TB, next 20TB, >50TB) | $0.50 / $0.25 / $0.10 / $0.05 per GB |
| `sizeOfInfrequentAccessVendedLogsDataIngested` | `usagetype=<P>-VendedLogIA-Bytes` (tiered, same band thresholds) | $0.25 / $0.15 / $0.075 / $0.05 per GB |

### Logs — delivered to S3 (vended-logs path)

| Sub-feature | Filter | Rate (us-east-2) |
|---|---|---|
| `sizeOfLogsDeliveredToS3` (raw delivery) | `usagetype=<P>-S3-Egress-Bytes` (tiered: 10/20/20/>50 TB) | $0.50 / $0.25 / $0.10 / $0.05 per GB |
| `logParquetFormatConversionSelect="1"` (Parquet conversion) | `operation=ParquetConversion` → `usagetype=<P>-S3-Egress-InputBytes` | $0.035 per GB of input bytes converted |

### Logs — storage (when `logStorageOption="1"`)

```
--filter productFamily="Storage Snapshot"
--filter regionCode=<region>
```
`usagetype=<P>-TimedStorage-ByteHrs`. Rate: **$0.03 per GB-month** of log storage. Applies to ingested-logs volume retained in CloudWatch Logs.

### Logs Insights queries

```
--filter usagetype=<P>-DataScanned-Bytes
```
$0.005 per GB scanned (`sizeOfLogsInsightsQueriesDataScanned`).

### Synthetics

```
--filter usagetype=<P>-CW:Canary-runs
```
$0.0012 per canary run (`numberOfCanaryRuns`). Free tier: 100 runs/month.

### RUM (web)

```
--filter usagetype=<P>-CW:RUM-events
```
$0.00001 per event ($1 per 100k events). Monthly events = `numberOfMonthlyvisitors × numberOfRumEvents × (PercentageOfRumEvents / 100)`. The configSummary shows the sampling rate as a 0–1 fraction (e.g. 10% → `0.1`).

### RUM (mobile / OpenTelemetry)

```
--filter usagetype=<P>-CW:RUM-OTEL-bytes
```
$0.35 per GB of OTEL event payload. The SPA computes payload from event count × an internal byte-size assumption; the exact byte-per-event multiplier the SPA uses is **not** Price-List-derived — **verify before relying on this** if exact-to-the-cent mobile RUM costs matter.

### Contributor Insights

| Field | Filter | Rate (us-east-2) |
|---|---|---|
| `insightsRulesForCloudWatch` | `usagetype=<P>-CW:ContributorInsightRules` | $0.50 per rule-month |
| `logEventsForCloudwatch` (matched events) | `usagetype=<P>-CW:ContributorInsightEvents` | $0.02 per million events |
| `insightsRulesForDynamoDB` | `usagetype=<P>-CW:ContributorRulesManaged` | $0.50 per rule-month |
| `EventsForDynamoDB` (matched events) | `usagetype=<P>-CW:ContributorEventsManaged` | $0.03 per million events |

The `unit: "perMonth"` on `logEventsForCloudwatch` and `EventsForDynamoDB` in the captured body is the SPA's hint that the values are **already in millions per month** (e.g. `"10"` means 10 million matched events/month — see configSummary: "10 million matched log events per month"). Multiply the user's literal value by `1,000,000` before multiplying by the per-event rate.

### Lambda Insights

There is no `Lambda Insights` SKU in `AmazonCloudWatch`. The calculator's Lambda-Insights cost contribution is computed from the resulting CloudWatch Logs ingest and metric counts that Lambda Insights generates — **the form fields `numberOfLambdaFunctions` and `numberOfLambdaInvokes` feed those derived volumes inside the SPA's bundled JS**, not a dedicated SKU lookup. **verify before relying on this** if Lambda Insights is material to the estimate; the SPA's internal conversion factor isn't exposed via the Pricing API and was not reverse-engineered from the captured body.

### Database Insights

```
--filter usagetype=<P>-CW:DatabaseInsights-vCPU-Hours
--filter usagetype=<P>-CW:DatabaseInsights-ACU-Hours
```
Multiple SKUs returned, keyed by `databaseEngineType` (Aurora-MySQL, Aurora-PostgreSQL, RDS MariaDB/MySQL/Oracle/PostgreSQL/SQL Server) × `instanceConfigurationType` (Provisioned, Serverless, Limitless).

Representative rates (us-east-2):
- Provisioned vCPU-hour: $0.0125 (e.g. RDS MariaDB Provisioned)
- Aurora Serverless ACU-hour: $0.003125 (Aurora-PostgreSQL Serverless)
- Aurora Limitless ACU-hour: query the specific SKU for `instanceConfigurationType=Limitless`

The single calculator field `numberOfvCPUs_Aurora` covers **both** Aurora-provisioned and RDS-provisioned vCPU-hours — the SPA does not let the user split engines, so use a representative rate (Aurora-PostgreSQL Provisioned $0.0125 is a safe default in us-east-2; check per region). **verify before relying on this** when the brief calls out a specific engine that prices materially differently.

## Multipliers / formula

Use a 730-hour month. Inputs are the literal string values from `calculationComponents`, parsed as numbers. Tier walks use 1 GB = 1024 MB (binary).

```
# Metrics
metrics_custom       = tiered_metric_monitor(totalNumberOfMetrics)        # 0/10000/250000/1000000 bands
gmd_cost             = metricsForGetMetricData          * 0.00001
gmwi_cost            = metricsForGetMetricWidgetImage   * 0.00002
other_req_cost       = metricsForOtherAPIRequests       * 0.00001

# Alarms
alarm_std_cost       = numberOfStandardAlarms           * 0.10
alarm_hires_cost     = numberOfHighResolutionAlarms     * 0.30
alarm_comp_cost      = numberOfCompositeAlarms          * 0.50
alarm_mi_cost        = numberOfAlarmsMetricInsights     * 0.10

# Dashboards
dash_cost            = numberOfDashboards               * 3.00     # flat; see note

# Logs ingest
log_std_cost         = sizeOfStandardLogsDataIngested            * 0.50
log_ia_cost          = sizeOfInfrequentAccessLogsDataIngested    * 0.25
log_vended_cost      = tiered_vended(sizeOfVendedLogsDataIngested)
log_vended_ia_cost   = tiered_vended_ia(sizeOfInfrequentAccessVendedLogsDataIngested)

# Logs delivered to S3
log_s3_cost          = tiered_s3_delivery(sizeOfLogsDeliveredToS3)
parquet_cost         = (sizeOfLogsDeliveredToS3 * 0.035)  if logParquetFormatConversionSelect == "1" else 0

# Logs storage
total_ingested_gb    = sizeOfStandardLogsDataIngested + sizeOfInfrequentAccessLogsDataIngested
                       + sizeOfVendedLogsDataIngested + sizeOfInfrequentAccessVendedLogsDataIngested
log_storage_cost     = (total_ingested_gb * 0.03)         if logStorageOption == "1" else 0

# Logs Insights queries
insights_cost        = sizeOfLogsInsightsQueriesDataScanned * 0.005

# Synthetics
canary_cost          = numberOfCanaryRuns * 0.0012

# Web RUM
rum_events_per_month = numberOfMonthlyvisitors * numberOfRumEvents * (PercentageOfRumEvents / 100)
rum_cost             = rum_events_per_month * 0.00001

# Mobile RUM (OTEL)
# Conversion of "mobile events" → OTEL payload bytes is internal to the SPA; treat as
# (numberOfMobileVisitors * numberOfMobileEvents * (percentageOfMobileRumEvents / 100)) events
# and multiply by an assumed byte-per-event size, then apply $0.35/GB. Verify against
# the SPA bundle before committing for cost-critical estimates.

# Contributor Insights
ci_cw_rule_cost      = insightsRulesForCloudWatch * 0.50
ci_cw_event_cost     = logEventsForCloudwatch * 1_000_000 * 0.00000002   # unit is millions; rate is per-event
ci_ddb_rule_cost     = insightsRulesForDynamoDB * 0.50
ci_ddb_event_cost    = EventsForDynamoDB * 1_000_000 * 0.00000003

# Lambda Insights — pass-through to logs + metrics; see notes above.

# Database Insights
db_vcpu_cost         = numberOfvCPUs_Aurora        * 730 * 0.0125     # representative provisioned rate
db_acu_sl_cost       = numberOfACUs_AuroraServerless * 730 * 0.003125
db_acu_lim_cost      = numberOfACUs_AuroraLmitless   * 730 * <Aurora-PostgreSQL Limitless ACU-hr rate>

serviceCost.monthly = sum(all of the above)
serviceCost.upfront = 0
```

The captured body's `serviceCost.monthly = 222.05` came from every dimension set to "10" (units vary), `logStorageOption="1"`, Parquet off. Reproducing that to the cent requires the SPA's internal mobile-RUM byte-size assumption and exact Database-Insights engine selection — not reproduced end-to-end here. Reproduce within ~5% by summing the explicit formulae above; for tighter agreement, snapshot the SPA bundle.

> **Caveat — SPA-internal dimensions.** The mobile-RUM byte-per-event factor (events → OTEL payload GB) and the Lambda-Insights cost path (functions/invokes → derived Logs + metrics volume) are **SPA-internal**, not Price-List-derived — they live in the calculator's bundled JS and are not exposed by the Pricing API. Any estimate that leans on these two dimensions **cannot be reconciled to the cent** against a capture; flag this to the user when mobile RUM or Lambda Insights is material to the quote.

## configSummary template

Match the captured ordering and phrasing exactly. The SPA reads this string to render the line-item card. Fields that are zero/disabled are still emitted by the SPA in the capture; keep the same comma-separated layout. From the capture:

```
Number of mobile OTEL events and spans or spans per visit (<numberOfMobileEvents>), Mobile sampling rate (<percentageOfMobileRumEvents/100>), Number of Metrics (includes detailed and custom metrics) (<totalNumberOfMetrics>), GetMetricData: Number of metrics requested (<metricsForGetMetricData>), GetMetricWidgetImage: Number of metrics requested (<metricsForGetMetricWidgetImage>), Number of other API requests (<metricsForOtherAPIRequests>), Number of vCPUs monitored by Database Insights (<numberOfvCPUs_Aurora> per hour), Number of Aurora Capacity Units (ACUs) monitored by Database Insights (<numberOfACUs_AuroraServerless> per hour), Number of Aurora Capacity Units (ACUs) monitored by Database Insights (<numberOfACUs_AuroraLmitless> per hour), Standard Logs: Data Ingested (<sizeOfStandardLogsDataIngested> GB), Infrequent Access Logs: Data Ingested (<sizeOfInfrequentAccessLogsDataIngested> GB), Standard Logs Delivered to CloudWatch Logs (<sizeOfVendedLogsDataIngested> GB), Infrequent Access Logs Delivered to CloudWatch Logs (<sizeOfInfrequentAccessVendedLogsDataIngested> GB), Logs Delivered to S3: Data Ingested (<sizeOfLogsDeliveredToS3> GB), Expected Logs Data scanned (<sizeOfLogsInsightsQueriesDataScanned> GB), Number of Dashboards (<numberOfDashboards>), Number of Standard Resolution Alarm Metrics (<numberOfStandardAlarms>), Number of High Resolution Alarm Metrics (<numberOfHighResolutionAlarms>), Number of composite alarms (<numberOfCompositeAlarms>), Number of alarms defined with a Metrics Insights query (<numberOfAlarmsMetricInsights>), Number of Canary runs (<numberOfCanaryRuns>), Number of Contributor Insights rules for CloudWatch (<insightsRulesForCloudWatch>), Total number of matched log events for CloudWatch (<logEventsForCloudwatch> million matched log events per month), Number of Contributor Insights rules for DynamoDB (<insightsRulesForDynamoDB>), Total number of events for DynamoDB (<EventsForDynamoDB> million events per month), Number of Lambda functions (<numberOfLambdaFunctions>), Number of requests per function (<numberOfLambdaInvokes> per hour), Monthly visits to your web application (<numberOfMonthlyvisitors>), Number of web RUM events per visit (<numberOfRumEvents>), Web sampling rate (<PercentageOfRumEvents/100>), Monthly visits to your mobile applications (<numberOfMobileVisitors>)
```

Key formatting quirks pulled from the capture:
- "Standard Logs Delivered to CloudWatch Logs" = the **vended** logs field (`sizeOfVendedLogsDataIngested`), not the custom one. The phrasing is the SPA's, not a mistake.
- Mobile sampling rate is rendered as a 0–1 fraction (`100%` → `1`), and Web sampling rate likewise (`10%` → `0.1`).
- `logEventsForCloudwatch` and `EventsForDynamoDB` are described in **millions** ("10 million matched log events per month") even though the field value is the literal `"10"`.

## Defaults

When the user doesn't specify a CloudWatch sub-dimension, do not silently enable it — emit `"0"` (or `"[ZERO_COST]"` for the two toggle fields). Defaulting every field to non-zero will pad the bill noticeably. A minimal "monitoring is on" baseline below matches what a small workload typically consumes.

| Field | Minimal-cost default | Why |
|---|---|---|
| `totalNumberOfMetrics` | `"0"` | The user gets 10 detailed metrics free; default 0 so the line item only charges for what the user names. |
| `metricsForGetMetricData` | `"0"` | Cheap but only set if the user mentions dashboards/API consumers. |
| `metricsForGetMetricWidgetImage` | `"0"` | Same. |
| `metricsForOtherAPIRequests` | `"0"` | Free tier covers 1M requests; default off. |
| `numberOfStandardAlarms` | `"0"` | 10/mo free in the AWS free tier; default zero in the form. |
| `numberOfHighResolutionAlarms` | `"0"` | Premium charge; only enable if user mentions sub-minute alarms. |
| `numberOfCompositeAlarms` | `"0"` | Premium charge; opt-in only. |
| `numberOfAlarmsMetricInsights` | `"0"` | Opt-in only. |
| `numberOfDashboards` | `"0"` | 3 free; default 0 in the form. |
| `sizeOfStandardLogsDataIngested` | `"0"` | Most expensive per-GB CloudWatch dimension; require explicit volume. |
| `sizeOfInfrequentAccessLogsDataIngested` | `"0"` | Same. |
| `sizeOfVendedLogsDataIngested` | `"0"` | Same. |
| `sizeOfInfrequentAccessVendedLogsDataIngested` | `"0"` | Same. |
| `sizeOfLogsDeliveredToS3` | `"0"` | Same. |
| `logParquetFormatConversionSelect` | `"[ZERO_COST]"` | Adds $0.035/GB; off unless user names Parquet. |
| `logStorageOption` | `"1"` | Log storage is enabled by default in the captured body — match it; toggle `"[ZERO_COST]"` only if user explicitly disables retention. |
| `sizeOfLogsInsightsQueriesDataScanned` | `"0"` | Bursty, only set if user mentions Logs Insights. |
| `numberOfCanaryRuns` | `"0"` | Synthetics is opt-in. |
| `numberOfMonthlyvisitors` | `"0"` | RUM is opt-in. |
| `numberOfRumEvents` | `"0"` | RUM is opt-in. |
| `PercentageOfRumEvents` | `"100"` | If user enables RUM but doesn't name a sampling rate, sample 100% (matches what CloudWatch RUM does on first enable). |
| `numberOfMobileVisitors` | `"0"` | Mobile RUM is opt-in. |
| `numberOfMobileEvents` | `"0"` | Mobile RUM is opt-in. |
| `percentageOfMobileRumEvents` | `"100"` | Match desktop RUM default. |
| `insightsRulesForCloudWatch` | `"0"` | Contributor Insights is opt-in. |
| `logEventsForCloudwatch` | `"0"` | Same. |
| `insightsRulesForDynamoDB` | `"0"` | Same. |
| `EventsForDynamoDB` | `"0"` | Same. |
| `numberOfLambdaFunctions` | `"0"` | Lambda Insights is opt-in. |
| `numberOfLambdaInvokes` | `"0"` | Same. |
| `numberOfvCPUs_Aurora` | `"0"` | Database Insights is opt-in (and Advanced mode is paid). |
| `numberOfACUs_AuroraServerless` | `"0"` | Same. |
| `numberOfACUs_AuroraLmitless` | `"0"` | Same. |

If the user gives a brief like "enable CloudWatch monitoring for our 20 EC2 instances, 50 GB logs/month, 10 alarms", set just those four fields and leave the rest at `"0"` / `"[ZERO_COST]"`.

## Verification

- Source: captured saveAs body at `captures/saveAs/per-service/amazonCloudWatch.json` (local capture, not in repo) (region `us-east-2`, every dimension exercised at value `"10"` except mobile events at `"70"` and mobile sampling at `"100"`). The captured `serviceCost.monthly` is **$222.05**.
- Rate SKUs above pulled live via `pricing_client.py --profile <your-profile> get-products --service-code AmazonCloudWatch --filter regionCode=us-east-2 …` against the listed `usagetype` values.
- Region tested via Pricing API: `us-east-2` / `US East (Ohio)`. For other regions, swap the `USE2-` prefix on each `usagetype` (`USE1-` Virginia, `USW2-` Oregon, `EUW1-` Ireland, etc.).
- **Not yet end-to-end reproduced** — the $222.05 figure requires the SPA's internal mobile-RUM-OTEL byte-per-event factor and an exact Database-Insights engine selection that the form doesn't expose. The shape and per-dimension rates above are individually verified; the aggregate is not byte-perfect against the capture.

Fields marked "verify before relying on this":
- **Dashboards** (`numberOfDashboards`) — flat rate $3.00/dashboard-month is from AWS public pricing pages; the Pricing API returns no SKU for `productFamily=Dashboard` in tested regions.
- **Mobile RUM payload sizing** (`numberOfMobileEvents` → OTEL GB) — the SPA's internal byte-per-event conversion is not Price-List-derived.
- **Lambda Insights cost path** — the calculator derives cost from CloudWatch Logs + metrics generated by Lambda Insights using internal multipliers that are not exposed via the Pricing API.
- **`numberOfvCPUs_Aurora`** — a single bucket covering RDS Provisioned and Aurora Provisioned across multiple engines; rate varies by engine, but the form picks one internally. Treat the per-engine selection as inferred.
- **`numberOfACUs_AuroraLmitless`** rate path — the Aurora Limitless ACU-hour rate exists in the Pricing API under `instanceConfigurationType=Limitless` but the calculator's selection logic was not exercised in the captured body.

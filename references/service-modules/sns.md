# SNS (`amazonSimpleNotificationService` group)

SNS is a **group** service: the line item has `subServices: [...]` rather than top-level `calculationComponents`. Each topic type (Standard / FIFO) is its own sub-service.

## Group-level header

```json
{
  "serviceCode":  "amazonSimpleNotificationService",
  "estimateFor":  "amazonSnsClassesGroup",
  "version":      "0.0.24",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Simple Notification Service (SNS)",
  "description":  null,
  "subServices":  [ ... see below ... ],
  "serviceCost":  { "monthly": <sum of subServices.serviceCost.monthly> },
  "configSummary": "<standard summary> <fifo summary>"
}
```

Only include the sub-services the user actually wants — Standard alone, FIFO alone, or both.

## subServices

### Standard topics (`standardTopics`)

```jsonc
{
  "serviceCode":  "standardTopics",
  "estimateFor":  "sns_t1",
  "version":      "0.0.64",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "simpleNotificationServiceSns_generated_23": {
      "value": [
        {"entryType": "INBOUND",  "value": "<TB>", "unit": "tb_month", "fromRegion": ""},
        {"entryType": "OUTBOUND", "value": "<TB>", "unit": "tb_month", "toRegion":   ""}
      ]
    },
    "numberOfRequests":                {"value": "<M>", "unit": "millionPerMonth"},
    "numberOfHTTPNotifications":       {"value": "<M>", "unit": "millionPerMonth"},
    "numberOfEmailNotifications":      {"value": "<M>", "unit": "millionPerMonth"},
    "numberOfSQSNotifications":        {"value": "<M>", "unit": "millionPerMonth"},
    "aws_Lambda":                      {"value": "<M>", "unit": "millionPerMonth"},
    "Amazon_Kinesis_Data_Firehose":    {"value": "<M>", "unit": "millionPerMonth"},
    "numberOfMobilePushNotifications": {"value": "<M>", "unit": "millionPerMonth"},
    "publishAndDeliveryMessageScanning":                      {"value": "<GB>", "unit": "gb|month"},
    "auditReporting":                                         {"value": "<GB>", "unit": "gb|month"},
    "The_amount_of_outbound_payload_data_scanned_per_month":  {"value": "<GB>", "unit": "gb|NA"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

Field names are literal. Several keys are auto-generated and **must be preserved character-for-character**:

- `simpleNotificationServiceSns_generated_23` — data-transfer block, mirrors the S3 DT shape
- `aws_Lambda`, `Amazon_Kinesis_Data_Firehose` — mixed casing and underscores
- `The_amount_of_outbound_payload_data_scanned_per_month` — sentence-cased, literal

See the open question in the **Verification** section about the `_23` suffix.

### FIFO topics (`fifoTopics`)

```jsonc
{
  "serviceCode":  "fifoTopics",
  "estimateFor":  "sns_t2",
  "version":      "0.0.44",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "Average_message_size":      {"value": "<KB>", "unit": "kb|NA"},
    "numberOfRequests":          {"value": "<M>",  "unit": "millionPerMonth"},
    "Number_of_subscriptions":   {"value": "<N>"},
    "retentionperiod":           {"value": "<days>", "unit": "day"},
    "The_amount_of_outbound_payload_data_scanned_per_month": {"value": "<GB>", "unit": "gb|NA"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

Preserve `Average_message_size`, `Number_of_subscriptions`, and `retentionperiod` (note the lowercase, no underscore in `retentionperiod`) exactly.

## Pricing API filters

ServiceCode for all SNS lookups: `AmazonSNS`. Use `--filter regionCode=<region>` everywhere. Filter by `group` for the cleanest single-SKU lookups (one SKU each).

| Dimension | Filter | us-east-2 rate |
|---|---|---|
| Standard publish API requests | `group=SNS-Requests-Tier1` | $0.50 per 1M (first 1M/mo free) |
| HTTP/HTTPS delivery           | `endpointType=HTTP` (productFamily=Message Delivery) | $0.06 per 100k = $0.60 per 1M (first 100k/mo free) |
| Email / Email-JSON delivery   | `endpointType=SMTP` | $2.00 per 100k (first 1,000/mo free) |
| SQS delivery                  | `endpointType=Amazon SQS` | $0 |
| Lambda delivery               | `endpointType=AWS Lambda` | $0 |
| Kinesis Firehose delivery     | `endpointType=Amazon Kinesis Data Firehose` | $0.19 per 1M |
| Mobile push delivery          | `endpointType=Apple Push Notification Service (APNS) - iOS` (or GCM/ADM/etc.) | $0.50 per 1M |
| Message scanning              | `group=SNS-MDP-Scanning` | $0.08 per GB |
| Audit reporting               | `group=SNS-MDP-AuditReporting` | $0.19 per GB |
| Standard payload filtering    | `group=SNS-Standard-Payload-MessageFiltering-Filter-Matched` / `-Filtered-Out` | $0.09 per GB |
| FIFO publish requests         | `group=SNS-FIFO-Requests` | $0.30 per 1M |
| FIFO publish payload          | `group=SNS-Publish-Payload` | $0.017 per GB |
| FIFO subscription messages    | `group=SNS-FIFO-Subscription-Messages` | $0.01 per 1M |
| FIFO subscription payload     | `group=SNS-FIFO-Subscription-Messages-Payload` | $0.001 per GB |
| FIFO archive processing       | `group=SNS-FIFO-ArchiveProcessing` | $0.10 per GB |
| FIFO storage                  | `group=SNS-FIFO-Storage` | $0.023 per GB-month |
| Data transfer in/out          | ServiceCode `AWSDataTransfer` (same shape as S3/EC2 DT) | tiered |

`get-attribute-values --service-code AmazonSNS --attribute group` enumerates the valid `group` strings.
`--attribute endpointType` enumerates delivery destinations.

## Multipliers / formula

### Standard topic

```
M = numberOfRequests.value                    (millions/mo)
H = numberOfHTTPNotifications.value
E = numberOfEmailNotifications.value
Q = numberOfSQSNotifications.value
L = aws_Lambda.value
F = Amazon_Kinesis_Data_Firehose.value
P = numberOfMobilePushNotifications.value
S = publishAndDeliveryMessageScanning.value   (GB)
A = auditReporting.value                       (GB)
O = The_amount_of_outbound_payload_data_scanned_per_month.value  (GB)

requestsCost     = M * 0.50                              # no free-tier subtraction in the SPA
httpCost         = max(0, H - 0.1) * 0.60                # 100k free per month
emailCost        = max(0, E*1_000_000 - 1000) * 0.00002  # 1000 free per month
sqsCost          = 0
lambdaCost       = 0
firehoseCost     = F * 0.19
mobilePushCost   = max(0, P - 1) * 0.50                  # 1M free per month
scanningCost     = S * 0.08
auditCost        = A * 0.19
outboundPayCost  = O * 0.09                              # standard filtering payload rate

standardMonthly  = sum of the above (+ data transfer, computed via the S3 DT formula)
```

The SPA does **not** apply the 1M free tier to `numberOfRequests` even though the AWS pricing page advertises it; the request line was billed flat at `$0.50 / M`. Match the SPA's behavior to reproduce the captured total.

### FIFO topic

```
M       = numberOfRequests.value                                          (millions/mo)
sub     = Number_of_subscriptions.value                                   (count)
kb      = Average_message_size.value                                      (KB)
days    = retentionperiod.value                                           (days)
O       = The_amount_of_outbound_payload_data_scanned_per_month.value     (GB)

publishedGB        = M * 1_000_000 * kb / 1_048_576           # ~ 1 GB per 262,144 msgs at 4 KB
subscriberMessages = M * sub                                  # millions
subscriberGB       = publishedGB * sub

fifoRequestCost      = M * 0.30
fifoPublishPayload   = publishedGB * 0.017
fifoSubMessageCost   = subscriberMessages * 0.01
fifoSubPayloadCost   = subscriberGB * 0.001
fifoArchiveProcCost  = publishedGB * 0.10
fifoStorageCost      = publishedGB * (days / 30) * 0.023
outboundPayloadCost  = O * 0.09

fifoMonthly = sum of the above
```

Round each sub-service total to two decimals before summing; the group total mirrors the S3 group pattern.

## configSummary template

```
Requests (<M> million per month), HTTP/HTTPS Notifications (<M> million per month), EMAIL/EMAIL-JSON Notifications (<M> million per month), SQS Notifications (<M> million per month), Amazon Web Services Lambda (<M> million per month), Amazon Kinesis Data Firehose (<M> million per month), Mobile Push Notifications (<M> million per month), Publish and Delivery Message Scanning (<GB> GB per Month), Audit Reporting (<GB> GB per Month), The amount of outbound payload data scanned per month (<GB> GB) Average message size (<KB> KB), Requests (<M> million per month), Number of subscriptions (<N>), Retention Period (<D> days), The amount of outbound payload data scanned per month (<GB> GB)
```

Note the **single space** (no comma) between the Standard-topic outbound-scanning clause and the FIFO `Average message size` clause — the SPA emits it that way; preserve it. Omit any clause whose dimension is zero only if the captured behavior allows; safest is to include all clauses with the user's values.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfRequests | "0" | Most workloads only price one delivery destination |
| numberOfHTTPNotifications | "0" | |
| numberOfEmailNotifications | "0" | |
| numberOfSQSNotifications | "0" | |
| aws_Lambda | "0" | |
| Amazon_Kinesis_Data_Firehose | "0" | |
| numberOfMobilePushNotifications | "0" | |
| publishAndDeliveryMessageScanning | "0" gb\|month | Scanning is opt-in |
| auditReporting | "0" gb\|month | |
| outbound payload scanned | "0" gb\|NA | |
| Average_message_size (FIFO) | "4" kb\|NA | AWS pricing-page default |
| Number_of_subscriptions (FIFO) | "1" | Single subscriber unless told otherwise |
| retentionperiod (FIFO) | "0" day | FIFO archive/retention is opt-in |
| Standard data-transfer block | INBOUND=0 / OUTBOUND=0 tb_month | Only price DT when the user calls it out |

If the user says "SNS topic" without specifying type, default to **Standard** only. Add FIFO when they say "ordered", "deduplicated", "FIFO", or call out subscriptions.

## Verification

- **Captured ground truth:** `/tmp/aws_calc_onboard/sns.json` (path was ephemeral; file lost — re-capture needed) — group `serviceCost.monthly = $231.20`, standard sub-service = $220.92, FIFO sub-service = $10.28, region us-east-2.
- **Inputs used:** every `millionPerMonth` and every `gb|month`/`gb|NA` field set to 10; FIFO avg message size 4 KB, 10 subscriptions, 10-day retention.
- **Reproduced standard ($220.92):** 10*0.50 (requests, no free tier applied) + (10M-100k)*$0.0000006 (HTTP) + (10M-1000)*$0.00002 (email) + 0 (SQS) + 0 (Lambda) + 10*0.19 (Firehose) + (10M-1M)*$5e-7 (mobile push) + 10*0.08 (scanning) + 10*0.19 (audit) + 10*0.09 (outbound-scanned) = 5.00 + 5.94 + 199.98 + 0 + 0 + 1.90 + 4.50 + 0.80 + 1.90 + 0.90 = **$220.92**.
- **FIFO published-GB divisor — corrected 2026-09-06 (recompute oracle).** The formula block above states `publishedGB = M * 1_000_000 * kb / 1_048_576`, i.e. **binary** KB→GiB. That divisor does not close this module's own capture: it gives 38.147 GB for 10M x 4 KB and a FIFO total of **$10.04**, against the captured **$10.28**. The **decimal** divisor (`/ 1_000_000`, giving exactly 40.0 GB) reproduces $10.287 ≈ the captured $10.28. The capture is ground truth, so `scripts/recompute_oracle.py` uses the decimal divisor and `tests/test_recompute_oracle.py` pins it. **Treat the `1_048_576` in the formula block as wrong** until a fresh capture says otherwise; the "≈ 40 GB" the reconciliation below uses is the correct number, not a rounding of 38.147.
- **Recompute-oracle reconciliation, 2026-09-06.** Both sub-service formulas were re-derived from `sns.json` (discovered via `standardTopics` / `fifoTopics` `mappingDefinitions`) and reproduce this module's captured totals to the cent: Standard **$220.92** (0.00%) and FIFO **$10.287** vs $10.28 (+0.07%). Two rate details the map settles: HTTP and email free bands **are** in the map as explicit $0 first tiers (`HTTP 0 to 100000`, `SMTP 0 to 1000`), so they need no special-casing; the **mobile-push 1M/month free band is not** — `sns.json` carries only the flat `$0.0000005` per-notification rate, so the oracle subtracts the 1M explicitly to match the capture and flags that it is doing so.
- **Reproduced FIFO ($10.28):** publishedGB = 10M * 4 KB ≈ 40 GB. 10*$0.30 (requests) + 40*$0.017 (publish payload) + (10*10)*$0.01 (sub messages) + (40*10)*$0.001 (sub payload) + 40*$0.10 (archive processing) + 40*(10/30)*$0.023 (storage) + 10*$0.09 (outbound-scanned) = 3.00 + 0.68 + 1.00 + 0.40 + 4.00 + 0.307 + 0.90 = **$10.287 ≈ $10.28**.
- **Group total:** 220.92 + 10.28 = $231.20 — matches.
- **Open question — `simpleNotificationServiceSns_generated_23`:** the `_23` suffix is almost certainly the SPA's auto-numbering of dynamic form fields (each instance increments a counter) and may differ across captures. Treat it as **probably environment-specific**: confirm the suffix before relying on this literal. If the SPA rejects the saved estimate, suspect this key first. The captured POST was accepted with `_23`, so it works at least sometimes.

  **Try the public catalog FIRST (before HAR capture).** Per `references/opaque-tokens.md`, the house rule is to first try the world-readable meteredUnitMaps catalog via `scripts/resolve_token.py`. Probe outcome (probed 2026-07-13):

  - `python3 scripts/resolve_token.py sns` → **HIT** (200; 37 regions, 34 friendly→token mappings). The catalog resolves SNS pricing SKUs (e.g. `"Amazon SNS API Requests"`, `"Amazon SNS Message Scanning per GB"`) to their 43-char `RegionlessRateCode` tokens — useful for pricing, but it does **not** contain the `simpleNotificationServiceSns_generated_23` key.
  - No match for `simpleNotificationServiceSns_generated_23` anywhere in the `sns` catalog.

  Reason: `_generated_N` is the SPA's **form-field identifier** (an auto-numbered form widget), not a `RegionlessRateCode` — a different token class the meteredUnitMaps catalog does not enumerate. So the catalog cannot resolve this suffix today; **capturing a fresh HAR remains the fallback** for confirming it. Try the catalog first anyway (it is cheap and it is the correct source for the pricing tokens), then fall back to HAR only for the `_generated_*` form-field suffix.
- **Mobile push free tier:** the Pricing API only surfaces the "thereafter" dimension for mobile push endpoints; the 1M-free-per-month tier is documented on the AWS pricing page and matches the captured math, but is not visible via the Price List API.
- **Standard requests free tier:** the SPA bills `numberOfRequests` flat at $0.50/M without subtracting the documented 1M monthly free tier (the free tier *is* present in the API SKU's `beginRange`/`endRange`). Mirror the SPA's behavior.

# Cross-module conventions (recompute-hazard classes)

Three families of field-encoding bugs recur across service modules and break the **SPA recompute** (share URL → "Update estimate"), not just the initial save. Consult this file before defining any percent, "millions", or free-tier field in a new or edited module. Every row cites the module it was derived from; do not add claims not present in a module.

## 1. Governing principle

**Mirror what the SPA computes on load, not what the AWS published pricing page says.** A saveAs body seeds `serviceCost`, but the SPA re-derives it from `calculationComponents` on "Update estimate". A field that merely *saves* correctly can still *recompute* to a wrong number if its encoding (literal-vs-fraction percent, value-in-millions, free-tier subtraction) disagrees with the SPA's math layer. Reconcile against a captured `serviceCost`, and where possible against a live-SPA recompute — see the two-tier vocabulary in `_template.md`.

## 2. Percent-field semantics

The trap: a "%" input is stored one way in `calculationComponents` (cc) and often rendered a *different* way in `configSummary`. cc is load-critical; get it wrong and recompute collapses the cost.

| Module | Field(s) | cc value | configSummary render | Evidence / note |
|---|---|---|---|---|
| backup.md | `annualGrowthOfPrimaryUsage`, `dailyChangeOfPrimaryUsage` | **Literal percent** (`"10"`=10%, `"3"`=3%); never the fraction `"0.1"`/`"0.03"` | Literal percent (`(10)`, `(3)`) | Recompute fix 2026-06: old fractional form read as 0.1%/0.03% ≈ zero → RDS $154.94→$1.64, S3 $48.6→~$25.86. Frags 49 (S3 512 GB→48.6) / 50 (RDS 2000 GB→154.94). Buggy captures show `(0.1)`/`(0.03)` in configSummary — that is the trap artifact, not correct. |
| drs.md | `avgChangeRateOfDisk`, `percentOfHigherPerformance` | **Integer percent** (`"5"`=5%, `"10"`=10%); SPA divides by 100 internally | **Fraction** (`(0.05)`, `(0.1)`) — deliberately split from cc | $216.04 round-trip verified. Reproduce the cc-integer / configSummary-fraction split exactly. |
| cloudwatch.md | `PercentageOfRumEvents`, `percentageOfMobileRumEvents` | **Literal percent** (`"10"`=10%, `"100"`=100%); formula applies `/100` | **Fraction** (web 10%→`0.1`, mobile 100%→`1`) | RUM cost = visitors × events × (pct/100) × rate. Sampling rate shown as 0–1 fraction in configSummary. |

Takeaway: cc stores the number the user typed into the "%" box (literal/integer percent) in every case above; the SPA does the `/100`. Divergence lives only in configSummary rendering (display-only, SPA rebuilds it). Never pre-divide the cc value.

## 3. Units secretly in millions

Query/request/event counts whose value is **already in millions** — multiply by 1e6 before applying the per-unit rate. The `unit` label does not reliably announce this: `millionPerMonth` does, but `perMonth` hides it.

| Module | Field(s) | Unit label | Meaning | Evidence |
|---|---|---|---|---|
| route53.md | `numberOfStandardQueries`, `numberOfLatencyBasedRoutingQueries`, `numberOfGeoDNSQueries`, `numberOfIPRoutingQueries`, `numberOfRecursiveAverageDNSQueries`, `numberOfFirewallDNSQueries` | `millionPerMonth` | Count in millions; SPA ×1e6 before per-query rate | Comment on cc; per-million rate tiers. |
| sns.md | `numberOfRequests`, `numberOfHTTPNotifications`, `numberOfEmailNotifications`, `numberOfSQSNotifications`, `aws_Lambda`, `Amazon_Kinesis_Data_Firehose`, `numberOfMobilePushNotifications` | `millionPerMonth` | Millions/month | configSummary: "`<M>` million per month". |
| sqs.md | `standardQueueRequests`, `fifoQueueRequests`, `fairQueueRequests` | **`perMonth`** (misleading) | Millions/month despite label | configSummary literally inserts "X million per month"; rates are per-million. |
| waf.md | `numberOfWebRequests` | **`perMonth`** (misleading) | Millions/month | `"10"` × $0.60/M = $6.00 matches observed. (Other WAF `perMonth` fields are true counts, not millions.) |
| cloudwatch.md | `logEventsForCloudwatch`, `EventsForDynamoDB` | **`perMonth`** (misleading) | Millions/month | configSummary: "10 million matched log events per month" for field value `"10"`. |

## 4. SPA free-tier behavior (applied vs ignored)

The SPA does **not** consistently apply AWS's published free tiers. Some it subtracts; most it ignores and bills from the first unit. Getting this backwards under-states or over-states the line.

> Caveat: each row is **single-capture evidence** unless noted otherwise — the observed behavior held in the one capture cited, and could differ in an edge case (e.g. a boundary count) or change if AWS updates the SPA.

| Module | Free tier | SPA behavior | Evidence |
|---|---|---|---|
| ecr.md | 100 GB/mo outbound data-transfer free tier | **Ignored** — bills full GB against tier rates. Global to the SPA's DT computation (S3/EC2 outbound too), not ECR-specific | 10 TB → $921.60 (full), not $912.60; total $922.60 reconciled. |
| guardduty.md | Malware-S3 1 GB scan + 1k scan-request slices; 30-day GuardDuty free trial | **Ignored** — bills from first unit; trial invisible | s3Data $0.09/GB, s3put $0.000215/event from unit 1. |
| dynamodb.md | 25 GB storage free tier | **Ignored** — storage billed flat $0.25/GB-Mo from first GB | `dynamoDBOnDemand` reconciled to the cent using flat storage (10 GB × $0.25 = $2.50, not $0). Two captures. |
| dynamodb.md | Streams 2.5M requests/mo free tier | **Applied** | `dynamoDBOnDemandStreams` captured $0 for 10 requests (below 2.5M band). |
| codepipeline.md | V1: first active pipeline per account free | **Applied** — subtract 1 from `numberOfPipelines`; only one region claims it (V2 minutes have no free tier) | 10 pipelines → $9 reconciled. Single-pipeline ($0) edge and multi-region handling **inferred, not round-tripped**. |
| cloudtrail.md | First trail copy of management + network-activity events | **Applied** (free) — network-activity treated like management events, though AWS docs price them from copy 1 | Module note; "that's the calculator's behavior; it may change." |
| kms.md | 20K symmetric requests/mo + AWS-managed CMK key storage | **Ignored** — charges from first request | Captured estimate bills from unit 1. |

## 5. Time constants (month length)

The month-to-hours/days factor is **not uniform** across services. Use the one the target module verified.

| Module(s) | Constant | Note |
|---|---|---|
| eks.md | **730 hours/month** | Applied consistently across every card (cluster, hybrid vCPU-hours, capabilities). |
| fargate.md | **730 hours/month = 30.4167 days/month** | "matches every other calculator module verified so far." |
| ebs.md | **730 hours** for volume duration; snapshot-frequency uses a **29.915 days/month** constant | `snapshotFrequency "59.83"` = 2 × 29.915 = "2x Daily". `durationOfInstanceRuns` defaults 730. |
| bedrock.md | **× 30 (30-day month)** — exception | Bedrock request volume uses `× 30`, unlike the 730-hour convention everywhere else. At captured $1.02 volume this can't be confirmed to the cent; if the SPA uses 30.42 instead, cost is off ~1.4%. |

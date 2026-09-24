# Amazon GuardDuty (`amazonGuardDuty`)

One line item covers every paid GuardDuty dimension exposed by the calculator: foundational CloudTrail / VPC Flow Log / DNS / S3 / EKS event analysis, runtime monitoring (EC2 / ECS-Fargate / EKS / Lambda / RDS / Aurora Serverless), and Malware Protection (EBS, EC2 AMI, S3 backup, S3 data + PUT).

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| All 17 documented cc dimensions at "10" (us-east-2) | capture-verified | captured saveAs (`/tmp/aws_calc_onboard/amazonGuardDuty.json`, lost) — $90.20 hand-total matches exactly |
| Foundational event analysis (CloudTrail / VPC Flow / DNS / S3 / EKS events) | capture-verified | same capture |
| Runtime monitoring vCPU/ACU dimensions (EC2, ECS-Fargate, EKS, Lambda, RDS, Aurora Serverless) | capture-verified | same capture |
| Malware Protection (EBS, EC2 AMI, S3 backup, S3 data + PUT) | capture-verified | same capture; the calculator skips the 1 GB free band |
| `aiDataEvents` (AI Protection) | inferred | form 0.0.77 definition (2026-09-06); Pricing API SKU not resolved — look the rate up before quoting |
| Other fields present in form 0.0.77 that no capture exercised | inferred | form 0.0.77 definition only |
| Foundational + S3 + ECS/Fargate Runtime Monitoring (`ecsInstances`, tiered $1.92 first 500 vCPU-months), eu-central-1 | recompute-verified | live SPA 2026-09-24, 42-line multi-account reference estimate (customer engagement, ID withheld); foundational dimensions also verified on two earlier estimates |
| Regions other than us-east-2 and eu-central-1 | inferred | per-region rates should be re-queried |

## Line-item header

```json
{
  "serviceCode":  "amazonGuardDuty",
  "estimateFor":  "template_0",
  "version":      "0.0.77",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon GuardDuty",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  // CloudTrail management events analyzed per month (count of events, not millions).
  "managementEventsAnalysis": {"value": "10", "unit": "perMonth"},

  // GB of VPC Flow Logs ingested + analyzed for EC2 sources per month.
  "vpcFlowLogs_EC2":          {"value": "10", "unit": "gb|month"},

  // GB of DNS query logs analyzed for EC2 sources per month.
  "dnsLogs_EC2":              {"value": "10", "unit": "gb|month"},

  // S3 data-plane events analyzed per month (count of events, not millions).
  "s3Events":                 {"value": "10", "unit": "perMonth"},

  // Kubernetes audit log events analyzed per month (count of events).
  "KubernetesEvents":         {"value": "10", "unit": "perMonth"},

  // Malware Protection — GB scanned on EBS volumes attached to suspicious EC2.
  "malwareDataScan":          {"value": "10", "unit": "gb|month"},

  // Malware Protection for S3 — total GB of S3 objects scanned per month.
  "s3Data":                   {"value": "10", "unit": "gb|month"},

  // Malware Protection for S3 — count of PUT requests monitored per month.
  // (Despite the "perMonth" unit label, this is raw request count.)
  "s3put":                    {"value": "10", "unit": "perMonth"},

  // On-demand Malware Protection — GB scanned from EBS snapshots per month.
  "ebsBackupDataScan":        {"value": "10", "unit": "gb|month"},

  // On-demand Malware Protection — GB scanned from EC2 AMIs per month.
  "ec2BackupDataScan":        {"value": "10", "unit": "gb|month"},

  // On-demand Malware Protection — GB scanned from S3 recovery points per month.
  "s3BackupDataScan":         {"value": "10", "unit": "gb|month"},

  // RDS Protection — provisioned RDS instance vCPUs monitored (vCPU-months).
  "vCPURDS":                  {"value": "10", "unit": "perMonth"},

  // RDS Protection — Aurora Serverless v2 ACUs monitored (ACU-months).
  "auroraServerless":         {"value": "10", "unit": "perMonth"},

  // Lambda Protection — GB of Lambda VPC network logs analyzed per month.
  "vpcFlowLogs_lambda":       {"value": "10", "unit": "gb|month"},

  // EKS Runtime Monitoring — vCPU-months of EKS worker nodes covered.
  "eksInstances":             {"value": "10", "unit": "perMonth"},

  // ECS/Fargate Runtime Monitoring — vCPU-months of Fargate tasks covered.
  "ecsInstances":             {"value": "10", "unit": "perMonth"},

  // EC2 Runtime Monitoring — vCPU-months of EC2 instances covered.
  "ec2Instances":             {"value": "10", "unit": "perMonth"}
}
```

All values are stringified numbers. Use `"0"` to disable a dimension cleanly. The three `*Instances` fields and `eksInstances` are **vCPU-months**, not instance counts — see "Ambiguity" below.

### Fields present in form 0.0.77 that no capture exercised — inferred, not capture-verified

```jsonc
{
  // AI Protection — GB of AI data events analyzed per month. Added in form 0.0.77.
  // Shape read from the form definition: subType fileSize,
  // defaultOption {size: "gb", frequency: "month"} → unit "gb|month". No form default.
  "aiDataEvents": {"value": "<GB>", "unit": "gb|month"}
}
```

Two reasons not to emit this without more work. **Its rate is unknown** — no Pricing API SKU has been resolved for GuardDuty AI Protection, so a line carrying it cannot be priced (see the `aiDataEvents` row in the filters table). And it is **region-gated**: the form only renders it where the `guardduty` metered-unit map carries `AquKJoDK1dc2lqKDfuB0bKsOqm6Syc7g-zViz94Oz2s`. Omit the key entirely rather than sending `"0"` when you are unsure the region has it.

## Pricing API filters

ServiceCode is `AmazonGuardDuty`. Every dimension is its own SKU keyed by `usagetype`; the prefix is region-specific (`USE2-` for us-east-2, `USE1-` for us-east-1, `EUW1-` for eu-west-1, etc.). Use `get-attribute-values --service-code AmazonGuardDuty --attribute group` to browse, and filter on `regionCode=<region>` + `usagetype=<prefix>-<feature>`. All rates below verified for `us-east-2`.

| Dimension (component field) | usagetype suffix | Unit | First-tier rate (us-east-2) |
|---|---|---|---|
| `managementEventsAnalysis` | `PaidEventsAnalyzed` | Events | $0.0000040 / event (flat) |
| `vpcFlowLogs_EC2`, `dnsLogs_EC2` | `PaidEventsAnalyzed-Bytes` | GB | $1.00 / GB (0–500 GB tier) |
| `s3Events` | `PaidS3DataEventsAnalyzed` | Events | $0.0000008 / event (0–500M tier) |
| `KubernetesEvents` | `PaidKubernetesAuditLogsAnalyzed` | Events | $0.0000016 / event (0–100M tier) |
| `malwareDataScan` | `PaidMalwareProtectionEBSDataScanned` | GB | $0.03 / GB |
| `s3Data` | `MalwareProtectionS3DataScanned` | GB | $0.09 / GB (calculator ignores the 1 GB free tier) |
| `s3put` | `MalwareProtectionS3ScanRequest` | Events | $0.000215 / event (calculator ignores the 1k free tier) |
| `ebsBackupDataScan` | `PaidOnDemandEBSSnapshotDataScanned` | GB | $0.05 / GB |
| `ec2BackupDataScan` | `PaidOnDemandEC2AMIDataScanned` | GB | $0.05 / GB |
| `s3BackupDataScan` | `PaidOnDemandS3RecoveryPointDataScanned` | GB | $0.05 / GB |
| `vCPURDS` | `PaidRDSvCPUMonitored` | vCPU-Months | $1.00 / vCPU-month |
| `auroraServerless` | `PaidRDSACUMonitored` | ACU-Months | $0.25 / ACU-month |
| `vpcFlowLogs_lambda` | `PaidLambdaNetworkLogsAnalyzed-Bytes` | GB | $1.00 / GB (0–500 GB tier) |
| `eksInstances` | `PaidEKSvCPUMonitored` | vCPU-Months | $1.50 / vCPU-month (0–500 tier) |
| `ecsInstances` | `PaidFargatevCPUMonitored` | vCPU-Months | $1.50 / vCPU-month (0–500 tier) |
| `ec2Instances` | `PaidEC2vCPUMonitored` | vCPU-Months | $1.50 / vCPU-month (0–500 tier) |
| `aiDataEvents` | **not yet resolved** | GB | **unknown — look up before quoting** (new in form 0.0.77; no Pricing API lookup has been run for GuardDuty AI Protection) |

Tiered SKUs (`vpcFlowLogs_*`, S3/EKS/EC2/Fargate, K8s, S3 events) drop sharply at higher volumes — walk the user's volume across the bands when it exceeds the first tier.

## Multipliers / formula

```
monthly_cloudtrail   = managementEventsAnalysis * 0.0000040
monthly_vpc_ec2      = sum_over_tiers(vpcFlowLogs_EC2 GB)              # tier 1: $1/GB
monthly_dns_ec2      = sum_over_tiers(dnsLogs_EC2 GB)                   # same SKU as VPC; tier 1: $1/GB
monthly_s3_events    = sum_over_tiers(s3Events events)                  # tier 1: $8e-7
monthly_k8s          = sum_over_tiers(KubernetesEvents events)          # tier 1: $1.6e-6
monthly_malware_ebs  = malwareDataScan * 0.03
monthly_malware_s3   = s3Data * 0.09 + s3put * 0.000215
monthly_md_ebs_snap  = ebsBackupDataScan * 0.05
monthly_md_ec2_ami   = ec2BackupDataScan * 0.05
monthly_md_s3_rp     = s3BackupDataScan * 0.05
monthly_rds          = vCPURDS * 1.00
monthly_aurora       = auroraServerless * 0.25
monthly_lambda       = sum_over_tiers(vpcFlowLogs_lambda GB)            # tier 1: $1/GB
monthly_eks          = sum_over_tiers(eksInstances vCPU-mo)             # tier 1: $1.50
monthly_ecs          = sum_over_tiers(ecsInstances vCPU-mo)             # tier 1: $1.50
monthly_ec2          = sum_over_tiers(ec2Instances vCPU-mo)             # tier 1: $1.50

serviceCost.monthly  = sum of the above
serviceCost.upfront  = 0
```

GuardDuty has no upfront and no commitment model. The calculator does **not** apply the published free-tier slices for the small-volume Malware S3 SKUs — bill from the first unit. The 30-day GuardDuty free trial is also invisible to the calculator.

## configSummary template

Match this exact phrasing so the SPA renders the line-item card normally. Only the bracketed `<N>` numbers should change:

```
AWS CloudTrail Management Event Analysis (<N> per month), EC2 VPC Flow Log Analysis (<N> GB per month), EC2 DNS Query Log Analysis (<N> GB per month), EBS Volume Data Scan Analysis (<N> GB per month), Total Size of S3 Objects scanned per month (<N> GB per month), Enter the amount of data scanned from EBS snapshots per month (<N> GB per month), Enter the amount of data scanned from EC2 AMI per month (<N> GB per month), Enter the amount of data scanned from S3 Recovery Point per month (<N> GB per month), RDS provisioned instance vCPU (<N> per month), Aurora Serverless v2 instances ACUs (<N> per month), Lambda VPC Flow Log Analysis (<N> GB per month)
```

(Note: the captured `configSummary` omits S3 events/PUT, Kubernetes events, and the three runtime-monitoring fields. Leave it that way — the SPA is happy as long as the `calculationComponents` block carries the real numbers.)

## Defaults

| Field | Default | Why |
|---|---|---|
| managementEventsAnalysis | "0" | Only set if user has CloudTrail volume to estimate |
| vpcFlowLogs_EC2 | "0" | Opt-in |
| dnsLogs_EC2 | "0" | Opt-in |
| s3Events | "0" | Opt-in S3 protection |
| KubernetesEvents | "0" | Opt-in EKS audit-log protection |
| malwareDataScan | "0" | Opt-in EBS Malware Protection |
| s3Data, s3put | "0" | Opt-in S3 Malware Protection |
| ebsBackupDataScan, ec2BackupDataScan, s3BackupDataScan | "0" | Opt-in on-demand malware scans |
| vCPURDS | "0" | Opt-in RDS Protection |
| auroraServerless | "0" | Opt-in Aurora Serverless protection |
| vpcFlowLogs_lambda | "0" | Opt-in Lambda Protection |
| eksInstances, ecsInstances, ec2Instances | "0" | Opt-in Runtime Monitoring |

If the user describes a workload class without precise numbers, populate just the relevant dimensions and zero the rest (e.g. an EKS-only estimate uses `KubernetesEvents` + `eksInstances`; a CloudTrail-only baseline uses `managementEventsAnalysis` + the three foundational log fields).

## Verification

Reproduced against the captured `serviceCost.monthly = $90.20` in `us-east-2` with every input field = `"10"`:

- VPC Flow EC2: 10 × $1.00 = **$10.00**
- DNS EC2: 10 × $1.00 = **$10.00**
- VPC Flow Lambda: 10 × $1.00 = **$10.00**
- RDS vCPU: 10 × $1.00 = **$10.00**
- Aurora Serverless ACU: 10 × $0.25 = **$2.50**
- EKS vCPU: 10 × $1.50 = **$15.00**
- ECS/Fargate vCPU: 10 × $1.50 = **$15.00**
- EC2 vCPU: 10 × $1.50 = **$15.00**
- Malware EBS: 10 × $0.03 = **$0.30**
- Malware S3 data: 10 × $0.09 = **$0.90**  (calculator skips the 1 GB free band)
- EBS snapshot scan: 10 × $0.05 = **$0.50**
- EC2 AMI scan: 10 × $0.05 = **$0.50**
- S3 recovery point scan: 10 × $0.05 = **$0.50**
- CloudTrail / S3 events / K8s events / S3 PUT: $0.00004 + $0.000008 + $0.000016 + $0.00215 ≈ **$0.00**

**Hand total: $90.20** — matches the captured value exactly. Captured shape: `/tmp/aws_calc_onboard/amazonGuardDuty.json` (path was ephemeral; file lost — re-capture needed).

- **Form 0.0.75 → 0.0.77 (2026-09-06).** Diffed against the live form definition (`data/amazonGuardDuty/en_US.json`, version `0.0.77`). Fields **added: `aiDataEvents`** (GuardDuty AI Protection — "AI Data Events Analyzed", subType `fileSize`, `gb|month`, region-gated on the `guardduty` metered-unit map); renamed: none; removed: none. All 17 previously documented cc keys are still present with the same ids. The new field is **inferred from the form definition, not capture-verified**, and its Pricing API SKU has not been resolved — do not quote an AI Protection line without looking the rate up first.
- The $90.20 hand-total above was computed before AI Protection existed and does not include it; it still reconciles for the 17 original dimensions.

## Ambiguity worth flagging before relying on this

- **`ec2Instances` / `ecsInstances` / `eksInstances` are vCPU-months, not instance counts.** The Pricing API SKU unit is `vCPU-Months` and the rates ($1.50/$0.75/$0.25 across the 500 / 5,000 vCPU tiers) match the published per-vCPU runtime monitoring fees. The calculator's UI labels these fields ambiguously, but the math only works as vCPU-months. When a user says "20 EC2 instances," multiply by the average vCPU/instance before populating.
- **`auroraServerless` unit is ACU-months.** SKU `PaidRDSACUMonitored` is priced at $0.25 per ACU-month flat. Treat the input value as monthly ACUs averaged over the month.
- **`s3put` "perMonth" unit is raw request count, not millions.** At $0.000215/request it contributes pennies even at 10k requests, but a user describing "10M PUTs" should enter `"10000000"`, not `"10"`.
- **`managementEventsAnalysis`, `s3Events`, `KubernetesEvents` are likewise raw event counts.** Same gotcha — quote enough zeros.
- The captured `configSummary` is incomplete (omits 6 of the 17 fields). It was captured against form 0.0.75 and has **not** been re-checked against 0.0.77 — which added an 18th field, so if AWS did fix the summary the current phrasing is already stale. Re-check on the next capture; if the summary changed, mirror the new phrasing.

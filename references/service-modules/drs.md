# AWS Elastic Disaster Recovery (`awsElasticDisasterRecovery`)

Covers AWS DRS replication charges plus the staging-area EBS volumes and EBS snapshots the service uses on the customer's behalf. Pricing is per replicating source server, plus the EBS storage that backs the staging disks and point-in-time snapshots in the target Region. Emit one line item per target Region the user is replicating into.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| `awsDrsRecoveryReplication` with `ebsVolumeType: "auto"` + `ebsVolumeCostType: "avg"` (us-east-2) | capture-verified | `captures/saveAs/per-service/awsElasticDisasterRecovery.json` — $216.04 reproduced exactly |
| `subServices` as a JSON array `[template1, template2]` | capture-verified | live-SPA load-parse check 2026-06; object form breaks estimate load |
| `awsDrsDrill` (`template2`) `!HIDDEN` placeholder shape, monthly 0 | capture-verified | same capture |
| Write-rate classification bands (3X..21X gp3/sc1 split) | capture-verified | `awsDrsRecoveryReplication/en_US.json` 0.0.37 math ops; closes the $216.04 total |
| DRS replication + EBS gp3/sc1/Magnetic/snapshot rates (us-east-2) | capture-verified | `pricing_client.py get-products` for the listed usagetypes |
| `ebsVolumeType` other than `auto` (gp3 / gp2 / st1 explicit) | inferred | math documented in the en_US template; no captured round-trip |
| `ebsVolumeCostType` `min` / `max` | inferred | same — documented, not round-tripped |
| Cross-region replication data transfer | inferred | no field on the form — build a separate EC2 DT line |
| Replication-server EC2 hours | inferred | excluded from the DRS line per the SPA's own help text |
| Regions other than us-east-2 | inferred | assumed one SKU per region with a swapped usagetype prefix |

This service is modeled as a **group** in the calculator (`estimateFor: "awsDRSGroups"`) with two nested `subServices`:

- `awsDrsRecoveryReplication` (`estimateFor: "template1"`) — the only one with paid components. DRS replication hours + EBS staging + EBS snapshots all roll up here.
- `awsDrsDrill` (`estimateFor: "template2"`) — drill / recovery launches. The SPA emits this with `!HIDDEN` placeholder values and `monthly: 0`; reproduce the same placeholder shape so the SPA doesn't reject the body.

> **`subServices` MUST be a JSON array, not an object.** (Recompute fix 2026-06, live-SPA verified.) Like every other group-shaped service in this skill (S3, VPC, ELB, AWS Backup), the `subServices` value is a **list** of the two subService objects, in order `[template1, template2]` — NOT a dict keyed by sub-service name. Encoding it as an object (e.g. `{"awsDrsRecoveryReplication": {...}, "awsDrsDrill": {...}}`) is accepted by the save endpoint but makes the SPA fail to parse the **entire** estimate on load ("Unable to parse the data using legacy methods") — every line item disappears and the total renders `$0`, not just the DRS line. See the container shape below.

The EC2 replication servers (default t3.small instances, `disks / 15` rounded up) are **not** charged through this line item. The SPA tells the user to add an EC2 estimate separately, and the captured saveAs body does not include any replication-server cost — see Verification.

## Line-item header (group wrapper)

```json
{
  "serviceCode":  "awsElasticDisasterRecovery",
  "estimateFor":  "awsDRSGroups",
  "version":      "0.0.17",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Elastic Disaster Recovery",
  "description":  null
}
```

The group's `serviceCost.monthly` equals the sum of its two subService `serviceCost.monthly` values. In practice only `template1` is non-zero.

## subServices (verified shape)

The full line-item value object wraps the two subServices in a **`subServices` array** and carries its own summed `serviceCost`:

```jsonc
{
  "serviceCode": "awsElasticDisasterRecovery",
  "estimateFor": "awsDRSGroups",
  "version": "0.0.17",
  "region": "<code>", "regionName": "<display>",
  "serviceName": "AWS Elastic Disaster Recovery",
  "description": null,
  "subServices": [            // <-- ARRAY, ordered [template1, template2]. NOT an object/dict.
    { /* awsDrsRecoveryReplication (template1) — see below */ },
    { /* awsDrsDrill (template2) — see below */ }
  ],
  "serviceCost": { "monthly": <sum of subServices>, "upfront": 0 },
  "configSummary": "..."
}
```

### `awsDrsRecoveryReplication` (template1) — required, carries all cost

```jsonc
{
  "estimateFor":  "template1",
  "serviceCode":  "awsDrsRecoveryReplication",
  "version":      "0.0.37",
  "region":       "<code>",
  "description":  null,
  "serviceCost":  { "monthly": <computed> },
  "calculationComponents": {
    // --- Replication ---
    "numberOnPremiseServerReplicated": {"value": "10"},   // source servers, count
    "numberOfDisk":                    {"value": "10"},   // total disks across all servers
    "avgChangeRateOfDisk":             {"value": "5"},    // PERCENT as integer-ish string. "5" means 5%/day.
                                                          // SPA divides by 100 before applying to bytes math.
    "storageAmount": {"value": "100", "unit": "gb|NA"},   // total GB across all disks and servers

    // --- EBS staging volumes ---
    "ebsVolumeType":     {"value": "auto"},               // see "ebsVolumeType values" below
    "ebsVolumeCostType": {"value": "avg"},                // avg | min | max  (only meaningful when ebsVolumeType == "auto")
    "percentOfHigherPerformance": {"value": "10"},        // PERCENT as integer string. "10" means 10% of disks are >= 125 GB
                                                          // and get the auto-selected / chosen volume type. Remainder
                                                          // (<125 GB) is priced as EBS Magnetic (standard).

    // --- EBS snapshots ---
    "numberOfRetentionDays": {"value": "7"}               // days of point-in-time history retained
  }
}
```

All numeric values are stringified. `avgChangeRateOfDisk` and `percentOfHigherPerformance` are percent inputs — the captured body stores the **integer percent**, and the SPA's math layer divides by 100 internally when computing GB-deltas and high-perf storage share.

### `awsDrsDrill` (template2) — required placeholder, monthly always 0

```jsonc
{
  "estimateFor":  "template2",
  "serviceCode":  "awsDrsDrill",
  "version":      "0.0.17",
  "region":       "<code>",
  "description":  null,
  "serviceCost":  { "monthly": 0 },
  "calculationComponents": {
    "DRS_Hidden_Input1": {"value": "!HIDDEN"},
    "DRS_Hidden_Input2": {"value": "!HIDDEN"}
  }
}
```

Emit this subService verbatim — the captured body always includes it with `!HIDDEN` placeholders. Drill / recovery instance launch costs surface in the calculator only when the user adds a separate EC2 line item.

### `ebsVolumeType` values

| User intent | calculationComponents.ebsVolumeType.value |
|---|---|
| Let DRS pick gp3 vs sc1 dynamically by write rate (recommended, calculator default) | `"auto"` |
| Force gp3 for all disks ≥ 125 GB | `"Storage General Purpose gp3 GB Mo"` |
| Force gp2 for all disks ≥ 125 GB | `"Storage General Purpose GB Mo"` |
| Force st1 (throughput-optimized HDD) for all disks ≥ 125 GB | `"Storage Throughput Optimized HDD GB Mo"` |

`ebsVolumeCostType` only applies when `ebsVolumeType == "auto"`:

| Mode | Meaning |
|---|---|
| `"avg"` | Dynamic gp3/sc1 split based on average write rate (calculator's default — see math below). |
| `"min"` | Disks ≥125 GB are all sc1; assumes lowest cost. |
| `"max"` | Disks ≥125 GB are all gp3; assumes highest cost. |

Disks <125 GB are always priced as EBS Magnetic (standard) regardless of `ebsVolumeType` / `ebsVolumeCostType`.

## Pricing API filters

Four SKU lookups per Region. Pricing API ServiceCode for DRS itself is `AWSElasticDisasterRecovery`; the staging-volume and snapshot SKUs come from `AmazonEC2`. The `usagetype` prefix changes by Region (`USE2-` for us-east-2, `USE1-` for us-east-1, `EUW1-` for eu-west-1, etc.) — enumerate with `get-attribute-values --service-code AWSElasticDisasterRecovery --attribute usagetype`.

### DRS replication (per source server per hour)

```
--service-code AWSElasticDisasterRecovery
--filter regionCode=<region>
--filter usagetype=<REGIONPREFIX>-DRS-Replication
```

Single OnDemand SKU with one priceDimension. In us-east-2 the rate is **$0.028 / Replication-hour** (SKU `PVX69GGW8WY67FUE`). The DRS Pricing API exposes only this one productFamily (`Server DR`) and one replicationType (`Normal`) — there is no separate point-in-time-recovery SKU. PITR retention beyond the included window is billed through the EBS Snapshot SKU below.

### EBS staging volumes — gp3

```
--service-code AmazonEC2
--filter regionCode=<region>
--filter productFamily=Storage
--filter volumeApiName=gp3
```

Single `GB-Mo` priceDimension. In us-east-2: **$0.08 / GB-Mo**.

### EBS staging volumes — sc1 (Cold HDD)

```
--service-code AmazonEC2
--filter regionCode=<region>
--filter productFamily=Storage
--filter volumeApiName=sc1
```

Single `GB-Mo` priceDimension. In us-east-2: **$0.015 / GB-Mo**.

### EBS staging volumes — Magnetic (used for the <125 GB share)

```
--service-code AmazonEC2
--filter regionCode=<region>
--filter productFamily=Storage
--filter volumeApiName=standard
```

Single `GB-Mo` priceDimension. In us-east-2: **$0.05 / GB-Mo**. The calculator's "standard EBS volume" mapping refers to this `volumeApiName=standard` (previous-generation Magnetic) SKU, not gp2 — confirmed against the captured saveAs body's $216.04 round-trip.

### EBS snapshot storage

```
--service-code AmazonEC2
--filter regionCode=<region>
--filter productFamily="Storage Snapshot"
--filter usagetype=<REGIONPREFIX>-EBS:SnapshotUsage
```

Single `GB-Mo` priceDimension at the standard tier. In us-east-2: **$0.05 / GB-Mo** (SKU `EZ8T7N34G3H5Y4ER`). Do not use the `SnapshotArchiveStorage` SKU ($0.0125) — the calculator models hot snapshots only.

### Replication-server EC2 hours

Not surfaced as a SKU on this line item. The calculator displays `roundedNumberOfReplicationServer = ceil(numberOfDisk / 15)` t3.small instances as an informational hint, then directs the user to build a separate EC2 line item for the cost. Do not roll the EC2 hourly rate into `serviceCost.monthly` for this module — doing so would diverge from what the SPA recomputes on load.

### Cross-region replication data transfer

Not modeled by this calculator template at all. If the user is replicating cross-region and needs DT cost, build a separate EC2 line item with `dataTransferForEC2` populated. **verify before relying on this** — DRS in cross-region scenarios uses inter-region data transfer SKUs (`AWSDataTransfer`, fromLocation=<source-region>, toLocation=<target-region>) but the calculator surfaces no field for it under `awsDrsRecoveryReplication`.

## Multipliers / formula

Convert percent inputs to fractions first:

```
change_rate_fraction = float(avgChangeRateOfDisk)       / 100      # "5"  -> 0.05
high_perf_fraction   = float(percentOfHigherPerformance) / 100      # "10" -> 0.10
```

Then:

```
# 1. DRS replication
total_drs_charge = numberOnPremiseServerReplicated * drs_hourly_rate * 730

# 2. Auto-mode write-rate classification (only used when ebsVolumeType == "auto" AND ebsVolumeCostType == "avg")
daily_change_gb     = storageAmount * change_rate_fraction
daily_change_mb     = daily_change_gb * 1024
second_change_mb    = daily_change_mb / 86400                       # average write rate, MB/s
avg_disk_size_tb    = (storageAmount / 1024) / numberOfDisk         # avg disk size in TB
# Thresholds (MB/s per 1 TB scaled by avg disk size in TB):
# 3X, 6X, 9X, 12X, 15X, 18X, 21X => bands of (gp3%, sc1%):
#  [-inf, 0]      -> (  0%, 100%)
#  (0,  3X]       -> (12.5%, 87.5%)
#  (3X, 6X]       -> ( 25%,  75%)
#  (6X, 9X]       -> (37.5%, 62.5%)
#  (9X, 12X]      -> ( 50%,  50%)
#  (12X, 15X]     -> (62.5%, 37.5%)
#  (15X, 18X]     -> ( 75%,  25%)
#  (18X, 21X]     -> (87.5%, 12.5%)
#  (21X, inf)     -> (100%,   0%)
gp3_share, sc1_share = classify(second_change_mb, avg_disk_size_tb)

total_high_perf_gb = storageAmount * high_perf_fraction             # disks >= 125 GB

if ebsVolumeType == "auto" and ebsVolumeCostType == "avg":
    high_perf_cost = total_high_perf_gb * gp3_share * ebs_gp3_rate \
                   + total_high_perf_gb * sc1_share * ebs_sc1_rate
elif ebsVolumeType == "auto" and ebsVolumeCostType == "min":
    high_perf_cost = total_high_perf_gb * ebs_sc1_rate              # all sc1
elif ebsVolumeType == "auto" and ebsVolumeCostType == "max":
    high_perf_cost = total_high_perf_gb * ebs_gp3_rate              # all gp3
else:
    # explicit gp3 / gp2 / st1 selection
    high_perf_cost = total_high_perf_gb * chosen_volume_rate

# 3. <125 GB share is always EBS Magnetic
low_cost_fraction = 1 - high_perf_fraction
total_magnetic_cost = ebs_magnetic_rate * storageAmount * low_cost_fraction

total_ebs_volume_cost = high_perf_cost + total_magnetic_cost

# 4. Snapshots — base full copy + per-day delta over retention window
snapshots_new_data  = storageAmount * change_rate_fraction * numberOfRetentionDays
total_snapshots_gb  = storageAmount + snapshots_new_data
ebs_snapshots_cost  = ebs_snapshot_rate * total_snapshots_gb

total_ebs_cost = total_ebs_volume_cost + ebs_snapshots_cost

# 5. Roll up
template1.serviceCost.monthly = round(total_drs_charge + total_ebs_cost, 2)
template2.serviceCost.monthly = 0
group.serviceCost.monthly     = template1.serviceCost.monthly + 0

serviceCost.upfront = 0   # no upfront / RI / SP model for DRS
```

The snapshot model is a one-shot full-copy baseline plus incremental deltas held for the retention window — not a sliding-window approximation. With change rate 0% the snapshots line item still costs `storageAmount * snapshot_rate` because of the baseline.

## configSummary template

Match the captured phrasing exactly — the SPA reads this for the line-item card title. Note the **two spaces** between "retention period" and the opening paren around the days value:

```
EBS volume type (<volume type display>), Number of days selected for EBS snapshot retention period  (<N>), Cost type (<cost type display>), Number of source servers replicated per month (<N>), Number of disks (<N>), Average change rate on disks per day (<change_rate_fraction>), Storage on all disks and all servers (<N> GB), Percentage of source disks equal or larger than 125 GB (<high_perf_fraction>)
```

Volume type display strings:

| ebsVolumeType.value | configSummary fragment |
|---|---|
| `auto` | `Auto volume type selection` |
| `Storage General Purpose gp3 GB Mo` | `Faster, general purpose SSD (gp3)` |
| `Storage General Purpose GB Mo` | `Faster, general purpose SSD (gp2)` |
| `Storage Throughput Optimized HDD GB Mo` | `Lower cost, throughput optimized HDD (st1)` |

Cost type display strings (only emitted when `ebsVolumeType == "auto"`):

| ebsVolumeCostType.value | configSummary fragment |
|---|---|
| `avg` | `Estimated cost - General purpose SSD (gp3) & Cold HDD (sc1) & Magnetic (previous generation)` |
| `min` | `Minimum cost - Cold HDD (sc1) & Magnetic (previous generation)` |
| `max` | `Maximum cost - General purpose SSD (gp3) & Magnetic (previous generation)` |

The captured body emits `Average change rate ... (0.05)` and `Percentage ... (0.1)` — i.e. the configSummary text shows the **fraction**, even though `calculationComponents.value` stores the **integer percent** (`"5"` and `"10"`). Reproduce that split.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOnPremiseServerReplicated | "1" | Single-server pilot is the common entry point; bump on user input |
| numberOfDisk | "1" | One disk per server is the simplest case; rises with server count in practice |
| avgChangeRateOfDisk | "5" | 5%/day matches the AWS DRS pricing page worked example |
| storageAmount | "100" (`unit: "gb|NA"`) | Modest baseline |
| ebsVolumeType | "auto" | Calculator default; lets DRS pick gp3/sc1 |
| ebsVolumeCostType | "avg" | Most realistic when ebsVolumeType is auto |
| percentOfHigherPerformance | "10" | 10% of disks ≥125 GB is a conservative typical share; user should override when known |
| numberOfRetentionDays | "7" | Template's hard-coded `defaultValue: 7` from the en_US config |
| awsDrsDrill subService | always emitted with `!HIDDEN` placeholders, `monthly: 0` | Matches captured shape; absence may break the SPA's group hydration |

If the user just says "we want DRS for N servers" with no further detail, the right answer is the DRS replication charge plus the defaults above — call out every defaulted field in the breakdown so they can correct.

## Verification

Reproduced the captured `group.serviceCost.monthly = $216.04` exactly in `us-east-2` from these inputs (the values in the captured saveAs body):

- 10 source servers, 10 disks, 100 GB total, 5%/day change rate, 7-day retention, 10% of disks ≥125 GB, `ebsVolumeType: auto`, `ebsVolumeCostType: avg`
- DRS replication: 10 × $0.028/hr × 730 hrs = **$204.40**
- Write-rate classification: SecondChangeMB = 5×1024/86400 = 0.0593 MB/s; avgDiskSizeInTB = (100/1024)/10 = 0.00977 TB → 6X = 0.0586, 9X = 0.0879, so usage falls in the (6X, 9X] band → 37.5% gp3, 62.5% sc1
- EBS staging (≥125 GB share = 10 GB): 10 × 0.375 × $0.08 + 10 × 0.625 × $0.015 = $0.30 + $0.094 = **$0.394**
- EBS Magnetic (<125 GB share = 90 GB): 90 × $0.05 = **$4.500**
- EBS snapshots: (100 + 100 × 0.05 × 7) × $0.05 = 135 × $0.05 = **$6.750**
- Total EBS: $0.394 + $4.500 + $6.750 = **$11.644** (rounds to $11.64)
- Total: $204.40 + $11.64 = **$216.04** — exact match.

**Ground truth files**:

- Captured saveAs body: `captures/saveAs/per-service/awsElasticDisasterRecovery.json` (local capture, not in repo)
- Service template (en_US definition with the SPA's verbatim math operations): extracted from `captures/calculator.aws_new_2.har`, response for `https://d1qsjq9pzbk1k6.cloudfront.net/data/awsDrsRecoveryReplication/en_US.json` (version `0.0.37`)
- DRS replication rate verified via `pricing_client.py get-products --service-code AWSElasticDisasterRecovery --filter regionCode=us-east-2 --filter usagetype=USE2-DRS-Replication` on the date this module was authored
- EBS gp3 / sc1 / Magnetic / Snapshot rates verified via the corresponding `AmazonEC2` `get-products` queries

**Inferred — verify before relying on this**:

- **Cross-region replication data transfer**: the calculator template defines no field for inter-region DT, even though DRS routinely replicates from on-prem or another Region into the target. If the user's brief implies cross-region DT, build a separate EC2 line item rather than inflating this one.
- **Replication-server EC2 hours**: explicitly excluded from the DRS line item per the SPA's own help text. End-to-end estimates that need replication-server cost must add a t3.small EC2 line item with quantity `ceil(numberOfDisk / 15)`.
- **`ebsVolumeType` values other than `auto`** (gp3 / gp2 / st1 explicit): the math path is documented in the en_US template, but the captured saveAs body only exercises the `auto`+`avg` combination. End-to-end round-trip for explicit volume choices is not yet verified.
- **`ebsVolumeCostType` values `min` and `max`**: same caveat — math is documented, not round-trip-verified against a captured saveAs body.
- **Non-`us-east-2` Regions**: usagetype prefix changes per Region (`USE1-`, `EUW1-`, etc.); the per-Region DRS replication rate should be queried per estimate. Rates outside us-east-2 are inferred to follow the same one-SKU-per-Region pattern.

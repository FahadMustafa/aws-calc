# EFS (`amazonEFS`)

Covers Amazon Elastic File System: Standard storage plus Infrequent Access and Archive lifecycle tiers, with read/write data-transfer charges and Elastic Throughput. Single flat line item — no group/subServices wrapper.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| Regional (multi-AZ) EFS with Elastic Throughput + IA and Archive lifecycle (us-east-2) | capture-verified | `captures/saveAs/per-service/amazonEFS.json` (local capture) — round-trips at $25.94 |
| Storage / lifecycle / Elastic Throughput / Provisioned Throughput rates (us-east-2) | capture-verified | `pricing_client.py get-products` for the listed EFS SKUs |
| Formula total vs the captured $25.94 (~$0.30 delta) | inferred | likely rounding plus the Percentage fields feeding transition writes — unresolved |
| Split logic between `Percentage_of_data_*` and the explicit `_Tiering` / `_Read` GB fields | inferred | both appear in the capture; interaction undocumented in the bundle |
| `throughputModeSS` tokens for Bursting and Provisioned | inferred | only the Elastic token is captured and the others are not enumerable from the bundle |
| `provisionedThroughputSS` field name | inferred | taken from EFS console terminology, not a capture |
| One Zone storage-class field names (e.g. `oneZoneStandardStorageSize`) | inferred | the captured estimate is Regional only |
| EFS Replication (cross-region) and AWS Backup for EFS | inferred | not represented in the captured body — model separately |

## Line-item header

```json
{
  "serviceCode":  "amazonEFS",
  "estimateFor":  "elasticFileSystem",
  "version":      "0.0.76",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Elastic File System (EFS)",
  "description":  null
}
```

Values pulled from `captures/saveAs/per-service/amazonEFS.json` (local capture, not in repo).

## calculationComponents (verified shape)

```jsonc
{
  "throughputModeSS": {                                              // throughput mode token (opaque hash)
    "value": "pPg1vmtASUb_DcOGFyxPNa8abU3NDsNcdbBc06f_K_U"           // captured Elastic Throughput token — see note below
  },
  "standardStorageSize": {                                           // total provisioned capacity, GB
    "unit": "gb|NA",
    "value": "100"
  },

  // --- Infrequent Access tier ---
  "Infrequent_Access_storage_Percentage_of_data_that_is_accessed_multiple_times_within_a_few_months": {
    "value": "10"                                                    // percent (0-100) of total capacity expected in IA
  },
  "Infrequent_Access_Tiering": {                                     // GB transitioned into IA per month
    "unit": "gb|NA",
    "value": "10"
  },
  "Infrequent_Access_Read": {                                        // GB read from IA per month
    "unit": "gb|NA",
    "value": "10"
  },

  // --- Archive tier ---
  "Archive_storage_Percentage_of_data_that_is_accessed_once_a_year": {
    "value": "10"                                                    // percent (0-100) of total capacity expected in Archive
  },
  "Archive_Access_Tiering": {                                        // GB transitioned into Archive per month
    "unit": "gb|NA",
    "value": "10"
  },
  "Archive_Access_Read": {                                           // GB read from Archive per month
    "unit": "gb|NA",
    "value": "10"
  },

  // --- Elastic Throughput data-transfer (only when throughputModeSS = Elastic) ---
  "elasticThroughputReadDataInputSS": {
    "unit": "gb|month",
    "value": "10"
  },
  "elasticThroughputWriteDataInputSS": {
    "unit": "gb|month",
    "value": "10"
  }
}
```

### Throughput-mode token (`throughputModeSS.value`)

The SPA stores the throughput mode as a hashed opaque token rather than a plain string. The captured value `pPg1vmtASUb_DcOGFyxPNa8abU3NDsNcdbBc06f_K_U` corresponds to **Elastic Throughput** in the capture. The Bursting and Provisioned tokens were not in the captured body and are not enumerable from the bundle in plain text — **verify before relying on this**. To produce a Bursting or Provisioned estimate, capture a fresh HAR with that mode selected and copy the token from `calculationComponents.throughputModeSS.value`.

When `throughputModeSS` is Bursting, omit `elasticThroughputReadDataInputSS` / `elasticThroughputWriteDataInputSS` and the IA-ET pricing (charged read/write per GB) becomes the standard IA per-GB read/write rate instead. When Provisioned, add a `provisionedThroughputSS` field (MiBps) — name inferred, **verify before relying on this**.

## Pricing API filters

All filters use `--service-code AmazonEFS` and `--filter regionCode=<region>`. Each filter combination below returns a single OnDemand `priceDimension`.

### Standard storage (per GB-month)

```
--service-code AmazonEFS
--filter regionCode=<region>
--filter "storageClass=General Purpose"
```

`usagetype` ends in `-TimedStorage-ByteHrs`. Unit: `GB-Mo`. Drives `standardStorageSize` after IA / Archive percentages are deducted.

### Infrequent Access storage (per GB-month, Bursting/Provisioned modes)

```
--service-code AmazonEFS
--filter regionCode=<region>
--filter "storageClass=Infrequent Access"
```

Returns three SKUs: one for `IATimedStorage-ByteHrs` (storage), plus `IADataAccess-Bytes` with `accessType=Read` and `accessType=Write` (per-GB request charges). Use the storage SKU for the IA portion of `standardStorageSize`, and the access SKUs for `Infrequent_Access_Read` / `Infrequent_Access_Tiering` when throughput mode is Bursting or Provisioned.

### Infrequent Access storage with Elastic Throughput (per GB-month)

```
--service-code AmazonEFS
--filter regionCode=<region>
--filter "storageClass=Infrequent Access-ET"
```

`usagetype` ends in `-IATimedStorage-ET-ByteHrs`. Used when `throughputModeSS` is Elastic — the per-GB-mo IA storage rate is lower with Elastic Throughput because access is charged separately via the ETDataAccess SKUs below.

### Elastic Throughput data-access (per GB read/write)

```
--service-code AmazonEFS
--filter regionCode=<region>
--filter "usagetype=<USE2|USW2|...>-ETDataAccess-Bytes"
```

Returns two SKUs (`accessType=Read` and `accessType=Write`). Drives `elasticThroughputReadDataInputSS` and `elasticThroughputWriteDataInputSS`. Use `get-attribute-values --attribute usagetype` to find the right per-region prefix (`USE2`, `USW2`, `EUW1`, ...).

### Archive storage and access

```
--service-code AmazonEFS
--filter regionCode=<region>
--filter "storageClass=Archive"
```

Returns three SKUs:
- `ArchiveTimedStorage-ByteHrs` — per GB-Mo storage rate for the Archive portion of `standardStorageSize`
- `ArchiveDataAccess-Bytes` with `accessType=Read` — drives `Archive_Access_Read`
- `ArchiveDataAccess-Bytes` with `accessType=Write` — drives `Archive_Access_Tiering`

### One Zone storage classes

```
--service-code AmazonEFS
--filter regionCode=<region>
--filter "storageClass=One Zone-General Purpose"        # One Zone Standard
--filter "storageClass=One Zone-Infrequent Access"      # One Zone IA
```

One Zone uses separate `calculationComponents` field names (e.g. `oneZoneStandardStorageSize`) — **verify before relying on this**; the captured body is Regional (multi-AZ) only.

### Provisioned Throughput (per MiBps-month)

```
--service-code AmazonEFS
--filter regionCode=<region>
--filter "productFamily=Provisioned Throughput"
--filter "throughputClass=Provisioned"
```

Unit: `MiBps-Mo`. The companion `Included` SKU (`throughputClass=Included`) is $0 and represents bandwidth that ships free with Standard storage; only the delta above included throughput is billable. Cross-reference the captured `provisionedThroughputSS` field name with a fresh HAR — **verify before relying on this**.

## Multipliers / formula

```
# Total provisioned capacity is split across tiers by the SPA, driven by the
# two "Percentage_of_data..." fields. The remainder stays in Standard.
ia_gb         = standardStorageSize * (ia_percent / 100)
archive_gb    = standardStorageSize * (archive_percent / 100)
standard_gb   = standardStorageSize - ia_gb - archive_gb

# Storage charges (per GB-Mo)
monthly_std    = standard_gb * standard_gb_mo_rate
monthly_ia     = ia_gb       * ia_gb_mo_rate          # use -ET- SKU when throughput mode is Elastic
monthly_arch   = archive_gb  * archive_gb_mo_rate

# Lifecycle / access charges (per GB)
monthly_ia_tier   = Infrequent_Access_Tiering  * ia_write_per_gb_rate    # transition writes
monthly_ia_read   = Infrequent_Access_Read     * ia_read_per_gb_rate
monthly_arch_tier = Archive_Access_Tiering     * archive_write_per_gb_rate
monthly_arch_read = Archive_Access_Read        * archive_read_per_gb_rate

# Elastic Throughput data transferred (only when throughputModeSS = Elastic)
monthly_et_read   = elasticThroughputReadDataInputSS  * et_read_per_gb_rate
monthly_et_write  = elasticThroughputWriteDataInputSS * et_write_per_gb_rate

# Provisioned Throughput (only when throughputModeSS = Provisioned)
monthly_pt        = max(0, provisioned_mibps - included_mibps) * 6.00   # us-east-2 rate

serviceCost.monthly = sum of all applicable lines above
serviceCost.upfront = 0
```

EFS has no upfront / reserved pricing — `serviceCost.upfront` is always `0`.

The captured estimate (`standardStorageSize=100`, all percentages and tier GBs = `10`, Elastic Throughput, us-east-2) recomputes to roughly `$25.6` using the formula above; the captured `serviceCost.monthly` is `$25.94`. The ~$0.30 delta is likely SPA rounding plus the "Percentage" fields feeding into transition-write volume in addition to the explicit `_Tiering` GB inputs — **verify before relying on the exact split**.

## configSummary template

Match the captured phrasing exactly. Only emit clauses for fields the user actually set (omit the rest):

```
Desired Storage Capacity (<N> GB per month), Infrequent Access Tiering (<N> GB per month), Infrequent Access Read (<N> GB per month), Archive Access Tiering (<N> GB per month), Archive Access Read (<N> GB per month), Read Data Transferred (<N> GB per month), Write Data Transferred (<N> GB per month)
```

For Provisioned Throughput, add: `Provisioned Throughput (<N> MiBps)` — **verify before relying on this**.

## Defaults

| Field | Default | Why |
|---|---|---|
| throughputModeSS | Elastic (captured token) | Matches the captured working body; Elastic is AWS's recommended default for new file systems |
| standardStorageSize | 100 GB | Modest baseline; user should specify |
| Infrequent_Access_storage_Percentage_... | 0 | No IA tiering unless user opts in |
| Infrequent_Access_Tiering | 0 | No IA writes |
| Infrequent_Access_Read | 0 | No IA reads |
| Archive_storage_Percentage_... | 0 | No Archive tiering unless user opts in |
| Archive_Access_Tiering | 0 | No Archive writes |
| Archive_Access_Read | 0 | No Archive reads |
| elasticThroughputReadDataInputSS | 0 | No traffic assumed; user should specify |
| elasticThroughputWriteDataInputSS | 0 | No traffic assumed; user should specify |

When a quantity field defaults to `0`, set `value: "0"` (string) and keep the `unit` key — do not omit the field. The captured body always includes every key.

## Verification

- Ground truth: `captures/saveAs/per-service/amazonEFS.json` (extracted from `captures/calculator.aws.har` / `_new.har` / `_new_2.har` via `extract_saveas.py`).
- Verified end-to-end: Regional (multi-AZ) EFS, Elastic Throughput, us-east-2, 100 GB total with 10 GB / 10% IA + 10 GB / 10% Archive lifecycle, 10 GB ET read + 10 GB ET write per month — round-trips with `serviceCost.monthly = 25.94`.
- Pricing API SKU coverage confirmed for us-east-2: Standard ($0.30/GB-Mo), IA-ET ($0.016/GB-Mo), Archive ($0.008/GB-Mo), IA read/write ($0.01/GB), Archive read/write ($0.03/GB), ET read ($0.03/GB), ET write ($0.06/GB), Provisioned Throughput ($6.00/MiBps-Mo).

**Inferred / not yet verified — mark "verify before relying on this":**

- The exact split logic the SPA uses between the `Percentage_of_data_...` fields and the explicit `_Tiering` / `_Read` GB fields. Both appear in the captured body simultaneously; their interaction is not documented in the bundle.
- The `throughputModeSS` token values for Bursting and Provisioned modes — only the Elastic token is captured.
- Provisioned Throughput field name (`provisionedThroughputSS` is inferred from EFS console terminology, not captured).
- One Zone storage-class field names (e.g. `oneZoneStandardStorageSize`) — the captured estimate is Regional only.
- Cross-region replication line items (EFS Replication is billed separately and is not represented in the captured body).
- Backup / AWS Backup for EFS charges — not in scope for this module; route to a separate AWS Backup module when one exists.

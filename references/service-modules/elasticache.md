# ElastiCache (`amazonElastiCache`)

Covers ElastiCache node-based deployments (Redis OSS / Valkey / Memcached) and ElastiCache Serverless in a single line item. The captured form exposes three columnar sub-forms — `columnFormIPM` (primary cluster), `columnFormIPMDT` (a second cluster, typically the data-tiered / replica variant), and `columnFormIPM_dsp` (Serverless / "design point" cluster) — plus four scalar "average usage" fields used to estimate Serverless ECPUs and data transfer.

> Redis Enterprise Cloud on AWS is a Marketplace product priced separately; it is **not** modelled by this `serviceCode`. Don't try to route Redis Enterprise briefs through this module — say so and offer to skip or capture a HAR.

## Line-item header

```json
{
  "serviceCode":  "amazonElastiCache",
  "estimateFor":  "amazonElastiCache",
  "version":      "0.0.87",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon ElastiCache",
  "description":  null
}
```

`estimateFor`, `version`, and `serviceName` taken verbatim from `captures/saveAs/per-service/amazonElastiCache.json`.

## calculationComponents (verified shape)

```jsonc
{
  // Scalar usage drivers — feed the Serverless ECPU / data-transfer/storage math.
  // Numbers are stored as strings; "AvgCacheDataSize" is GB, "AvgDataTransfer" is KB per request.
  "AvgCacheDataSize":     {"value": "100"},                  // GB (legacy field)
  "AvgCacheDataSize_v2":  {"value": "100"},                  // GB (current field; mirror the legacy one)
  "AvgDataTransfer":      {"value": "100"},                  // KB per request (legacy)
  "AvgDataTransfer_v2":   {"value": "100"},                  // KB per request (current)

  // Opaque engine token. Captured value below corresponds to "Redis OSS" — the only
  // value verified end-to-end. The other tokens (Valkey / Memcached / Redis Enterprise)
  // are emitted by the bundle from the same dropdown but their opaque ids have NOT been
  // captured; mark them "verify before relying on this" if you need them.
  "EngineType": {
    "value": "x4dSskWC2UA5R5dVtIkM0EjZJQKU02zll08quzox15U"  // Redis OSS
  },

  // Primary node-based cluster (one row per distinct config). Push extra rows for
  // mixed clusters (e.g. one row for the primaries, one for the replicas if the user
  // wants them sized differently — but normally a single row with Number of Nodes covers it).
  "columnFormIPM": {
    "value": [
      {
        "Cache Engine":      {"value": "Redis"},             // Redis | Valkey | Memcached
        "Instance Family":   {"value": "Standard"},          // Standard | Memory optimized | Network optimized
        "Instance Type":     {"value": "cache.m5.xlarge"},
        "Number of Nodes":   {"value": "2"},                 // primaries + replicas total, as string
        "TermType":          {"value": "OnDemand"},          // OnDemand | Reserved-1yr-No-Upfront | ...
        "undefined": {                                       // utilization (key is literally "undefined")
          "value": {
            "selectedId": "%Utilized/Month",
            "unit":       "100"                              // percent as string
          }
        }
      }
    ]
  },

  // Second node-based cluster (data-tiered / cross-AZ replica tier in the captured body).
  // Same row shape as columnFormIPM. Set to a single empty-style row if the user has only
  // one cluster — DO NOT delete the key; the SPA expects it to exist.
  "columnFormIPMDT": {
    "value": [
      {
        "Cache Engine":      {"value": "Redis"},
        "Instance Family":   {"value": "Memory optimized"},
        "Instance Type":     {"value": "cache.r6gd.12xlarge"},
        "Number of Nodes":   {"value": "10"},
        "TermType":           {"value": "OnDemand"},
        "undefined": {
          "value": {
            "selectedId": "%Utilized/Month",
            "unit":       "100"
          }
        }
      }
    ]
  },

  // ElastiCache Serverless / "design-point" sub-cluster. The captured row carries only
  // Cache Engine + TermType; the actual ECPU and data-storage values come from
  // processingUnitCount_v2 and AvgCacheDataSize_v2. Leave as a single row; omit the
  // extra fields the calculator's node columns expect — see "verify" note below.
  "columnFormIPM_dsp": {
    "value": [
      {
        "Cache Engine": {"value": "Redis"},
        "TermType":     {"value": "OnDemand"}
      }
    ]
  },

  // Serverless request rate (ECPUs/sec). Value is requests/sec; the SPA multiplies by
  // 730*3600 and the per-engine ECPU rate. unit is literal "perSecond".
  "processingUnitCount_v2": {
    "unit":  "perSecond",
    "value": "100"
  }
}
```

### TermType string values

For the node-based sub-forms (`columnFormIPM`, `columnFormIPMDT`) the captured `TermType` is the literal `"OnDemand"` — the only value verified end-to-end here. Reserved Cache Node forms are emitted by the same dropdown, but **their encoding has NOT been seen in a captured ElastiCache saveAs body.**

> **Do NOT emit a Reserved ElastiCache line as a packed `TermType` string.** The single packed form `"Reserved-1yr-No-Upfront-Standard"` (and its `-Partial-Upfront-` / `-All-Upfront-` / `-3yr-` variants) is **likely WRONG**. The sibling `aurora-postgres.md` proved that exact packed pattern collapses Reserved lines to ~15% of stored on "Update estimate" (instance cost drops out, only storage/IO survive — e.g. $2600.26 → $404.61); `rds-sqlserver.md` proved the same packed string silently recomputes to $0.00. Both forms only round-trip Reserved pricing when it is split into three sibling row fields: `TermType: "Reserved"` + `LeaseContractLength` (`"1yr"`/`"3yr"`) + `PurchaseOption` (`"No Upfront"`/`"Partial Upfront"`/`"All Upfront"`). Whether ElastiCache's form uses that same three-field shape is **UNVERIFIED** — no capture exists either way.

**Instruction: refuse the Reserved line, or capture a HAR first.** Until a Reserved ElastiCache saveAs body is captured and recompute-validated (drive the SPA's "Update estimate" per `SKILL.md` step 7, or capture a fresh Reserved HAR), do not emit a Reserved node line. Fall back to `TermType: "OnDemand"` or tell the user a Reserved-RI capture is needed. Do not copy the packed-string pattern from any module — it is the known-broken shape on the sibling forms. On-Demand lines are unaffected.

### EngineType opaque tokens

| Engine UI label | EngineType.value | Status |
|---|---|---|
| Redis OSS | `x4dSskWC2UA5R5dVtIkM0EjZJQKU02zll08quzox15U` | Verified (captured) |
| Valkey | `3N-kN93Pj_EqF8T10vg8iOBwAqooXN7Z4emJZ0zY8i0` | **Inferred from the form definition (0.0.87), not capture-verified** |
| Memcache | `x4dSskWC2UA5R5dVtIkM0EjZJQKU02zll08quzox15U` | **Inferred from the form definition (0.0.87), not capture-verified.** The live dropdown gives Memcache the **same** option id as Redis OSS — so `EngineType` alone does not distinguish the two. Do not treat a round-tripping Memcache line as proof it priced as Memcache |
| Redis Enterprise | not an option in form 0.0.87 | Marketplace — refuse |

The live 0.0.87 dropdown has exactly three options (Valkey / Redis OSS / Memcache) with `defaultDropDownItem` = the Redis OSS token. Selecting Valkey also changes which scalar is live: `AvgCacheDataSize_v2` is hidden and the otherwise-hidden `AvgCacheDataSize_nonval_v2` takes over. This is read from the form definition and is **not capture-verified** — capture a Valkey HAR before emitting one.

## Pricing API filters

### Node-based On-Demand (cache.* node-hour)

```
--service-code AmazonElastiCache
--filter productFamily="Cache Instance"
--filter regionCode=<region>
--filter instanceType=<cache.m5.xlarge|cache.r6gd.12xlarge|...>
--filter cacheEngine=<Redis|Valkey|Memcached>
```

Pick the SKU whose `attributes.locationType == "AWS Region"` (skip `AWS Outposts` SKUs and the `ExtendedSupport*` SKUs unless the user explicitly asked for either). The SKU has one `OnDemand` rate in `Hrs`; `price_per_unit` is the per-node hourly rate.

For the Memory optimized family with data tiering (`cache.r6gd.*`), AWS publishes a single per-node-hour rate that already bakes in the SSD tier — no separate storage charge to add. (The captured `serviceCost.monthly = $87 106.81` includes the `processingUnitCount_v2` and `AvgCacheDataSize_v2` contributions; the raw node-hours alone come out to about $68 767/month for the captured config, so the remainder is Serverless ECPU + data storage. See "verification" below.)

### Reserved Cache Nodes (1yr / 3yr, No / Partial / All Upfront, Standard offering only)

Same filters as On-Demand. The returned SKU also carries `Reserved` terms keyed by `LeaseContractLength` (`1yr`/`3yr`), `PurchaseOption` (`No Upfront`/`Partial Upfront`/`All Upfront`), and `OfferingClass=standard`. ElastiCache does **not** offer the Convertible class.

Each Reserved term has two priceDimensions:
- one in `Hrs` — recurring hourly charge (multiply by 730)
- one in `Quantity` — upfront one-time charge (zero for No Upfront; the entire term cost for All Upfront)

### Snapshot / backup storage (over the free allocation)

```
--service-code AmazonElastiCache
--filter productFamily="Storage Snapshot"
--filter regionCode=<region>
--filter cacheEngine=<Redis|Valkey>
```

Single OnDemand `GB-Mo` priceDimension (typically $0.085/GB-mo). The free allocation is one snapshot's worth of node memory per cluster; budget snapshot cost only for retained snapshots beyond that.

### ElastiCache Serverless — ECPU + data storage + serverless backup

```
--service-code AmazonElastiCache
--filter productFamily="ElastiCache Serverless"
--filter regionCode=<region>
--filter cacheEngine=<Redis|Valkey|Memcached>
```

Returns three SKUs per engine, distinguishable by `usagetype` suffix:
- `*ElastiCacheProcessingUnits:<engine>` — per-ECPU rate (unit `ElastiCacheProcessingUnit`, e.g. $0.0034 per million Redis ECPUs)
- `*CachedData:<engine>` — per-GB-hour data-storage rate (unit `GB-Hours`, e.g. $0.125 GB-hr for Memcached, $0.084 for Valkey)
- `*BackupUsage:<engine>` — per-GB-month serverless snapshot storage (unit `GB-months`)

### Cross-AZ data transfer (replication)

ElastiCache cross-AZ replication uses the standard `AWSDataTransfer` SKUs:

```
--service-code AWSDataTransfer
--filter fromLocation=<regionName>
--filter transferType=InterAZ-In  # or InterAZ-Out
```

There is no dedicated calculationComponents field for this in the captured body — it appears to be inferred by the SPA from `AvgDataTransfer_v2` (KB per request) × the Serverless request rate × 2 (in+out). **Verify before relying on this** if cross-AZ cost dominates the estimate.

## Multipliers / formula

Let:
- `H = 730` (hours per month)
- For each row in `columnFormIPM` and `columnFormIPMDT`:
  - `nodes = int(Number of Nodes)`
  - `u    = int(undefined.value.unit) / 100`
  - `rate = on-demand $/hr` (or Reserved Hrs for an RI term)
  - `up   = Reserved Quantity` (upfront, only for Partial/All Upfront; 0 otherwise)

```
node_monthly_per_row   = rate * H * nodes * u
node_upfront_per_row   = up * nodes
nodes_monthly          = sum over rows of node_monthly_per_row
nodes_upfront          = sum over rows of node_upfront_per_row
```

> **Serverless math is best-effort and not reconciled — handle with care.** In the captured estimate the Serverless drivers (`processingUnitCount_v2`, `AvgCacheDataSize_v2`, `AvgDataTransfer_v2`) account for ~$18,339/mo — about **21% of the $87,106.81 total** — and that residual does **not** decompose cleanly into the published ECPU / data-storage / cross-AZ rates (the two node clusters alone are ~$68,767/mo). So any estimate that populates the Serverless scalars rests on an unverified path. **Keep all Serverless scalar fields at `"0"` unless the user explicitly asks for ElastiCache Serverless.** When they do: compute with the formula below, but mark the line best-effort, recompute-validate the share URL, and prefer to capture a Serverless-only HAR before quoting a large Serverless workload.

For Serverless (`columnFormIPM_dsp` + the scalar fields):

```
ecpu_per_sec           = int(processingUnitCount_v2.value)
ecpu_per_month         = ecpu_per_sec * 3600 * H
ecpu_monthly           = ecpu_per_month * ecpu_rate_per_unit          # price_per_unit is per single ECPU

storage_gb             = float(AvgCacheDataSize_v2.value)
data_storage_monthly   = storage_gb * data_storage_gb_hr * H

serverless_dt_monthly  = ecpu_per_sec * H * 3600 \                    # requests/month
                         * float(AvgDataTransfer_v2.value) / 1024 / 1024 \  # GB per request
                         * cross_az_per_gb * 2                          # cross-AZ billed in+out (see "Verify" note); UNVERIFIED
```

Snapshot cost (rough):

```
snapshot_monthly = max(0, retained_snap_gb - free_alloc_gb) * snap_per_gb_month
```

```
serviceCost.monthly = nodes_monthly + ecpu_monthly + data_storage_monthly +
                      serverless_dt_monthly + snapshot_monthly
serviceCost.upfront = nodes_upfront                                    # RI Partial/All Upfront totals
```

## configSummary template

Match the captured phrasing — the SPA renders this verbatim on the card. The captured value concatenates a per-row segment for each populated columnar sub-form, in this exact order: `columnFormIPM_dsp` (Serverless / design point) row → `columnFormIPM` row → `columnFormIPMDT` row → scalar fields. Commas separate every field; some labels intentionally repeat (the calculator literally re-emits "Cache Engine (Redis)" once per row).

```
Engine (Redis OSS), Instance type (<columnFormIPM.Instance Type>), Cache Engine (<columnFormIPM.Cache Engine>), Nodes (<columnFormIPM.Number of Nodes>), Utilization (On-Demand only) (<columnFormIPM.undefined.unit> %Utilized/Month), Cache Node Type (<columnFormIPM.Instance Family>), Pricing strategy (<columnFormIPM.TermType>), Cache Engine (<columnFormIPM_dsp.Cache Engine>), Pricing strategy (<columnFormIPM_dsp.TermType>), Nodes (<columnFormIPMDT.Number of Nodes>), Instance type (<columnFormIPMDT.Instance Type>), Utilization (On-Demand only) (<columnFormIPMDT.undefined.unit> %Utilized/Month), Cache Engine (<columnFormIPMDT.Cache Engine>), Cache Node Type (<columnFormIPMDT.Instance Family>), Pricing strategy (<columnFormIPMDT.TermType>), Average cache data size (in GB) (<AvgCacheDataSize>), Average data transferred per request [KBs] (<AvgDataTransfer>), Average cache data size (in GB) (<AvgCacheDataSize_v2>), Average simple request rate (<processingUnitCount_v2.value> per second), Average data transferred per request [KBs] (<AvgDataTransfer_v2>)
```

If the user's brief only mentions a single node-based cluster, populate `columnFormIPM` with the user's row and leave `columnFormIPMDT` as a single low-impact row (e.g. `Number of Nodes: "0"`) — the SPA tolerates a zero-node row in the second slot. The `_dsp` row must always exist with at least `Cache Engine` and `TermType`. **Verify before relying on this** in production briefs that omit the second cluster — easiest sanity check is to load the resulting share URL and confirm the calculator renders the card without an "incomplete configuration" warning.

## Defaults

| Field | Default | Why |
|---|---|---|
| EngineType | `x4dSskWC2UA5R5dVtIkM0EjZJQKU02zll08quzox15U` (Redis OSS) | Most common ElastiCache choice and the only engine token verified end-to-end |
| Cache Engine (each row) | `Redis` | Matches the Redis OSS engine selection above |
| Instance Family | `Standard` | Cheapest baseline; flag in breakdown for memory-heavy workloads |
| Instance Type (`columnFormIPM`) | `cache.m5.large` | Modest baseline node |
| Number of Nodes (`columnFormIPM`) | `"2"` | One primary + one replica (Multi-AZ default) |
| Utilization (`undefined.unit`) | `"100"` | Full utilization |
| TermType | `OnDemand` | No commitment risk |
| `columnFormIPMDT` row | single row with `Number of Nodes: "0"` | Required to keep the SPA happy without modelling a second cluster |
| `columnFormIPM_dsp` row | single row with `Cache Engine: "Redis"`, `TermType: "OnDemand"` | Serverless slot must exist; zero usage if the scalar fields are 0 |
| AvgCacheDataSize / AvgCacheDataSize_v2 | `"0"` | No Serverless data unless asked |
| AvgDataTransfer / AvgDataTransfer_v2 | `"0"` | No Serverless DT unless asked |
| processingUnitCount_v2 | `{"unit": "perSecond", "value": "0"}` | No Serverless requests unless asked |

When the user asks for "ElastiCache Serverless" specifically, flip the defaults: zero `columnFormIPM*` rows and populate `processingUnitCount_v2`, `AvgCacheDataSize_v2`, `AvgDataTransfer_v2` from their brief.

## Verification

**Captured ground truth**: `captures/saveAs/per-service/amazonElastiCache.json` — Redis OSS in `us-east-2` with two clusters (2× `cache.m5.xlarge` Standard On-Demand + 10× `cache.r6gd.12xlarge` Memory optimized On-Demand), Serverless scalars at 100 GB / 100 KB / 100 req-sec, recorded `serviceCost.monthly = 87106.81` / `upfront = 0`. The capture lives in `captures/saveAs/per-service/` which was sliced out of the full HAR (`captures/calculator.aws.har`, `captures/calculator.aws_new.har`).

**Verified**:
- Top-level header (`serviceCode`, `estimateFor`, `version`, `serviceName`) — straight from the capture.
- `calculationComponents` field names, nesting, and value types — straight from the capture.
- Node-hour Pricing API filter combo (`AmazonElastiCache` + `productFamily=Cache Instance` + `instanceType` + `cacheEngine` + `regionCode`) — resolves to the expected SKU with sensible On-Demand and Reserved rates for `cache.m5.xlarge` and `cache.r6gd.12xlarge` in `us-east-2`.
- Snapshot / Serverless ECPU / Serverless storage / Serverless backup SKU shapes — resolved via Pricing API and units confirmed.

**Inferred and not yet round-tripped — `verify before relying on this`**:
- `EngineType.value` opaque tokens for Valkey, Memcached, and Redis Enterprise. Only the Redis OSS token is captured.
- `TermType` string values for Reserved Cache Nodes (`Reserved-1yr-No-Upfront-Standard` etc.) — pattern is borrowed from the RDS module; capture an RI HAR before quoting.
- Single-cluster shape: how the SPA reacts when `columnFormIPMDT` is left as a zero-node placeholder row. Captured body always carries two real rows.
- Empty Serverless shape: how the SPA renders the card when `processingUnitCount_v2.value = "0"`. Captured body always carries `"100"`.
- Cross-AZ replication math — the captured `serviceCost.monthly` ($87 106.81) does not decompose cleanly into the published On-Demand node-hour rates alone (the two clusters alone come to ~$68 767/month), so the residual ~$18 339/month is presumed to be Serverless ECPU + data storage + cross-AZ DT computed from `AvgCacheDataSize_v2` / `AvgDataTransfer_v2` / `processingUnitCount_v2`. Exact formula not confirmed; treat the Serverless math above as best-effort and re-verify against the share-URL render.
- Reserved Cache Node upfront-vs-recurring split is documented from the Pricing API response shape but not from a captured Reserved saveAs.

- **Form 0.0.81 → 0.0.87 (2026-09-06).** Diffed the documented cc keys against the live form definition (`data/amazonElastiCache/en_US.json`, version `0.0.87`). Every documented key still exists: `EngineType`, `AvgCacheDataSize`, `AvgCacheDataSize_v2`, `AvgDataTransfer`, `AvgDataTransfer_v2`, `processingUnitCount_v2`, `columnFormIPM`, `columnFormIPMDT`, `columnFormIPM_dsp`. **No cc-relevant change**: fields added: none, renamed: none, removed: none.
- Four live input ids are *not* cc keys in this module and should stay that way: `Alert` and `dt_bodyText` are display-only, and `AvgCacheDataSize_nonval` / `processingUnitCount` / `AvgDataTransfer` / `AvgCacheDataSize` all carry `isDisabled: "true"` in 0.0.87 — they are read-only mirrors the form renders under a different engine or metered-unit condition, not user inputs. The one exception worth knowing about is `AvgCacheDataSize_nonval_v2`, which is *not* disabled and is the field the form shows in place of `AvgCacheDataSize_v2` when the engine is Valkey. Read from the form definition; **not capture-verified**.
- `EngineType` option ids for Valkey and Memcache were read out of the same file and filled into the token table above (Memcache shares the Redis OSS id). Still **inferred, not capture-verified** — the Serverless caveat and the Reserved-`TermType` refusal above are unchanged by this bump.

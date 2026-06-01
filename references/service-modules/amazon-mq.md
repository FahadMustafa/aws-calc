# Amazon MQ (`amazonMQ`)

`serviceCode` is `amazonMQ`. Amazon MQ has multiple form templates selected by the `estimateFor` value; this module covers four configurations with different confidence levels. The "opaque token" problem this module previously had is resolved — the SPA's public pricing catalog at `calculator.aws/pricing/2.0/meteredUnitMaps/mq/USD/current/mq.json` contains the full friendly-key → `RegionlessRateCode` mapping for every (engine, mode, instance type) combination, and that `RegionlessRateCode` IS the opaque token used in cc. See §Opaque token resolution below.

## Coverage matrix

| Path | `estimateFor` | Confidence | Anchor |
|---|---|---|---|
| RabbitMQ Cluster (Multi-AZ) | `rabbitMQBroker` | **Verified** end-to-end from HAR | `captures/saveAs/per-service/amazonMQ.json` |
| ActiveMQ Single Instance | `singleInstanceBroker` | **Inferred** from `captures/bundle.js` form + catalog token table — quoteable | bundle.js + mq.json catalog |
| ActiveMQ Active/Standby | `activeInstanceBroker` | **Inferred** from `captures/bundle.js` form + catalog token table — quoteable | bundle.js + mq.json catalog |
| RabbitMQ Single Instance | `rabbitMQBroker` (likely; not yet HAR-verified) | **Inferred** from mq.json catalog (RabbitMQ Single Instance tokens present for m5.large/xlarge/2xlarge/4xlarge + t3.micro) — flag in breakdown | mq.json catalog |

When the user's brief is ambiguous (e.g. "Amazon MQ broker, m5.large"), ask which engine (ActiveMQ vs RabbitMQ) and which deployment mode (single / active-standby / cluster) — engine + mode determines which template, which token series, and which rate row in the catalog.

## Opaque token resolution

Three cc fields across MQ paths carry 43-char URL-safe-base64 tokens (`rabbitmqInstanceTypeClustered` for RabbitMQ Cluster; potentially the analogous fields for RabbitMQ Single Instance once its form is HAR-captured). These tokens are NOT secret — they are simply `RegionlessRateCode` values from `mq.json`. The friendly key in that catalog encodes engine + mode + instance type as a single string.

```
# Resolve a token from the catalog (Python):
from urllib.request import Request, urlopen
import gzip, json
req = Request(
  "https://calculator.aws/pricing/2.0/meteredUnitMaps/mq/USD/current/mq.json",
  headers={"Accept-Encoding": "gzip"})
raw = urlopen(req).read()
catalog = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
# Walk regions to find the friendly key (region-independent token):
for region_data in catalog["regions"].values():
    for friendly_key, rec in region_data.items():
        if " " in friendly_key and friendly_key == "RabbitMQ Active Standby mq m5.large":
            print(rec["RegionlessRateCode"])  # -> 5hcZU6WguRUktrgs8rMw8I50JgkU3TyzOOdhtsRRjXs
            break
```

Or use the helper:
```
python3 scripts/resolve_token.py mq --friendly "RabbitMQ Active Standby mq m5.large"
python3 scripts/resolve_token.py mq --dump-friendly       # print all known friendly→token mappings
```

The full friendly→token table (region-independent), as of the catalog snapshot embedded with this module:

| Friendly key | Token |
|---|---|
| `Active Standby mq t2.micro` | `kfxZ0YaiRoHs7pML7IWMBWDLefTTKVdqZUmyOtGJoMg` |
| `Active Standby mq t3.micro` | `npxP4jMuDPI0Tsa33ciplHdXcReZI2smOX69b1Lg6C4` |
| `Active Standby mq m4.large` | `SLebDRjZkpP_bjXHPXfEmPQiI4NudlvtieaZhTyDODU` |
| `Active Standby mq m5.large` | `7lVtnGTGLw_MCxTFas-0CZbLqyBXbwYqww8u7D2jAuo` |
| `Active Standby mq m5.xlarge` | `uf168aXfjL6-aRynoV2NlgtBV7ylSjUNPr5T_qbQecY` |
| `Active Standby mq m5.2xlarge` | `szEa9FzeZ2rVziGW0DE8PENkqHUNUqXDx3WQsLQ74Og` |
| `Active Standby mq m5.4xlarge` | `avUaVtodKfdIrt83yUrbRnlaOFydLtxyaUc_qSgP5jU` |
| `Single Instance mq t2.micro` | `xgy1w0xhhksiyvrKXO6-2UQQynDmqJafzIh8kqhD214` |
| `Single Instance mq t3.micro` | `7TrHec2r24mxInPR-Bprm45ubxZ-3Ran19DAA_H7ftA` |
| `Single Instance mq m4.large` | `i3UuD2-5BN8zq0Wfa2ljDCKbHPVmig3PlLq4CZx3v08` |
| `Single Instance mq m5.large` | `HLZazhwFlWQWVAP40yLRU_mnrAAqfbFXoEnUQ8vO2E0` |
| `Single Instance mq m5.xlarge` | `_GpeUBAhVeChAHST1Pjm3iyHKLCmp8z65T-oAFvdOAk` |
| `Single Instance mq m5.2xlarge` | `jwLThnQyM2WcAWtHWrqTHNrIXA7a3umeCMg9tJYDZfU` |
| `Single Instance mq m5.4xlarge` | `7vf7Rg3t4twRI0-i6vh73Lz3cSnpa3tdCApPHKD570I` |
| `RabbitMQ Active Standby mq m5.large` | `5hcZU6WguRUktrgs8rMw8I50JgkU3TyzOOdhtsRRjXs` |
| `RabbitMQ Active Standby mq m5.xlarge` | `KPxC2fybU94reTBFrRT3bV_mp2XYp296Ymnif66W7Xo` |
| `RabbitMQ Active Standby mq m5.2xlarge` | `XNf64g6crkltBz6zv4_QWkSXAd0OoJWOUvcqApGLmSY` |
| `RabbitMQ Active Standby mq m5.4xlarge` | `ThiP7B-4dj61clPe5SnmJXF15UZoJ6O4LQltykX4tQ8` |
| `RabbitMQ Single Instance mq t3.micro` | `bIP-j-e1U0lIvrHHWKKiQEyMbgDp1ojFj116JEpClc0` |
| `RabbitMQ Single Instance mq m5.large` | `tIoJ4D_dNdY2Z0ip26h0fdIGIr9-giewflvmYs_wLQ4` |
| `RabbitMQ Single Instance mq m5.xlarge` | `w6squB73r6aqdldW-m_uu-eXzQOUkgg6MUAcD8GXYVE` |
| `RabbitMQ Single Instance mq m5.2xlarge` | `pSWo3F_5nj8PvgDjK2BX4NY5FdrJMD79gFnBwBF29wY` |
| `RabbitMQ Single Instance mq m5.4xlarge` | `PgcLCJ51By9-b00S4-7-PUgivVkUSw_zfnP89DKFuDQ` |
| `Broker Storage GB Mo` (storage SKU, EFS) | `Watrf2j3RTOHvqFvNyHO2__jk9suw5nwtH-siXP1ch0` |
| `Broker Storage Single AZ GB-Mo` (storage SKU, EBS) | `4yECRDLprMhFz4DNKwkPnhiB7MJsdz2F353VdKBw0HI` |

The catalog also has ActiveMQ Cross-Region Data Replication ("CRDR") variants and a free-tier storage row — re-run the resolver with `--dump-friendly` to pick those up. The Pricing API only sees one rate per row regardless; for any new token, the catalog is the canonical source.

Important quirk noted from the resolution work: the **captured "3-node cluster Broker" RabbitMQ Cluster line** uses the token `5hcZU6Wgu...`, which the catalog labels `RabbitMQ Active Standby mq m5.large`. The SPA reuses the Active/Standby per-broker rate code for the cluster path and multiplies by `rabbitmqNumberOfClusteredBrokers` — there is no separate "cluster" rate row.

---

## Path 1: RabbitMQ Cluster — `rabbitMQBroker` (Verified)

Line-item header:

```json
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "rabbitMQBroker",
  "version":      "0.0.59",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon MQ",
  "description":  null,
  "serviceCost":  { "monthly": <computed> }
}
```

### calculationComponents

```jsonc
{
  "rabbitBrokerType":                {"value": "0"},                          // captured "0" = 3-node cluster; other topology codes unknown
  "rabbitmqInstanceTypeClustered":   {"value": "<RegionlessRateCode for RabbitMQ Active Standby mq <type>>"},
  "rabbitmqNumberOfClusteredBrokers":{"value": "<N>"},
  "rabbitmqstoragePerNodeClustered": {"value": "<GB>", "unit": "gb|NA"},      // lowercase 's' in 'storage' is literal

  "dataTransfer": {                                                            // SAME array shape as VPC dataTransferVpc
    "value": [
      { "entryType": "INBOUND",      "fromRegion": "External", "unit": "tb_month", "value": "<X>" },
      { "entryType": "OUTBOUND",     "toRegion":   "External", "unit": "tb_month", "value": "<X>" },
      { "entryType": "INTRA_REGION",                            "unit": "tb_month", "value": "<X>" }
    ]
  }
}
```

### Formula (RabbitMQ Cluster)

```
brokers.monthly      = rabbitmqNumberOfClusteredBrokers * 730 * broker_hourly_rate(instanceType, region)
storage.monthly      = rabbitmqNumberOfClusteredBrokers * rabbitmqstoragePerNodeClustered_GB * storage_per_gb_month
data_xfer.monthly    = sum over dataTransfer.value entries (see VPC dataTransferVpc formula in vpc.md)
serviceCost.monthly  = brokers.monthly + storage.monthly + data_xfer.monthly
```

Captured at eu-west-1 with 10 × mq.m5.large clustered + 10 GB/node + 10 TB each DT direction → `serviceCost.monthly: $8,167.30`. The broker hourly rate is the catalog's `RabbitMQ Active Standby mq m5.large` `price` for the user's region (eu-west-1: $0.963/h per the catalog — `10 × 730 × 0.963 = $7,030`; the remaining ~$1,100 is storage + tiered DT).

### configSummary template (RabbitMQ Cluster)

```
Broker type (3-node cluster Broker), DT Inbound: <Internet|None> (<X> TB per month), DT Outbound: <Internet|<region>> (<X> TB per month), DT Intra-Region: (<X> TB per month), Amazon RabbitMQ Broker Instance (<instance type label>), Number of clustered Brokers (<N>), Storage per node (<X> GB)
```

---

## Path 2: ActiveMQ Single Instance — `singleInstanceBroker` (Inferred)

⚠ Shape inferred from `captures/bundle.js` form definition plus mq.json catalog for tokens. Field names and option ids are directly from bundle; no opaque tokens needed (ActiveMQ Single Instance uses **readable id strings** for `instanceType` and `brokerStorageType`). Round-trip a test save once to confirm the `version` value the SPA emits.

```json
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "singleInstanceBroker",
  "version":      "<TBD — confirm on first capture>",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon MQ",
  "description":  null,
  "serviceCost":  { "monthly": <computed> }
}
```

### calculationComponents (Single Instance Broker)

```jsonc
{
  "numberOfBrokers":    {"value": "<N>"},
  "instanceType":       {"value": "Single Instance mq m5.large"},   // readable id string from bundle dropdown
  "brokerStorageType":  {"value": "Broker Storage GB Mo"},          // "Broker Storage GB Mo" (EFS) or "Broker Storage Single AZ GB-Mo" (EBS, NOT supported for mq.t2.micro)
  "storagePerBroker":   {"value": "200", "unit": "gb|NA"},          // bundle default 200 GB

  "dataTransfer": { "value": [ ...same 3-entry array as Path 1... ] }
}
```

Valid `instanceType.value` strings — directly from bundle.js dropdown ids:

| Label | `instanceType.value` |
|---|---|
| `mq.t2.micro` | `Single Instance mq t2.micro` |
| `mq.m4.large` | `Single Instance mq m4.large` |
| `mq.m5.large` | `Single Instance mq m5.large` |
| `mq.m5.xlarge` | `Single Instance mq m5.xlarge` |
| `mq.m5.2xlarge` | `Single Instance mq m5.2xlarge` |
| `mq.m5.4xlarge` | `Single Instance mq m5.4xlarge` |

### Formula (Single Instance — straight from bundle.js mathsSection)

```
broker_cost    = numberOfBrokers * 730 * mqBrokerPrice(instanceType, region)
storage_cost   = numberOfBrokers * storagePerBroker_GB * storageBrokerPrice(brokerStorageType, region)
data_xfer_cost = standard DT tiered math (same as VPC dataTransferVpc)
serviceCost.monthly = broker_cost + storage_cost + data_xfer_cost
```

Look up `mqBrokerPrice` from the catalog's `regions[<region display>][<friendly key>].price` (or via Pricing API — they should match). `storageBrokerPrice` for `Broker Storage GB Mo` is the EFS per-GB-month rate; for `Broker Storage Single AZ GB-Mo` it's the EBS rate.

### configSummary template (Single Instance)

```
Number of Brokers running (<N>), Amazon MQ Broker Instance (<mq.x.y label>), Storage per Broker (<X> GB), DT Inbound: ..., DT Outbound: ..., DT Intra-Region: ...
```

---

## Path 3: ActiveMQ Active/Standby — `activeInstanceBroker` (Inferred)

Same provenance as Path 2: shape from bundle.js, tokens from mq.json catalog where applicable.

```json
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "activeInstanceBroker",
  "version":      "<TBD>",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon MQ",
  "description":  null,
  "serviceCost":  { "monthly": <computed> }
}
```

### calculationComponents (Active/Standby)

```jsonc
{
  "numberOfBrokers":   {"value": "<N>"},                              // typically 2 for active/standby
  "instanceType":      {"value": "Active Standby mq m5.large"},       // readable id string
  // brokerStorageType is FIXED to "Broker Storage GB Mo" (EFS only) — bundle omits the dropdown
  "storagePerBroker":  {"value": "<X>", "unit": "gb|NA"},

  "dataTransfer": { "value": [ ...same 3-entry array... ] }
}
```

Valid `instanceType.value` strings:

| Label | `instanceType.value` |
|---|---|
| `mq.t2.micro` | `Active Standby mq t2.micro` |
| `mq.m4.large` | `Active Standby mq m4.large` |
| `mq.m5.large` | `Active Standby mq m5.large` |
| `mq.m5.xlarge` | `Active Standby mq m5.xlarge` |
| `mq.m5.2xlarge` | `Active Standby mq m5.2xlarge` |
| `mq.m5.4xlarge` | `Active Standby mq m5.4xlarge` |

### Formula (Active/Standby)

Identical to Single Instance: `broker_cost = numberOfBrokers * 730 * mqBrokerPrice + storage_cost + data_xfer_cost`. Storage price is the EFS rate (only storage type allowed on this template).

---

## Path 4: RabbitMQ Single Instance (Inferred)

⚠ Bundle.js v1 has no RabbitMQ form definitions, but mq.json contains the RabbitMQ Single Instance token series (5 instance types: m5.large/xlarge/2xlarge/4xlarge + t3.micro). The cc shape is **not yet HAR-verified** — the most likely shape mirrors RabbitMQ Cluster with one swap: `rabbitmqNumberOfClusteredBrokers` becomes `"1"` (or the field name changes; capture HAR to confirm). Until then, prefer Path 2 (ActiveMQ Single Instance) as a fully-quoteable alternative if the user's engine choice is flexible, or emit this best-effort and flag in the breakdown:

```jsonc
// SPECULATIVE shape — verify against HAR before relying on it
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "rabbitMQBroker",
  "version":      "0.0.59",                                       // copying from Cluster capture; may differ
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon MQ",
  "description":  null,
  "calculationComponents": {
    "rabbitBrokerType":                {"value": "<TBD — likely a different small-int selector>"},
    "rabbitmqInstanceTypeClustered":   {"value": "<RegionlessRateCode for RabbitMQ Single Instance mq <type>>"},
    "rabbitmqNumberOfClusteredBrokers":{"value": "1"},
    "rabbitmqstoragePerNodeClustered": {"value": "<GB>", "unit": "gb|NA"},
    "dataTransfer": { "value": [ ...3-entry array... ] }
  },
  "serviceCost": { "monthly": <computed> }
}
```

When you do capture a HAR for this path, update this section and promote it to **Verified**.

---

## Pricing API filters

```
--service-code AmazonMQ
--filter productFamily="Message Broker"
--filter brokerEngine=<ActiveMQ|RabbitMQ>
--filter deploymentOption=<Single|Active|Cluster>
--filter instanceType=<mq.t2.micro|mq.m4.large|mq.m5.large|...>
--filter regionCode=<region>
```

Returns OnDemand `Hrs` rate per broker-hour. These rates should match `mq.json`'s `regions[<region>][<friendly key>].price` field — if they diverge, prefer the live Pricing API value.

Storage SKU is separate:
```
--service-code AmazonMQ
--filter productFamily="Broker Storage"
--filter brokerEngine=<ActiveMQ|RabbitMQ>
--filter storageType=<EFS|EBS>
--filter regionCode=<region>
```

Data transfer SKUs live under `AmazonEC2`; see `vpc.md` Pricing API filters.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfBrokers (single) | "1" | A single-instance broker is one node |
| numberOfBrokers (active/standby) | "2" | One active + one standby |
| numberOfBrokers (cluster) | "3" | Smallest cluster; matches captured `rabbitBrokerType: "0"` topology |
| instanceType | none — **ask** | Per-hour rate varies ~80x across t2.micro through m5.4xlarge |
| storagePerBroker (single) | "200" GB (bundle default) | |
| storagePerBroker (active/standby, cluster) | "20" GB | Modest default; bundle has no default for active/standby |
| brokerStorageType (single) | "Broker Storage GB Mo" (EFS) | Bundle default; EBS variant is `"Broker Storage Single AZ GB-Mo"` and is not valid for t2.micro |
| dataTransfer entries | always emit all 3 entryTypes with `"0"` for unspecified directions | Matches captured shape |

## Verification

- **Path 1 (RabbitMQ Cluster)**: verified from `captures/saveAs/per-service/amazonMQ.json` (eu-west-1). `serviceCost.monthly: $8,167.30` matches `10 × 730 × $0.963 (catalog rate) + storage + DT` within tolerance.
- **Paths 2/3 (ActiveMQ Single Instance / Active-Standby)**: shape from `captures/bundle.js` `singleInstanceBroker` and `activeInstanceBroker` templates; token table from `mq.json` catalog. Round-trip a test save once before quoting at scale.
- **Path 4 (RabbitMQ Single Instance)**: token table present in catalog; cc shape is speculative (mirrors Cluster with brokers=1). Capture HAR to confirm.
- The full friendly→token mapping above is from a catalog snapshot; re-run `python3 scripts/resolve_token.py mq --dump-friendly` to refresh if the catalog adds new instance types or ActiveMQ CRDR variants.

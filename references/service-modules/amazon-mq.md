# Amazon MQ (`amazonMQ`)

`serviceCode` is `amazonMQ`. Amazon MQ has multiple form templates selected by the `estimateFor` value; this module covers four configurations with different confidence levels. The "opaque token" problem this module previously had is resolved — the SPA's public pricing catalog at `calculator.aws/pricing/2.0/meteredUnitMaps/mq/USD/current/mq.json` contains the full friendly-key → `RegionlessRateCode` mapping for every (engine, mode, instance type) combination, and that `RegionlessRateCode` IS the opaque token used in cc. See §Opaque token resolution below.

> **BREAKING in form 0.0.60 — `estimateFor: "activeInstanceBroker"` no longer exists.** The live form definition ships exactly two templates, `singleInstanceBroker` and `rabbitMQBroker`. The ActiveMQ Active/Standby path documented below as Path 3 has been folded into `singleInstanceBroker`, selected by a new `activeBrokerType` dropdown (`"1"` = single-instance, `"0"` = active/standby) with its own `_2`-suffixed field set. **Do not emit `estimateFor: "activeInstanceBroker"`** — the SPA has no template to resolve it. See Path 3 for the replacement shape.
>
> **Also in 0.0.60: Path 2's `instanceType` / `brokerStorageType` values are opaque tokens, not the readable strings this module documented.** The live dropdown option ids are `RegionlessRateCode`s (e.g. `Single Instance mq t2.micro` → `xgy1w0xhhksiyvrKXO6-2UQQynDmqJafzIh8kqhD214`), the same tokens already tabulated below. Both flags are read from the form definition and are **not capture-verified**.

## Coverage matrix

| Path | `estimateFor` | Confidence | Anchor |
|---|---|---|---|
| RabbitMQ Cluster (Multi-AZ) | `rabbitMQBroker` | **Verified** end-to-end from HAR | `captures/saveAs/per-service/amazonMQ.json` (local capture, not in repo) |
| ActiveMQ Single Instance | `singleInstanceBroker` (`activeBrokerType: "1"`) | **Inferred** from `captures/bundle.js` form + catalog token table; field values re-checked against form 0.0.60 | bundle.js + mq.json catalog + form 0.0.60 |
| ActiveMQ Active/Standby | `singleInstanceBroker` (`activeBrokerType: "0"`) — **NOT `activeInstanceBroker`; that template is gone in 0.0.60** | **Inferred** from form 0.0.60 | form 0.0.60 + mq.json catalog |
| RabbitMQ Single Instance | `rabbitMQBroker` (`rabbitBrokerType: "1"`) | **Verified** end-to-end from live-SPA HAR | sessionStorage capture (2026-06) + mq.json catalog |

When the user's brief is ambiguous (e.g. "Amazon MQ broker, m5.large"), ask which engine (ActiveMQ vs RabbitMQ) and which deployment mode (single / active-standby / cluster) — engine + mode determines which template, which token series, and which rate row in the catalog.

## Opaque token resolution

Several cc fields across MQ paths carry 43-char URL-safe-base64 tokens (`rabbitmqInstanceTypeClustered` for RabbitMQ Cluster; `rabbitmqInstanceType` + `rabbitmqBrokerStorageType` for RabbitMQ Single Instance — see Path 4). These tokens are NOT secret — they are simply `RegionlessRateCode` values from `mq.json`. The friendly key in that catalog encodes engine + mode + instance type as a single string.

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
| RabbitMQ Single Instance EBS storage type (`rabbitmqBrokerStorageType`, "Throughput optimized (EBS)") | `esp4MPQi7KC4ZP_fJVh0_C5OFda2B5SOjR_Yc8g-bxM` |

The catalog also has ActiveMQ Cross-Region Data Replication ("CRDR") variants and a free-tier storage row — re-run the resolver with `--dump-friendly` to pick those up. The Pricing API only sees one rate per row regardless; for any new token, the catalog is the canonical source.

Important quirk noted from the resolution work: the **captured "3-node cluster Broker" RabbitMQ Cluster line** uses the token `5hcZU6Wgu...`, which the catalog labels `RabbitMQ Active Standby mq m5.large`. The SPA reuses the Active/Standby per-broker rate code for the cluster path and multiplies by `rabbitmqNumberOfClusteredBrokers` — there is no separate "cluster" rate row.

---

## Path 1: RabbitMQ Cluster — `rabbitMQBroker` (Verified)

Line-item header:

```json
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "rabbitMQBroker",
  "version":      "0.0.60",
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

⚠ Shape inferred from `captures/bundle.js` form definition plus mq.json catalog for tokens.

> **Corrected against form 0.0.60 (2026-09-06):** this module previously claimed ActiveMQ Single Instance uses **readable id strings** for `instanceType` and `brokerStorageType`. It does not. The live dropdown option ids are the same `RegionlessRateCode` tokens tabulated in §Opaque token resolution — `instanceType` options run `xgy1w0xh…` (t2.micro) through `7vf7Rg3t…` (m5.4xlarge), and `brokerStorageType` defaults to `Watrf2j3RTOHvqFvNyHO2__jk9suw5nwtH-siXP1ch0` ("Broker Storage GB Mo", EFS). Emit the token, not the friendly key. Read from the form definition; **not capture-verified**.

```json
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "singleInstanceBroker",
  "version":      "0.0.60",
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
  "activeBrokerType":   {"value": "1"},                             // "1" = Single-instance (form default); "0" selects Active/Standby — see Path 3
  "numberOfBrokers":    {"value": "<N>"},
  "instanceType":       {"value": "HLZazhwFlWQWVAP40yLRU_mnrAAqfbFXoEnUQ8vO2E0"},   // RegionlessRateCode token; form labels it "mq.m5.large", mq.json's friendly key is "Single Instance mq m5.large"
  "brokerStorageType":  {"value": "Watrf2j3RTOHvqFvNyHO2__jk9suw5nwtH-siXP1ch0"},   // form default; EBS is "4yECRDLprMhFz4DNKwkPnhiB7MJsdz2F353VdKBw0HI" (NOT supported for mq.t2.micro). The form labels these "Durability optimized (Amazon EFS)" / "Throughput optimized (EBS)"; the friendly keys "Broker Storage GB Mo" / "Broker Storage Single AZ GB-Mo" come from mq.json, not the form
  "storagePerBroker":   {"value": "200", "unit": "gb|NA"},          // form default 200 GB

  // Cross-region data replication broker count. Present in form 0.0.60 on BOTH
  // MQ templates; validations.required = true, no form default, frequency field
  // (defaultFrequency "perHour", output "perMonth"). Inferred from the form
  // definition, not capture-verified — send "0" when CRDR is not in use.
  "numberOfbrokersrunningdatareplication": {"value": "0", "unit": "perMonth"},

  "dataTransfer": { "value": [ ...same 3-entry array as Path 1... ] }
}
```

Valid `instanceType.value` tokens — from the form 0.0.60 dropdown option ids (these are the same `RegionlessRateCode`s as the friendly-key table above):

| Label | `instanceType.value` |
|---|---|
| `mq.t2.micro` | `xgy1w0xhhksiyvrKXO6-2UQQynDmqJafzIh8kqhD214` |
| `mq.t3.micro` | `7TrHec2r24mxInPR-Bprm45ubxZ-3Ran19DAA_H7ftA` |
| `mq.m4.large` | `i3UuD2-5BN8zq0Wfa2ljDCKbHPVmig3PlLq4CZx3v08` |
| `mq.m5.large` | `HLZazhwFlWQWVAP40yLRU_mnrAAqfbFXoEnUQ8vO2E0` |
| `mq.m5.xlarge` | `_GpeUBAhVeChAHST1Pjm3iyHKLCmp8z65T-oAFvdOAk` |
| `mq.m5.2xlarge` | `jwLThnQyM2WcAWtHWrqTHNrIXA7a3umeCMg9tJYDZfU` |
| `mq.m5.4xlarge` | `7vf7Rg3t4twRI0-i6vh73Lz3cSnpa3tdCApPHKD570I` |

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

## Path 3: ActiveMQ Active/Standby — `singleInstanceBroker` + `activeBrokerType: "0"` (Inferred)

> **`estimateFor: "activeInstanceBroker"` is GONE as of form 0.0.60 (checked 2026-09-06).** The live definition ships only `singleInstanceBroker` and `rabbitMQBroker`. Active/Standby is now a branch *inside* `singleInstanceBroker`: set `activeBrokerType: "0"` and use the `_2`-suffixed field set (`numberOfBrokers_2`, `instanceType_2`, `storagePerBroker_2`). `instanceType_2`'s form default is `kfxZ0YaiRoHs7pML7IWMBWDLefTTKVdqZUmyOtGJoMg` — the `Active Standby mq t2.micro` token from the table above, which confirms the branch maps to the Active/Standby rate series. There is no `brokerStorageType_2`: the storage type stays fixed to EFS on this branch, as previously documented. All of this is **inferred from the form definition, not capture-verified** — capture an Active/Standby HAR before quoting at scale.

```json
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "singleInstanceBroker",
  "version":      "0.0.60",
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
  "activeBrokerType":    {"value": "0"},                             // "0" = Active/standby-instance Broker
  "numberOfBrokers_2":   {"value": "<N>"},                           // typically 2 for active/standby — note the _2 suffix
  "instanceType_2":      {"value": "7lVtnGTGLw_MCxTFas-0CZbLqyBXbwYqww8u7D2jAuo"},  // token; form labels it "mq.m5.large", mq.json's friendly key is "Active Standby mq m5.large"
  // there is no brokerStorageType_2 — storage is FIXED to EFS on this branch
  "storagePerBroker_2":  {"value": "<X>", "unit": "gb|NA"},

  "numberOfbrokersrunningdatareplication": {"value": "0", "unit": "perMonth"},  // shared with Path 2

  "dataTransfer": { "value": [ ...same 3-entry array... ] }
}
```

Valid `instanceType_2.value` tokens (form 0.0.60 option ids):

| Label | `instanceType_2.value` |
|---|---|
| `mq.t2.micro` | `kfxZ0YaiRoHs7pML7IWMBWDLefTTKVdqZUmyOtGJoMg` (form default) |
| `mq.t3.micro` | `npxP4jMuDPI0Tsa33ciplHdXcReZI2smOX69b1Lg6C4` |
| `mq.m4.large` | `SLebDRjZkpP_bjXHPXfEmPQiI4NudlvtieaZhTyDODU` |
| `mq.m5.large` | `7lVtnGTGLw_MCxTFas-0CZbLqyBXbwYqww8u7D2jAuo` |
| `mq.m5.xlarge` | `uf168aXfjL6-aRynoV2NlgtBV7ylSjUNPr5T_qbQecY` |
| `mq.m5.2xlarge` | `szEa9FzeZ2rVziGW0DE8PENkqHUNUqXDx3WQsLQ74Og` |
| `mq.m5.4xlarge` | `avUaVtodKfdIrt83yUrbRnlaOFydLtxyaUc_qSgP5jU` |

### Formula (Active/Standby)

Identical to Single Instance: `broker_cost = numberOfBrokers * 730 * mqBrokerPrice + storage_cost + data_xfer_cost`. Storage price is the EFS rate (only storage type allowed on this template).

---

## Path 4: RabbitMQ Single Instance — `rabbitMQBroker` (Verified)

✅ HAR-verified from the live SPA (`sessionStorage` key `awspc-root-estimate-v1`, captured 2026-06). The single-instance form reuses `estimateFor: "rabbitMQBroker"` (same as Cluster; `version` was `0.0.59` at capture time and the live form has since moved to `0.0.60` — see the Verification section) but its cc uses a **different field set** than the Cluster path — do not copy the Cluster fields. Key differences: `rabbitBrokerType` is `"1"` for single-instance (Cluster is `"0"`), the instance/storage field names drop the `Clustered` suffix, there is **no broker-count field** (single instance is implicitly 1), and there is a distinct `rabbitmqBrokerStorageType` token field.

Line-item header:

```json
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "rabbitMQBroker",
  "version":      "0.0.60",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon MQ",
  "description":  null,
  "serviceCost":  { "monthly": <computed> }
}
```

### calculationComponents (RabbitMQ Single Instance)

```jsonc
{
  "rabbitBrokerType":          {"value": "1"},                                     // "1" = single-instance (Cluster = "0")
  "rabbitmqInstanceType":      {"value": "<RegionlessRateCode for RabbitMQ Single Instance mq <type>>"},
  "rabbitmqBrokerStorageType": {"value": "<storage-type token — see below>"},      // NOT a readable string; a RegionlessRateCode
  "rabbitmqStoragePerBroker":  {"value": "<GB>", "unit": "gb|NA"},                 // capital 'S' in 'Storage', no 'Clustered'
  "dataTransfer": {                                                                // SAME 3-entry array shape as Cluster path
    "value": [
      { "entryType": "INBOUND",      "value": "<X|''>", "unit": "tb_month", "fromRegion": "<region|''>" },
      { "entryType": "OUTBOUND",     "value": "<X|''>", "unit": "tb_month", "toRegion":   "<region|''>" },
      { "entryType": "INTRA_REGION", "value": "<X|''>", "unit": "tb_month" }
    ]
  }
}
```

There is **no** `rabbitmqNumberOfClusteredBrokers` / `numberOfBrokers` field — a single-instance broker is always one node. The form shows a "Number of Brokers running" input but the captured cc omits it; do not add it.

**`rabbitmqBrokerStorageType` tokens** (the "Broker storage type" dropdown — these are `RegionlessRateCode`s, region-independent; the SPA resolves the per-region price):

| Storage type label | Token | Per-GB-mo rate source |
|---|---|---|
| Throughput optimized (EBS) — default for m5.* | `esp4MPQi7KC4ZP_fJVh0_C5OFda2B5SOjR_Yc8g-bxM` | EBS rate (eu-central-1: $0.119; eu-west-1: $0.11; us-east-2: $0.10) |
| Durability optimized (Amazon EFS) | `Watrf2j3RTOHvqFvNyHO2__jk9suw5nwtH-siXP1ch0` (`Broker Storage GB Mo`) | EFS rate |

The EBS storage token is not in `resolve_token.py --dump-friendly` (it has no friendly key); look it up by `RegionlessRateCode` directly in `mq.json` if you need its per-region price, or use the EBS per-GB-mo rate for the region.

### Formula (RabbitMQ Single Instance)

```
broker.monthly      = 730 * broker_hourly_rate(RabbitMQ Single Instance mq <type>, region)   // 1 broker
storage.monthly     = rabbitmqStoragePerBroker_GB * storage_per_gb_month(storage-type, region)
data_xfer.monthly   = sum over dataTransfer.value entries (see VPC dataTransferVpc formula)
serviceCost.monthly = broker.monthly + storage.monthly + data_xfer.monthly
```

Verified example (eu-central-1, mq.m5.2xlarge, EBS, 1024 GB, no DT): `730 × $1.38 + 1024 × $0.119 = $1,129.26`. The instance hourly rate is `mq.json`'s `regions[<region>][RabbitMQ Single Instance mq <type>].price`.

> **Recompute validation caveat:** headless Chromium does **not** run the calculator's client-side price engine — a freshly hand-built, fully-valid single-instance line displays `$0.00` in headless even though the cc is correct. So the live-SPA recompute check (SKILL.md step 7) can confirm the cc **shape** round-trips (region/engine/broker-type/instance/storage all recognized, no "incompatible inputs" error, configSummary regenerates) but **cannot** confirm the numeric cost headless. Confirm the number against the `mq.json` catalog rates instead — that is the same pricing source the SPA uses.

### configSummary template (RabbitMQ Single Instance)

```
Broker type (Single-instance Broker), DT Inbound: <Internet|Not selected> (<X> TB per month), DT Outbound: <Internet|<region>|Not selected> (<X> TB per month), DT Intra-Region: (<X> TB per month), Storage per Broker (<X> GB), Amazon RabbitMQ Broker Instance (<instance type label>)
```

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

Fixture: `references/fixtures/amazonMQ.json` (Path 1, RabbitMQ Cluster).

- **Path 1 (RabbitMQ Cluster)**: verified from `captures/saveAs/per-service/amazonMQ.json` (eu-west-1). `serviceCost.monthly: $8,167.30` matches `10 × 730 × $0.963 (catalog rate) + storage + DT` within tolerance.
- **Paths 2/3 (ActiveMQ Single Instance / Active-Standby)**: shape originally taken from `captures/bundle.js`, which at that time had separate `singleInstanceBroker` and `activeInstanceBroker` templates; token table from `mq.json` catalog. **The `activeInstanceBroker` template no longer exists** — both paths were re-derived from form 0.0.60 (see the 2026-09-06 entry below). Round-trip a test save once before quoting at scale.
- **Path 4 (RabbitMQ Single Instance)**: **verified** from a live-SPA `sessionStorage` capture (2026-06). cc uses `rabbitBrokerType: "1"`, `rabbitmqInstanceType`, `rabbitmqBrokerStorageType` (token), `rabbitmqStoragePerBroker`, `dataTransfer` — and NO broker-count field. Example: eu-central-1 mq.m5.2xlarge + EBS 1024 GB = `730 × $1.38 + 1024 × $0.119 = $1,129.26`. Numeric recompute is not observable headless (price engine doesn't run); validate the number against `mq.json` rates.
- The full friendly→token mapping above is from a catalog snapshot; re-run `python3 scripts/resolve_token.py mq --dump-friendly` to refresh if the catalog adds new instance types or ActiveMQ CRDR variants.

- **Form 0.0.59 → 0.0.60 (2026-09-06).** Diffed against the live form definition (`data/amazonMQ/en_US.json`, version `0.0.60`). Fields **added: `activeBrokerType`** (Broker type dropdown on `singleInstanceBroker`, default `"1"`), **`numberOfBrokers_2` / `instanceType_2` / `storagePerBroker_2`** (the Active/Standby branch), **`numberOfbrokersrunningdatareplication`** (cross-region data replication, on both templates); **removed: the entire `activeInstanceBroker` template** — `templates` is now exactly `["singleInstanceBroker", "rabbitMQBroker"]`. Renamed: none. All Path 1 and Path 4 cc keys are unchanged and still present.
- **Correction, not a version change:** Path 2's `instanceType` and `brokerStorageType` were documented as readable strings (`"Single Instance mq m5.large"`, `"Broker Storage GB Mo"`). The live dropdowns use `RegionlessRateCode` tokens for both. The token tables in Paths 2 and 3 were rewritten from the form's option ids. Both paths remain **inferred from the form definition, not capture-verified**; no ActiveMQ saveAs body has ever been captured, so neither the old strings nor the new tokens were ever round-tripped.
- The friendly→token table in §Opaque token resolution is now **incomplete**: form 0.0.60 offers `mq.m7g.medium` / `large` / `xlarge` / `2xl` / `4xl` / `8xl` / `12xl` / `16xl` for `rabbitmqInstanceType` and `rabbitmqInstanceTypeClustered`, none of which are listed there. Re-run `python3 scripts/resolve_token.py mq --dump-friendly` before quoting an m7g RabbitMQ broker.
- `references/examples/groups-example-body.json` still pins `amazonMQ` at 0.0.59. It is a historical capture used only by the math/validation tests; it was deliberately left alone.

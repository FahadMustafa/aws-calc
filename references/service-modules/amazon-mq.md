# Amazon MQ (`amazonMQ`)

`serviceCode` is `amazonMQ`. Amazon MQ has multiple form templates selected by the `estimateFor` value; this module covers four configurations with different confidence levels (see §Coverage matrix below). Always pick the right template — the SPA validates each form's cc keys literally, and switching templates is not just a config change.

## Coverage matrix

| Path | `estimateFor` | Confidence | Anchor |
|---|---|---|---|
| RabbitMQ Cluster (3-node) | `rabbitMQBroker` | **Verified** end-to-end from HAR | `captures/saveAs/per-service/amazonMQ.json` |
| ActiveMQ Single Instance | `singleInstanceBroker` | **Inferred** from `captures/bundle.js` form definition — quoteable but **flag in breakdown** | none |
| ActiveMQ Active/Standby | `activeInstanceBroker` | **Inferred** from `captures/bundle.js` form definition — quoteable but **flag in breakdown** | none |
| RabbitMQ Single Instance | unknown | **Unknown** — bundle.js v1 has no RabbitMQ definitions; the captured cluster form is from a newer SPA. **Refuse** without a fresh HAR | n/a |

When the user's brief is ambiguous (e.g. "Amazon MQ broker, m5.large"), ask which engine (ActiveMQ vs RabbitMQ) and which deployment mode (single / active-standby / cluster). Engine + mode determines which template and rate table apply, and the per-broker hourly rate differs across them.

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
  "rabbitBrokerType":                {"value": "0"},                                            // cluster topology selector; "0" = 3-node cluster (captured); other values are unknown
  "rabbitmqInstanceTypeClustered":   {"value": "5hcZU6WguRUktrgs8rMw8I50JgkU3TyzOOdhtsRRjXs"}, // OPAQUE instance-type token — see token table below
  "rabbitmqNumberOfClusteredBrokers":{"value": "10"},
  "rabbitmqstoragePerNodeClustered": {"value": "10", "unit": "gb|NA"},                          // lowercase 's' in 'storage'

  "dataTransfer": {                                                                              // SAME array shape as VPC dataTransferVpc
    "value": [
      { "entryType": "INBOUND",      "fromRegion": "External", "unit": "tb_month", "value": "10" },
      { "entryType": "OUTBOUND",     "toRegion":   "External", "unit": "tb_month", "value": "10" },
      { "entryType": "INTRA_REGION",                            "unit": "tb_month", "value": "10" }
    ]
  }
}
```

`rabbitmqInstanceTypeClustered` carries a 43-char URL-safe base64-ish token that the SPA dereferences at calculation time. The token is **not** in greppable form in the bundle.js snapshot — it lives in a newer pricing-catalog asset the SPA fetches at runtime.

| Token | Instance type | Source |
|---|---|---|
| `5hcZU6WguRUktrgs8rMw8I50JgkU3TyzOOdhtsRRjXs` | `mq.m5.large` | `captures/saveAs/per-service/amazonMQ.json` (eu-west-1) |

To quote any other clustered instance type, capture a fresh HAR with that type selected and extract its token. **Do not invent or guess tokens** — a malformed token causes the SPA to recompute `serviceCost.monthly: $0` on load, even if you write a non-zero `serviceCost` into the body.

### Formula (RabbitMQ Cluster)

```
brokers.monthly      = rabbitmqNumberOfClusteredBrokers * 730 * broker_hourly_rate(instanceType)
storage.monthly      = rabbitmqNumberOfClusteredBrokers * rabbitmqstoragePerNodeClustered_GB * storage_per_gb_month
data_xfer.monthly    = sum over dataTransfer.value entries (see VPC dataTransferVpc formula in vpc.md)
serviceCost.monthly  = brokers.monthly + storage.monthly + data_xfer.monthly
```

Captured at eu-west-1 with 10 × mq.m5.large clustered + 10 GB/node + 10 TB each DT direction → `serviceCost.monthly: $8,167.30`. Back-calculation puts the broker hourly rate near $1.00 and storage near $0.10/GB-mo; **re-derive per-region rates from `get-products` before quoting**.

### configSummary template (RabbitMQ Cluster)

```
Broker type (3-node cluster Broker), DT Inbound: <Internet|None> (<X> TB per month), DT Outbound: <Internet|<region>> (<X> TB per month), DT Intra-Region: (<X> TB per month), Amazon RabbitMQ Broker Instance (<instance type label>), Number of clustered Brokers (<N>), Storage per node (<X> GB)
```

---

## Path 2: ActiveMQ Single Instance — `singleInstanceBroker` (Inferred)

⚠ Shape inferred from `captures/bundle.js` (the SPA's form-layout definition for the Single Instance Broker template). Field names and dropdown option ids are directly from the bundle, so they should round-trip correctly — but no captured saveAs body has been verified against this module yet. Emit and flag in the breakdown as "shape inferred from bundle.js; verify with a test save before relying on it".

Line-item header:

```json
{
  "serviceCode":  "amazonMQ",
  "estimateFor":  "singleInstanceBroker",
  "version":      "<TBD — copy whatever the SPA emits when you do the first capture>",
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
  "instanceType":       {"value": "Single Instance mq m5.large"},   // see option table below — these are READABLE id strings, not opaque tokens
  "brokerStorageType":  {"value": "Broker Storage GB Mo"},          // "Broker Storage GB Mo" (EFS) or "Broker Storage Single AZ GB-Mo" (EBS)
  "storagePerBroker":   {"value": "200", "unit": "gb|NA"},          // bundle default is 200 GB

  "dataTransfer": {
    "value": [
      { "entryType": "INBOUND",      "fromRegion": "External", "unit": "tb_month", "value": "0" },
      { "entryType": "OUTBOUND",     "toRegion":   "External", "unit": "tb_month", "value": "<X>" },
      { "entryType": "INTRA_REGION",                            "unit": "tb_month", "value": "<X>" }
    ]
  }
}
```

**No opaque hash tokens** for single-instance — `instanceType` and `brokerStorageType` take the literal human-readable `id` strings from the bundle dropdown definitions.

Valid `instanceType` values (from bundle.js):

| Label shown | `instanceType.value` to set |
|---|---|
| `mq.t2.micro` | `Single Instance mq t2.micro` |
| `mq.m4.large` | `Single Instance mq m4.large` |
| `mq.m5.large` | `Single Instance mq m5.large` |
| `mq.m5.xlarge` | `Single Instance mq m5.xlarge` |
| `mq.m5.2xlarge` | `Single Instance mq m5.2xlarge` |
| `mq.m5.4xlarge` | `Single Instance mq m5.4xlarge` |

Valid `brokerStorageType` values:

| Label shown | `brokerStorageType.value` to set | Notes |
|---|---|---|
| Durability optimized (Amazon EFS) | `Broker Storage GB Mo` | Default per bundle |
| Throughput optimized (EBS) | `Broker Storage Single AZ GB-Mo` | **Not supported for mq.t2.micro** per bundle validation |

### Formula (Single Instance — directly from bundle.js maths section)

```
broker_cost    = numberOfBrokers * 730 * mqBrokerPrice(instanceType, region)
storage_cost   = numberOfBrokers * storagePerBroker_GB * storageBrokerPrice(brokerStorageType, region)
data_xfer_cost = standard DT tiered math (same as VPC dataTransferVpc)

serviceCost.monthly = broker_cost + storage_cost + data_xfer_cost
```

### configSummary template (Single Instance)

```
Number of Brokers running (<N>), Amazon MQ Broker Instance (<mq.x.y label>), Storage per Broker (<X> GB), DT Inbound: ..., DT Outbound: ..., DT Intra-Region: ...
```

---

## Path 3: ActiveMQ Active/Standby — `activeInstanceBroker` (Inferred)

⚠ Same provenance as Path 2: shape inferred from `captures/bundle.js`, not yet round-trip-verified.

Line-item header:

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
  "numberOfBrokers":   {"value": "<N>"},                              // typically 2 for active/standby; bundle does not constrain
  "instanceType":      {"value": "Active Standby mq m5.large"},       // see option table below
  // brokerStorageType is FIXED to "Broker Storage GB Mo" (Durability optimized / EFS) on this template — the bundle omits the dropdown
  "storagePerBroker":  {"value": "<X>", "unit": "gb|NA"},             // bundle has no default — user must specify

  "dataTransfer": { "value": [ ...same shape as above... ] }
}
```

Valid `instanceType` values (from bundle.js):

| Label shown | `instanceType.value` to set |
|---|---|
| `mq.t2.micro` | `Active Standby mq t2.micro` |
| `mq.m4.large` | `Active Standby mq m4.large` |
| `mq.m5.large` | `Active Standby mq m5.large` |
| `mq.m5.xlarge` | `Active Standby mq m5.xlarge` |
| `mq.m5.2xlarge` | `Active Standby mq m5.2xlarge` |
| `mq.m5.4xlarge` | `Active Standby mq m5.4xlarge` |

### Formula (Active/Standby — directly from bundle.js maths section)

Identical to Single Instance: `broker_cost = numberOfBrokers * 730 * mqBrokerPrice + storage_cost + data_xfer_cost`. Storage price is the EFS rate (the only storage type allowed here).

### configSummary template (Active/Standby)

```
Number of Brokers running (<N>), Amazon MQ Broker Instance (<mq.x.y label>), Storage per Broker (<X> GB), DT ...
```

---

## Path 4: RabbitMQ Single Instance — Unknown

Bundle.js v1 in `captures/bundle.js` predates RabbitMQ support (zero `rabbitmq` references in the file), so we cannot infer the form from the bundle. The captured RabbitMQ Cluster form is the only RabbitMQ shape we have ground truth for, and it has different `estimateFor` / cc keys than the ActiveMQ paths.

**Refuse to emit RabbitMQ Single Instance** until a HAR is captured. Tell the user: "Single-instance RabbitMQ isn't covered by this module — please capture a HAR of the SPA configured for single-instance RabbitMQ so I can add the shape. Alternatives in the meantime: ActiveMQ Single Instance (Path 2) or RabbitMQ Cluster (Path 1)."

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

Returns OnDemand `Hrs` rate per broker-hour.

Storage SKU is separate:
```
--service-code AmazonMQ
--filter productFamily="Broker Storage"
--filter brokerEngine=<ActiveMQ|RabbitMQ>
--filter storageType=<EFS|EBS>
--filter regionCode=<region>
```

Data transfer SKUs live under `AmazonEC2`; see `vpc.md` Pricing API filters for the same shape.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfBrokers (single) | "1" | A single-instance broker is one node |
| numberOfBrokers (active/standby) | "2" | One active + one standby |
| numberOfBrokers (cluster) | "3" | Smallest cluster; matches captured `rabbitBrokerType: "0"` topology |
| instanceType | none — **ask** | Per-hour rate varies ~80x across t2.micro through m5.4xlarge |
| storagePerBroker (single) | "200" GB (bundle default) | |
| storagePerBroker (active/standby, cluster) | "20" GB | Modest default; bundle has no default for active/standby |
| brokerStorageType (single) | "Broker Storage GB Mo" (EFS) | Bundle default. Switch to EBS only if user explicitly mentions throughput-optimized; not valid for t2.micro |
| dataTransfer entries | omit unmentioned directions but always emit all 3 entryTypes with `"0"` when dataTransfer is sent | Matches captured shape |

## Verification

- **Path 1 (RabbitMQ Cluster)**: `captures/calculator.aws_new_6.har` → `captures/saveAs/per-service/amazonMQ.json`. `serviceCost.monthly: $8,167.30` reconstructs within ~$100 using inferred ~$1/h mq.m5.large clustered rate.
- **Path 2 (ActiveMQ Single Instance)** and **Path 3 (ActiveMQ Active/Standby)**: shape inferred from `captures/bundle.js` lines defining the `singleInstanceBroker` and `activeInstanceBroker` templates. Math formula extracted from the bundle's `mathsSection`. **Round-trip a test save once before quoting at scale**; the field names match bundle ids exactly and option ids are readable, so the shape should be correct, but the SPA's `version` value to put in the line-item header is not known until first capture.
- **Path 4 (RabbitMQ Single Instance)**: unknown. Refuse without HAR.
- Only the `mq.m5.large` Cluster instance-type token is known. Cluster quotes for other instance types require fresh HARs per type.

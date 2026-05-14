# EC2 (`ec2Enhancement`)

Covers EC2 compute, EBS storage, snapshots, monitoring, and EC2 data transfer in a single line item.

## Line-item header

```json
{
  "serviceCode":  "ec2Enhancement",
  "estimateFor":  "template",
  "version":      "0.0.68",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon EC2",
  "description":  null
}
```

## calculationComponents (verified shape)

```jsonc
{
  "tenancy":           {"value": "shared"},                        // shared | dedicatedInstance | dedicatedHost
  "selectedOS":        {"value": "linux"},                         // linux | windows | rhel | sles
  "workloadSelection": {"value": "consistent"},                    // consistent | dailySpike | weeklySpike | monthlySpike
  "workload": {                                                    // count of instances + workload pattern
    "value": {
      "workloadType": "consistent",
      "data": "1"                                                  // instance count as string
    }
  },
  "instanceType":      {"value": "t3.small"},
  "pricingStrategy": {                                             // see "Pricing strategy values" below
    "value": {
      "selectedOption":   "on-demand",
      "term":             "1 year",
      "utilizationValue": "100",
      "utilizationUnit":  "%Utilized/Month"
    }
  },
  "storageType":       {"value": "Storage General Purpose gp3 GB Mo"},
  "storageAmount":     {"value": "500", "unit": "gb|NA"},
  "snapshotFrequency": {"value": "30"},                            // snapshots per month, "0" disables
  "detailedMonitoringCheckbox": {"value": false},
  "ec2AdvancedPricingMetrics":  {"value": 1},
  "dataTransferForEC2": {                                          // see DT section
    "value": [
      {"entryType": "INBOUND",      "value": "",  "unit": "tb_month", "fromRegion": ""},
      {"entryType": "OUTBOUND",     "value": "",  "unit": "tb_month", "toRegion":   ""},
      {"entryType": "INTRA_REGION", "value": "",  "unit": "tb_month"}
    ]
  }
}
```

## Pricing strategy values

| User intent | calculationComponents.pricingStrategy.value |
|---|---|
| On-Demand 100% util | `{selectedOption: "on-demand", term: "1 year", utilizationValue: "100", utilizationUnit: "%Utilized/Month"}` |
| Standard RI 1Y All Upfront | `{selectedOption: "standard", term: "1 Year", upfrontPayment: "All", model: "standard"}` |
| Standard RI 1Y No Upfront | `{selectedOption: "standard", term: "1 Year", upfrontPayment: "None", model: "standard"}` |
| Standard RI 1Y Partial Upfront | `{selectedOption: "standard", term: "1 Year", upfrontPayment: "Partial", model: "standard"}` |
| Standard RI 3Y All Upfront | `{selectedOption: "standard", term: "3 Year", upfrontPayment: "All", model: "standard"}` |
| Standard RI 3Y No Upfront | `{selectedOption: "standard", term: "3 Year", upfrontPayment: "None", model: "standard"}` |
| Standard RI 3Y Partial Upfront | `{selectedOption: "standard", term: "3 Year", upfrontPayment: "Partial", model: "standard"}` |
| Convertible RI 1Y/3Y | replace `model: "convertible"`; same `upfrontPayment` options |

For Compute Savings Plans and EC2 Instance Savings Plans the `pricingStrategy.value.selectedOption` is `"compute-savings-plans"` or `"ec2-instance-savings-plans"` with additional `term` / `upfrontPayment` keys. Capture a HAR before promising those — fields haven't been validated end-to-end here.

## Pricing API filters

Run `scripts/pricing_client.py get-products` with these filters per pricing model.

### On-Demand compute

```
--service-code AmazonEC2
--filter instanceType=<type>
--filter operatingSystem=<Linux|Windows|RHEL|SUSE>
--filter regionCode=<region>
--filter tenancy=Shared
--filter preInstalledSw=NA
--filter capacitystatus=Used
--filter "licenseModel=No License required"
```

The matching SKU has exactly one OnDemand priceDimension; `price_per_unit` is the hourly rate.

### Reserved Instances (Standard / Convertible, 1yr / 3yr)

Same filters as above. The returned SKU includes Reserved terms keyed by `LeaseContractLength` (`1yr`/`3yr`), `PurchaseOption` (`No Upfront`/`Partial Upfront`/`All Upfront`), and `OfferingClass` (`standard`/`convertible`). Pick the matching combination. RI rates have two priceDimensions:
- one in `Hrs` — recurring hourly charge (multiply by 730)
- one in `Quantity` — upfront one-time charge

### EBS storage (gp3)

```
--service-code AmazonEC2
--filter productFamily=Storage
--filter regionCode=<region>
--filter volumeApiName=gp3
```

Single OnDemand `GB-Mo` priceDimension. Multiply by `storageAmount` × instance count.

For other volume types: `volumeApiName=gp2|io1|io2|st1|sc1|standard`.

### Snapshot storage (per GB-month, copies the EBS region rate)

```
--service-code AmazonEC2
--filter productFamily="Storage Snapshot"
--filter regionCode=<region>
```

### EC2 data transfer (outbound to internet, tiered)

```
--service-code AWSDataTransfer
--filter fromLocation=<regionName>
--filter toLocationType=External
--filter transferType=AWS Outbound
```

Returns multiple priceDimensions with `begin_range`/`end_range` for the standard 10 TB / 40 TB / 100 TB / 350 TB tiers. Walk the user's outbound volume across the bands.

## Multipliers / formula

```
monthly_compute  = on_demand_hourly * 730 * count * (utilization_pct / 100)
monthly_ebs      = ebs_per_gb_month * storage_gb * count
monthly_snap     = snap_per_gb_month * storage_gb * snapshots_per_month   # rough; the SPA is more nuanced
monthly_dt_out   = sum over tiers of (gb_in_tier * tier_price)
serviceCost.monthly = monthly_compute + monthly_ebs + monthly_snap + monthly_dt_out
serviceCost.upfront = (RI all/partial-upfront upfront amount * count) if applicable, else 0
```

For RI 1yr All Upfront the upfront charge is the entire term cost; the hourly Hrs rate is 0. For Partial Upfront, both pieces are non-zero. For No Upfront, the upfront is 0 and Hrs carries the full rate.

## configSummary template

Match the captured style so the saved estimate displays normally:

```
Tenancy (Shared Instances), Operating system (<OS display>), Workload (Consistent, Number of instances: <N>), Advance EC2 instance (<type>), Pricing strategy (<strategy display>), Enable monitoring (<enabled|disabled>), EBS Storage amount (<N> GB), DT Inbound: <Not selected|N TB per month>, DT Outbound: <...>, DT Intra-Region: (<N> TB per month)
```

## Defaults to apply when the user is silent

| Field | Default | Why |
|---|---|---|
| tenancy | shared | Matches the calculator's UI default |
| selectedOS | linux | Cheapest baseline; flag this in the breakdown so user can correct |
| workloadSelection | consistent | Most common pattern |
| workload count | 1 | One instance |
| pricingStrategy | on-demand 100% util | No commitment risk |
| storage | 100 GB gp3 | Modest default |
| snapshotFrequency | 0 | Disabled |
| detailedMonitoring | false | Disabled |
| dataTransfer | all `""` (empty) | Calculator treats blank as 0 |

## Captured working example

`/home/fahadmustafa/src/aws-calc/poc/sample_input.json` (from `aws-calc` repo) holds two ec2Enhancement entries — one OnDemand t3.small Windows + 500 GB gp3, one Standard RI 3yr No Upfront r5.large Linux + 100 GB gp3. Both verified to round-trip.

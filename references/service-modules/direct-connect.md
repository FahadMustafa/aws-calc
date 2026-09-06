# AWS Direct Connect (`awsDirectConnect`)

`serviceCode` is `awsDirectConnect`, `estimateFor` is `template`. Flat line item, no `subServices` array. Critical quirk: **the `region` field is essentially decorative — the `port:Direct Connect Location` value inside `columnFormIPM` is what drives pricing.** Port rates vary by physical Direct Connect colocation site, not by AWS region. A user can have a port at "165 Halsey Street, Newark, NJ" with the line item `region: "eu-west-1"`; pricing follows Newark, not Ireland.

## Line-item header

```json
{
  "serviceCode":  "awsDirectConnect",
  "estimateFor":  "template",
  "version":      "0.0.60",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Direct Connect",
  "description":  null,
  "serviceCost":  { "monthly": <computed> },
  "configSummary": "<see template below>"
}
```

## calculationComponents (verified shape)

```jsonc
{
  "columnFormIPM": {
    "value": [
      {
        "Number of Ports":              {"value": "2"},
        "port:Capacity":                {"value": "100G"},        // "1G" | "10G" | "100G" — also "50Mbps", "200Mbps", "500Mbps", "1G", "2G", "5G" for hosted
        "port:Connection Type":         {"value": "Dedicated"},   // "Dedicated" | "Hosted"
        "port:Direct Connect Location": {"value": "165 Halsey Street, Newark, NJ"}
      }
      // one row object per (capacity, type, location) group; add another row to mix port profiles
    ]
  },
  "dataTransferOut": {"value": "10", "unit": "gb|NA"},   // GB/month outbound from AWS to on-prem via DX
  "datatransferin":  {"value": "10", "unit": "gb|NA"},   // GB/month inbound; free, but the field is still sent
  "utilization":     {"value": "730", "unit": "hoursPerMonth"}    // billable hours per month per port; default 730
}
```

Key-name and shape quirks to copy verbatim:
- `datatransferin` is **all lowercase**, while `dataTransferOut` is camelCase — single inconsistency the SPA validates literally.
- `columnFormIPM` (no suffix) at the top level, unlike Directory Service which uses suffixed variants (`columnFormIPM_MicrosoftAD`, `columnFormIPM_SharedMicrosoftAD`). Different module, different convention.
- Row-object keys with `port:` prefix (`port:Capacity`, `port:Connection Type`, `port:Direct Connect Location`) — preserve the colon and the space inside the value.
- `port:Direct Connect Location` is a free-form string like `"165 Halsey Street, Newark, NJ"` — the SPA validates against a fixed enumeration of DX locations; use the exact display string the AWS console shows for the chosen site.
- `utilization` defaults to `"730"` (full month). Drop to lower values only if the user is modeling partial-month or scheduled port enablement, which is unusual.

## Pricing API filters

```
--service-code AWSDirectConnect
--filter regionCode=<region>     # the AWS region, NOT the DX location
```

Then filter by `usagetype` and `productFamily`. Look for:
- **Port-hour SKUs** by `usagetype` — they encode location and capacity (e.g. `USE1-DCPortUsage:DDC-100GE` for a 100G dedicated port homed to a us-east-1-adjacent location).
- **Data transfer out SKUs** by `productFamily=Data Transfer` + `transferType=AWS Outbound (DX)` — rates differ by source AWS region and destination DX location.

`get-attribute-values --service-code AWSDirectConnect --attribute usagetype` enumerates port and DT SKUs together. The mapping from `port:Direct Connect Location` (display string) to the AWS region used in the `usagetype` prefix is not exposed by the Pricing API — keep a side table or scrape the AWS DX locations page once when adding a new location.

## Multipliers / formula

```
# Per port-row in columnFormIPM
port.monthly  = numberOfPorts * utilization * port_per_hour_rate(capacity, type, location)

# Data transfer
dt_out.monthly = dataTransferOut_GB * dx_dt_out_per_gb(source_region, dx_location)
dt_in          = 0                                                                     # inbound is free

serviceCost.monthly = sum(port.monthly over rows) + dt_out.monthly
```

Verified at the Newark, NJ location: 2 × 100G Dedicated ports, 730 hours, 10 GB out, 10 GB in → captured `serviceCost.monthly: $32,850.28`. Math:
```
port           = 2 * 730 * $22.50  = $32,850.00            # US 100G dedicated port hourly
dt_out         = 10 * ~$0.028       = $0.28                 # eu-west-1 source → Newark DX out
total          = $32,850.28                                 # ✓ matches exactly
```

The $0.028/GB DT rate above is back-calculated from the capture (line item shows total $32,850.28, port subtotal $32,850.00). Confirm via Pricing API before quoting other source-region / DX-location combos — DT out rates vary substantially across pairings.

> **CAVEAT — do not quote from the baked-in table.** The port-hour rates ($22.50/h for 100G, $0.30/h for 1G) vary by DX colocation/location, and the $0.028/GB DX egress was inferred from a tiny **10 GB** capture where rounding noise dominates the residual ($0.28 / 10 GB), so the per-GB figure is essentially noise. **ALWAYS** resolve both SKUs live before quoting: the port-hour SKU (`usagetype` like `*-DCPortUsage:*`, keyed to the chosen capacity and DX location) and the DX outbound-DT SKU (`productFamily=Data Transfer`, `transferType=AWS Outbound (DX)`, per source AWS region / DX location). Never quote from the hardcoded numbers above.

## configSummary template

Match the captured phrasing exactly — semicolon-free, parenthesized values, free DT-in noted in line:

```
Number of ports (<N>), Location (<Direct Connect location string>), Port type (<Dedicated|Hosted>), Port capacity (<1G|10G|100G|...>), Data transfer out (<X> GB), Data transfer in (free) (<X> GB)
```

For multi-row port configurations: the SPA concatenates per-row segments with space separators. Re-derive from a multi-row capture before quoting mixed-capacity setups.

## Defaults

| Field | Default | Why |
|---|---|---|
| Number of Ports | "1" | Single port is the minimum; ask if multi-port redundancy is needed |
| port:Capacity | none — **ask** | Cost varies 100x across 1G ($0.30/h) vs 100G ($22.50/h); never default |
| port:Connection Type | "Dedicated" | More common for enterprise DX; ask if hosted (sub-1G) is needed |
| port:Direct Connect Location | none — **ask** | Hundreds of locations with different rates; never guess. If unsure, use the closest geographic enum value (NYC area, Frankfurt, Tokyo, etc.) |
| dataTransferOut | "0" (GB/month) | Set only if user mentions outbound DX traffic volume |
| datatransferin | match `dataTransferOut` | Free regardless; the SPA still wants the field present |
| utilization | "730" (hoursPerMonth) | Full month default — only lower for partial-month enablement |

If the user mentions "Direct Connect" without a location, **ask**. If they mention a capacity without a connection type, default to Dedicated for 1G+ and Hosted for sub-1G capacities — but flag the assumption in the breakdown.

## Verification

- Captured HAR: `captures/calculator.aws_new_4.har` (local capture, not in repo) → `captures/saveAs/per-service/awsDirectConnect.json` (region `eu-west-1` field but **priced at Newark, NJ**).
- Port-hour math matches captured `$32,850.28` exactly using $22.50/h for the 2 × 100G Dedicated ports at Newark.
- Data transfer math infers $0.028/GB for `eu-west-1` source → Newark DX out from the residual $0.28; **re-derive from a higher-DT capture to confirm**.
- **Hosted ports** (sub-1G capacities) are NOT covered by this capture — the shape should be identical, but the per-hour rates and capacity enumeration differ. Capture a hosted-port HAR before quoting.
- **Multi-row `columnFormIPM` configurations** (mixed capacities or locations on the same line item) are not captured — the configSummary concatenation rule above is inferred.
- The region/location decoupling is a real footgun: do not assume the `region` field controls pricing.

- **Form 0.0.59 → 0.0.60 (2026-09-06).** Diffed against the live form definition (`data/awsDirectConnect/en_US.json`, version `0.0.60`). Template `template` defines exactly `columnFormIPM`, `utilization` (form default `730`), `dataTransferOut`, `datatransferin` — including the lowercase `datatransferin` quirk documented above. **No cc-relevant change**: fields added: none, renamed: none, removed: none. Version pin bumped only; port rates and the inferred $0.028/GB DX egress residual remain as caveated above.

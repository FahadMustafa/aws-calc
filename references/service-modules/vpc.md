# VPC (`amazonVirtualPrivateCloud` group)

VPC is a **group** service: the line item has `subServices: [...]` for each priced VPC feature (VPN, Transit Gateway, NAT Gateway, etc.). The VPC itself is free; only its priced add-ons appear in the body.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| `publicIpv4Address` (idle + in-use) | capture-verified | `references/fixtures/amazonVirtualPrivateCloud.json` — $73.00 matches exactly |
| `awsPrivateLinkVpc` (endpoints x AZs x GB) | capture-verified | `references/fixtures/amazonVirtualPrivateCloud.json` — $804.00 computed vs $803.10 captured (endpoint rate nuance) |
| `dataTransferVpc` outbound + intra-region (2x cross-AZ) | capture-verified | `references/fixtures/amazonVirtualPrivateCloud.json` — $1126.40 = $921.60 out + $204.80 intra ($0.02/GB) |
| `vpnConnectionVpc` (Site-to-Site VPN) — cc shape captured, hourly formula not reconciled | capture-verified | `references/fixtures/amazonVirtualPrivateCloud.json` ($73/mo line; tunnel-hour nuance unresolved) |
| `transitGatewayVpc` | inferred | shape documented from the capture/bundle; no reconciled cost in this module |
| `networkAddressTranslationNatGatewayVpc` (NAT Gateway) | inferred | form 0.0.19 partial shape — missing `regionalNatGateway*` / `_generated_*`; refuse and offer a HAR |
| `_generated_*` NAT token values | inferred | catalog probe 2026-07-13 returned nothing; HAR capture is the only route |
| Other VPC sub-services (`gatewayLoadBalancerVpc`, `ipamVpc`, `networkAccessAnalyzerVpc`, `reachabilityAnalyzerVpc`, `trafficMirroringVpc`, `vpcRouteServer`, `cloudWan`) | inferred | manifest key names only — capture a HAR before pricing |

## Group-level header

```json
{
  "serviceCode":  "amazonVirtualPrivateCloud",
  "estimateFor":  "virtualPrivateCloudSubServiceSelector",
  "version":      "0.0.101",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Virtual Private Cloud (VPC)",
  "description":  null,
  "subServices":  [ ... ],
  "serviceCost":  { "monthly": <sum>, "upfront": 0 },
  "configSummary": "<feature summaries joined>"
}
```

## subServices

### Site-to-Site VPN (`vpnConnectionVpc`)

```jsonc
{
  "serviceCode":  "vpnConnectionVpc",
  "estimateFor":  "VPNConnection",
  "version":      "0.0.19",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "numberOfSiteToSiteVPNConnections":   {"value": "2"},
    "averageDurationForEachConnection":   {"value": "24", "unit": "perDay"},   // hours/day
    "vpnConnection_numberOfWorkDays":     {"value": "22"},
    "vpnConnection_clientAvgDuration":    {"value": "10", "unit": "perDay"}    // client VPN; "0" disables
  },
  "serviceCost": { "monthly": <computed>, "upfront": 0 }
}
```

### Transit Gateway (`transitGatewayVpc`)

```jsonc
{
  "serviceCode":  "transitGatewayVpc",
  "estimateFor":  "transitGateway",
  "version":      "0.0.19",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "numberOfTransitGatewayAttachments":         {"value": "10"},
    "dataProcessedPerTransitGatewayAttachment":  {"value": "10", "unit": "gb|month"}
  },
  "serviceCost": { "monthly": <computed>, "upfront": 0 }
}
```

### NAT Gateway (`networkAddressTranslationNatGatewayVpc`) — NOT yet supported, refuse until HAR-captured

The live form (`version 0.0.19`) is more complex than the two verified sub-services. Its real input set is **not** the simple `{numberOfNATGateways, dataProcessedPerNATGateway}` shape previously guessed here — inspecting the current service definition shows the primary count field is actually `numberOfGateways` (not `numberOfNATGateways`), plus a separate **regional** NAT Gateway block (`regionalNatGatewayCount`, `regionalNatGatewayAzCount`, `regionalNatGatewayDataProcessed`, …) and several `networkAddressTranslationNatGateway_generated_*` fields whose semantics are not captured.

```jsonc
{
  "serviceCode":  "networkAddressTranslationNatGatewayVpc",
  "estimateFor":  "natGateway",
  "version":      "0.0.19",            // confirmed live; cc shape below is INCOMPLETE
  "region":       "<code>",
  "calculationComponents": {
    "numberOfGateways":            {"value": "1"},                       // confirmed field name (was wrongly "numberOfNATGateways")
    "dataProcessedPerNATGateway":  {"value": "100", "unit": "gb|month"}  // confirmed; but other required fields are missing
  }
}
```

**Do not emit a NAT Gateway line from this partial shape.** It is missing the `regionalNatGateway*` and `_generated_*` fields the form requires, so a saved estimate will error on the recipient's "Update" (the SPA reports the service as incompatible with its inputs). Refuse the NAT Gateway line and offer to capture a HAR to complete the module. Pricing API filters are correct (below) for when the shape is captured. Same rule for any other unverified VPC sub-service.

**Resolving the `networkAddressTranslationNatGateway_generated_*` tokens — try the public catalog FIRST.** Per `references/opaque-tokens.md`, before capturing a HAR you should first try the world-readable meteredUnitMaps catalog via `scripts/resolve_token.py`. Probe outcome (probed 2026-07-13):

- `python3 scripts/resolve_token.py vpc` → **HIT** (200; 105 regions, 38 friendly→token mappings) but the `vpc` catalog contains **no NAT Gateway entries at all** and none of the `networkAddressTranslationNatGateway_generated_*` field names. (Consistent with NAT pricing living under `AmazonEC2`, not `AmazonVPC` — see the pricing filter below.)
- `natgateway`, `nat`, `amazonvpc` slugs → **MISS** (404).

So the catalog does not resolve these tokens today. Note also that `_generated_N` suffixes are the SPA's **form-field identifiers** (auto-numbered form widgets), not the 43-char `RegionlessRateCode` values the catalog indexes — a different token class the meteredUnitMaps catalog does not enumerate. **HAR capture remains the fallback** for the NAT Gateway shape. Still try the catalog first when the slug list grows; re-probe rather than assuming.

### Data Transfer (`dataTransferVpc`)

```jsonc
{
  "serviceCode":  "dataTransferVpc",
  "estimateFor":  "dataTransfer",
  "version":      "0.0.9",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "dataTransfer": {
      "value": [
        { "entryType": "INBOUND",      "fromRegion": "",         "unit": "tb_month", "value": "0"  },
        { "entryType": "OUTBOUND",     "toRegion":   "External", "unit": "tb_month", "value": "10" },
        { "entryType": "INTRA_REGION",                            "unit": "tb_month", "value": "10" }
      ]
    }
  },
  "serviceCost": { "monthly": <computed> }
}
```

`calculationComponents.dataTransfer.value` is an **array** of entry objects, not a single value — copy this shape exactly. Each entry has `entryType` ∈ `INBOUND` | `OUTBOUND` | `INTRA_REGION`, plus `toRegion` (for OUTBOUND: `"External"` for public internet egress, or an AWS region code like `"us-east-1"` for inter-region transfer) or `fromRegion` (for INBOUND, currently always `""`), `unit: "tb_month"`, and a string `value`. Use `"0"` for entries the user did not specify; INBOUND data transfer is free, but the entry is still present in the saveAs body.

### PrivateLink / Interface VPC Endpoints (`awsPrivateLinkVpc`)

```jsonc
{
  "serviceCode":  "awsPrivateLinkVpc",
  "estimateFor":  "awsPrivateLink",
  "version":      "0.0.17",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "numberOfInterfaceVPCEndpointsPerRegion":     {"value": "10"},
    "numberOfAvailabilityZonesEndpointsDeployed": {"value": "10"},
    "dataProcessedByEachVPCENIAZ":                {"value": "10", "unit": "gb|month"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

This is **per-endpoint** × **per-AZ** billing. `numberOfAvailabilityZonesEndpointsDeployed` is the AZ count applied to every endpoint (the SPA doesn't allow per-endpoint AZ counts in this form); `dataProcessedByEachVPCENIAZ` is GB/month per ENI per AZ. The total endpoint-hours billed = `endpoints * AZs * 730`.

### Public IPv4 Addresses (`publicIpv4Address`)

```jsonc
{
  "serviceCode":  "publicIpv4Address",
  "estimateFor":  "ipv4publicaddress",
  "version":      "0.0.17",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "numberOfInusepublicipv4address": {"value": "10"},
    "numberOfIdlepublicipv4address":  {"value": "10"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

Field-name quirks to copy verbatim: both keys are all-lowercase after the camelCase prefix (`Inusepublicipv4address`, `Idlepublicipv4address`) — no separators or capitals inside `publicipv4address`. The SPA matches literally.

In-use and idle IPs are billed at the **same** $0.005/IP-hour rate — the SPA splits them only because the AWS billing console reports them as separate line items.

### Other VPC sub-services seen in the manifest

`gatewayLoadBalancerVpc`, `ipamVpc`, `networkAccessAnalyzerVpc`, `reachabilityAnalyzerVpc`, `trafficMirroringVpc`, `vpcRouteServer`, `cloudWan`. The serviceCode is the JSON key name; estimateFor varies. Capture a HAR and add a section above before pricing.

## Pricing API filters

### Site-to-Site VPN

```
--service-code AmazonVPC
--filter "groupDescription=Site-to-Site VPN"
--filter regionCode=<region>
```

Returns OnDemand `Hrs` rate per VPN connection-hour.

### Transit Gateway

```
--service-code AmazonVPC
--filter "groupDescription=Transit Gateway"
--filter regionCode=<region>
```

Two SKUs typically: per-attachment-hour and per-GB processed.

### NAT Gateway

```
--service-code AmazonEC2
--filter productFamily="NAT Gateway"
--filter regionCode=<region>
```

Two SKUs: per-NAT-Gateway-hour and per-GB processed.

### Data Transfer

Inter-region and internet egress live in the EC2 service code, not AmazonVPC:

```
--service-code AmazonEC2
--filter productFamily="Data Transfer"
--filter regionCode=<region>
```

Filter further by `transferType` to get the right SKU: `AWS Outbound` (internet egress, tiered by GB/month), `InterRegion Outbound` (between regions; `toRegionCode` selects destination), `IntraRegion` (cross-AZ within the same region).

**Intra-region (cross-AZ) is billed in both directions.** The `IntraRegion` SKU rate (~$0.01/GB) is charged once for egress *and* once for ingress across AZs, so the effective rate is **2×** the per-GB SKU rate. Verified against the capture: `dataTransferVpc` = $1126.40 = $921.60 outbound + **$204.80 intra-region**, and $204.80 / 10 240 GB = **$0.02/GB** = $0.01 × 2. Multiply intra-region GB by `2 × intra_region_per_gb`.

### PrivateLink / Interface VPC Endpoints

```
--service-code AmazonVPC
--filter groupDescription="VPC Endpoints"
--filter regionCode=<region>
```

Two SKUs: per-VPC-endpoint-hour (`VpcEndpoint-Hours`) and per-GB processed (`VpcEndpoint-Bytes`).

### Public IPv4 Addresses

```
--service-code AmazonVPC
--filter groupDescription="Public IPv4 Address"
--filter regionCode=<region>
```

Single SKU: `PublicIPv4:InUseAddress` (per-hour). The same rate applies to idle and in-use IPs.

`get-attribute-values --service-code AmazonVPC --attribute groupDescription` lists the valid VPC `groupDescription` strings.

## Multipliers / formula

```
S2S VPN monthly        = vpn_per_hour * connection_count * vpn_hours_per_month
                         where vpn_hours_per_month ~= averageDurationForEachConnection.value
                                                       * vpnConnection_numberOfWorkDays.value
TGW attachment monthly = tgw_attach_per_hour * 730 * numberOfTransitGatewayAttachments
TGW data monthly       = tgw_per_gb * dataProcessedPerTransitGatewayAttachment * numberOfTransitGatewayAttachments
# NAT Gateway — pricing-reference ONLY. Do NOT emit a NAT line from this (see the
# NAT Gateway sub-service section: the cc shape is incomplete, refuse + offer HAR).
# Field name is numberOfGateways (NOT the old wrong numberOfNATGateways).
NAT GW hourly monthly  = nat_per_hour * 730 * numberOfGateways
NAT GW data monthly    = nat_per_gb * dataProcessedPerNATGateway * numberOfGateways

# Data transfer — walk the entries array, apply the per-entryType SKU + tier
data_xfer monthly      = sum over entries of:
    if entryType == "OUTBOUND" and toRegion == "External":
        tiered_outbound(value_in_GB)        # AWS Outbound, first 10 TB/$0.09, etc.
    elif entryType == "OUTBOUND":
        inter_region_outbound(value, toRegion) * value_in_GB
    elif entryType == "INTRA_REGION":
        intra_region_per_gb * value_in_GB * 2   # cross-AZ is billed in BOTH directions ($0.01/GB each way) -> $0.02/GB effective
    # INBOUND is free

PrivateLink hourly     = privatelink_per_hour * 730
                                * numberOfInterfaceVPCEndpointsPerRegion
                                * numberOfAvailabilityZonesEndpointsDeployed
PrivateLink data       = privatelink_per_gb
                                * numberOfInterfaceVPCEndpointsPerRegion
                                * numberOfAvailabilityZonesEndpointsDeployed
                                * dataProcessedByEachVPCENIAZ        # GB/month

Public IPv4 monthly    = (numberOfInusepublicipv4address + numberOfIdlepublicipv4address)
                                * 730 * public_ipv4_per_hour_rate    # $0.005/IP-hour

sub.serviceCost.monthly = the relevant sum
group.serviceCost.monthly = sum of all sub.serviceCost.monthly
```

Verified at eu-west-1:
- `awsPrivateLinkVpc` with 10 endpoints × 10 AZs × 10 GB/month → `10 * 10 * 730 * $0.011 + 10 * 10 * 10 * $0.01 = $803.00 + $1.00 = $804.00` against captured `$803.10` (within $0.90 — likely a $0.0109/h endpoint rate, not flat $0.011).
- `publicIpv4Address` with 10 idle + 10 in-use → `(10 + 10) * 730 * $0.005 = $73.00` against captured `$73.00`. **Matches exactly.**

The captured estimate's S2S VPN priced at $73/mo for 2 connections × 24h × 22 days — that's roughly `0.05 * 2 * 24 * 22 ≈ $52.80/mo` for the connection-hour rate, plus tunnel-hours; the SPA's exact formula has nuance. Use the SPA's value as ground truth when possible (re-derive after capture).

## Defaults

| Field | Default |
|---|---|
| numberOfSiteToSiteVPNConnections | "0" (no VPN) |
| numberOfTransitGatewayAttachments | "0" (no TGW) |
| numberOfGateways (NAT GW) | "0" — pricing-reference only; the NAT sub-service is NOT emittable (refuse + offer HAR, see its section). Field name is `numberOfGateways`, not the old wrong `numberOfNATGateways`. |
| dataTransfer.value (the array) | omit `dataTransferVpc` entirely if the user did not mention data transfer; otherwise include all three entryTypes with `"0"` for the ones the user did not specify |
| numberOfInterfaceVPCEndpointsPerRegion | "0" (omit `awsPrivateLinkVpc` entirely if not mentioned) |
| numberOfAvailabilityZonesEndpointsDeployed | match the user's `numberOfAvailabilityZones` for the VPC; default `"2"` if unspecified |
| dataProcessedByEachVPCENIAZ | "1" (GB/month per ENI per AZ) — low but non-zero; flag the assumption |
| numberOfInusepublicipv4address | "0" (omit `publicIpv4Address` sub-service if not mentioned) | Only include when user mentions Elastic IPs or public IPv4 addresses |
| numberOfIdlepublicipv4address | "0" | Same rate as in-use; split only because the billing console reports them separately |

If the user mentions "Site-to-Site VPN" without a count, default to 1. If they mention "PrivateLink" or "interface endpoint(s)" without a count, default to 1 endpoint × `numberOfAvailabilityZonesEndpointsDeployed` AZs.

## configSummary template

```
Working days per month (<N>), Number of Site-to-Site VPN Connections (<N>) Number of Transit Gateway attachments (<N>)
```

(Match the captured style; the SPA may render odd phrasing if you deviate.)

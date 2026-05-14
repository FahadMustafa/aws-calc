# VPC (`amazonVirtualPrivateCloud` group)

VPC is a **group** service: the line item has `subServices: [...]` for each priced VPC feature (VPN, Transit Gateway, NAT Gateway, etc.). The VPC itself is free; only its priced add-ons appear in the body.

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

### NAT Gateway (`networkAddressTranslationNatGatewayVpc`) — fields inferred, verify before use

```jsonc
{
  "serviceCode":  "networkAddressTranslationNatGatewayVpc",
  "estimateFor":  "natGateway",
  "version":      "<TBD>",
  "region":       "<code>",
  "calculationComponents": {
    "numberOfNATGateways":               {"value": "1"},
    "dataProcessedPerNATGateway":        {"value": "100", "unit": "gb|month"}
  }
}
```

(Capture a HAR before promising NAT Gateway, PrivateLink, or other VPC sub-services. Field names follow the pattern of the verified two but should be confirmed.)

### Other VPC sub-services seen in the manifest

`awsPrivateLinkVpc`, `dataTransferVpc`, `gatewayLoadBalancerVpc`, `ipamVpc`, `networkAccessAnalyzerVpc`, `reachabilityAnalyzerVpc`, `trafficMirroringVpc`, `vpcRouteServer`, `cloudWan`, `publicIpv4Address`. The serviceCode is the JSON key name; estimateFor varies. Capture a HAR and add a section above before pricing.

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

`get-attribute-values --service-code AmazonVPC --attribute groupDescription` lists the valid VPC `groupDescription` strings.

## Multipliers / formula

```
S2S VPN monthly        = vpn_per_hour * connection_count * vpn_hours_per_month
                         where vpn_hours_per_month ~= averageDurationForEachConnection.value
                                                       * vpnConnection_numberOfWorkDays.value
TGW attachment monthly = tgw_attach_per_hour * 730 * numberOfTransitGatewayAttachments
TGW data monthly       = tgw_per_gb * dataProcessedPerTransitGatewayAttachment * numberOfTransitGatewayAttachments
NAT GW hourly monthly  = nat_per_hour * 730 * numberOfNATGateways
NAT GW data monthly    = nat_per_gb * dataProcessedPerNATGateway * numberOfNATGateways

sub.serviceCost.monthly = the relevant sum
group.serviceCost.monthly = sum of all sub.serviceCost.monthly
```

The captured estimate's S2S VPN priced at $73/mo for 2 connections × 24h × 22 days — that's roughly `0.05 * 2 * 24 * 22 ≈ $52.80/mo` for the connection-hour rate, plus tunnel-hours; the SPA's exact formula has nuance. Use the SPA's value as ground truth when possible (re-derive after capture).

## Defaults

| Field | Default |
|---|---|
| numberOfSiteToSiteVPNConnections | "0" (no VPN) |
| numberOfTransitGatewayAttachments | "0" (no TGW) |
| numberOfNATGateways | "0" (no NAT GW) |

If the user mentions "Site-to-Site VPN" without a count, default to 1.

## configSummary template

```
Working days per month (<N>), Number of Site-to-Site VPN Connections (<N>) Number of Transit Gateway attachments (<N>)
```

(Match the captured style; the SPA may render odd phrasing if you deviate.)

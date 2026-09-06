# Elastic Load Balancing (`elasticLoadBalancing` group)

ELB is a **group** service: the line item has `subServices: [...]` for each priced load-balancer type. The group `serviceCost.monthly` is the sum of its sub-services. The classic Load Balancer (CLB) is not in this form — only ALB, NLB, and GWLB.

## Group-level header

```json
{
  "serviceCode":  "elasticLoadBalancing",
  "estimateFor":  "elasticLoadBalancingGroups",
  "version":      "0.0.28",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Elastic Load Balancing",
  "description":  null,
  "subServices":  [ ... ],
  "serviceCost":  { "monthly": <sum> },
  "configSummary": "<joined sub-service summaries>"
}
```

## subServices

### Application Load Balancer (`applicationLoadBalancer`)

```jsonc
{
  "serviceCode":  "applicationLoadBalancer",
  "estimateFor":  "template_0",
  "version":      "0.0.28",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "numberOfApplicationLoadBalancers":                 {"value": "1"},
    "averageNumberOfNewConnectionsPerALB":              {"value": "10", "unit": "perSecond"},
    "averageConnectionDuration":                        {"value": "10", "unit": "sec"},
    "averageNumberOfRequestsPerALBPerSecond":           {"value": "10"},
    "averageNumberOfRuleEvaluationsPerRequest":         {"value": "10"},
    "sizeOfDataProcessedForEC2InstanceAndIPAddressTargets": {"value": "10", "unit": "gb|hour"},
    "sizeOfBytesProcessedForLambdaFunctionTargets":     {"value": "10", "unit": "gb|hour"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

LCU dimensions (the SPA takes the max across these per hour, then multiplies by the LCU rate):

| Dimension | Capacity per LCU |
|---|---|
| New connections | 25 connections / second |
| Active connections | 3,000 connections / minute |
| Processed bytes — EC2/IP targets | 1 GB / hour |
| Processed bytes — Lambda targets | 0.4 GB / hour |
| Rule evaluations | `max(0, ruleEvals - 10) * requestsPerSecond / 1000` LCUs |

### Network Load Balancer (`networkLoadBalancer`)

```jsonc
{
  "serviceCode":  "networkLoadBalancer",
  "estimateFor":  "template_0",
  "version":      "0.0.21",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "numberOfNetworkLoadBalancers":            {"value": "1"},
    "sizeOfProcessedDataPerNLBForTCP":         {"value": "10", "unit": "gb|hour"},
    "averageNumberOfNewTCPConnections":        {"value": "10", "unit": "perSecond"},
    "averageTCPConnectionDuration":            {"value": "10", "unit": "sec"},
    "sizeOfDataProcessedPerNLBForUDP":         {"value": "10", "unit": "gb|hour"},
    "averageNumberOfNewUDPFlows":              {"value": "10", "unit": "perSecond"},
    "averageUDPFlowduration":                  {"value": "10", "unit": "sec"},
    "sizeOfDataProcessedPerNLBForTLS":         {"value": "10", "unit": "gb|hour"},
    "averageNumberOfNewTLSConnections":        {"value": "10", "unit": "perSecond"},
    "averageDurationForTLSConnection":         {"value": "10", "unit": "sec"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

Field-name quirks to copy verbatim: `averageUDPFlowduration` (lowercase `d`, no space) and `sizeOfProcessedDataPerNLBForTCP` (note `Processed`, while the UDP/TLS keys use `DataProcessed`). The SPA matches these literally.

NLCU dimensions are evaluated per protocol then summed (TCP + UDP + TLS), unlike ALB's single max:

| Protocol | Capacity per NLCU |
|---|---|
| TCP — new flows | 800 / second |
| TCP — active flows | 100,000 |
| TCP — processed bytes | 1 GB / hour |
| UDP — new flows | 400 / second |
| UDP — active flows | 50,000 |
| UDP — processed bytes | 1 GB / hour |
| TLS — new connections | 50 / second |
| TLS — active connections | 9,500 |
| TLS — processed bytes | 1 GB / hour |

### Gateway Load Balancer (`gatewayLoadBalancer`)

```jsonc
{
  "serviceCode":  "gatewayLoadBalancer",
  "estimateFor":  "template_0",
  "version":      "0.0.37",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "numberOfGatewayAZs":                  {"value": "1"},
    "numberOfGatewayLoadBalancerEndpoints":{"value": "1"},
    "sizeOfProcessedDataPerGLB":           {"value": "10", "unit": "gb|hour"},
    "averageNumberOfNewGLBConnections":    {"value": "10", "unit": "perSecond"},
    "averageGLBConnectionDuration":        {"value": "10", "unit": "sec"}
  },
  "serviceCost": { "monthly": <computed> }
}
```

GLBCU dimensions (single max, like ALB):

| Dimension | Capacity per GLBCU |
|---|---|
| New connections | 600 / second |
| Active connections | 60,000 |
| Processed bytes | 1 GB / hour |

GWLB has three priced components — AZ-hours, GLBCUs, and **separately** endpoint-hours + endpoint data-processed.

## Pricing API filters

Service code is `AWSELB` for all three load-balancer types. Use the `groupDescription` attribute to scope.

### Application Load Balancer

```
--service-code AWSELB
--filter groupDescription="Application Load Balancer"
--filter regionCode=<region>
```

Returns two SKUs: `Hrs` (load-balancer-hour) and `LCU-Hrs`.

### Network Load Balancer

```
--service-code AWSELB
--filter groupDescription="Network Load Balancer"
--filter regionCode=<region>
```

Returns `Hrs` (load-balancer-hour) and `LCU-Hrs` (the NLCU rate; AWS prices NLCUs and LCUs on separate SKUs even though the API spells both as `LCU-Hrs`).

### Gateway Load Balancer

```
--service-code AWSELB
--filter groupDescription="Gateway Load Balancer"
--filter regionCode=<region>
```

Returns `Hrs` (per-AZ hour), `LCU-Hrs` (GLBCU), `VpcEndpoint-Hrs` (endpoint hourly), and a per-GB data-processed SKU for endpoint traffic.

`get-attribute-values --service-code AWSELB --attribute groupDescription` enumerates the valid strings.

## Multipliers / formula

Constants: `HOURS_PER_MONTH = 730`.

### ALB

```
alb_bytes_lcu = sizeProcessedForEC2GbPerHour / 1
              + sizeProcessedForLambdaGbPerHour / 0.4

alb_non_bytes_lcu = max(
    newConnectionsPerSecond / 25,
    (newConnectionsPerSecond * connectionDurationSec) / 3000 / 60,      # active conns/minute
    max(0, ruleEvalsPerRequest - 10) * requestsPerSecond / 1000
)

alb_lcu_per_hour = max(alb_non_bytes_lcu, alb_bytes_lcu)

alb.monthly = numberOfALBs * 730 * (alb_per_hour + alb_lcu_per_hour * lcu_rate)
```

Verified at eu-west-1: 1 ALB, 10 req/s, 10 new conn/s, 10s dur, 10 rule evals/req, 10 GB/h EC2, 10 GB/h Lambda → bytes = 10 + 25 = 35; non-bytes = max(0.4, 0.056, 0) = 0.4; LCU = max(0.4, 35) = 35 → `1 * 730 * (0.0252 + 35 * 0.008) = $222.80`. **Matches capture exactly.** Note this differs from AWS's published per-dimension max formula in one specific way: byte counts across target types (EC2/IP + Lambda) are *summed before* the outer max, not max'd independently. Capture a second saveAs with only Lambda bytes set (zero EC2 bytes) before quoting a Lambda-target-only ALB to confirm Lambda's 0.4 GB/LCU divisor still holds standalone.

### NLB

```
nlcu_tcp = max(newTCPPerSec / 800,  activeTCP / 100000,  tcpGbPerHour / 1)
nlcu_udp = max(newUDPPerSec / 400,  activeUDP / 50000,   udpGbPerHour / 1)
nlcu_tls = max(newTLSPerSec / 50,   activeTLS / 9500,    tlsGbPerHour / 1)
nlb_nlcu_per_hour = nlcu_tcp + nlcu_udp + nlcu_tls

nlb.monthly = numberOfNLBs * 730 * (nlb_per_hour + nlb_nlcu_per_hour * nlcu_rate)
```

Verified at eu-west-1: 1 NLB, 10 each (TCP/UDP/TLS) connections-per-second, 10s duration, 10 GB/h each → each protocol's NLCU dominated by GB/h = 10 → total 30 NLCU → `1 * 730 * (0.0252 + 30 * 0.006) = $149.80`. **Matches capture exactly.**

### GWLB

```
glbcu_per_hour = max(
    newGLBPerSecond / 600,
    (newGLBPerSecond * glbConnDurationSec) / 60000 / 60,
    sizeProcessedGbPerHour / 1
)

gwlb.monthly = numberOfGatewayAZs * 730 * gwlb_per_az_hour
             + 730 * glbcu_per_hour * glbcu_rate
             + numberOfEndpoints * 730 * gwlb_endpoint_per_hour
             + numberOfEndpoints * sizeProcessedGbPerHour * 730 * gwlb_endpoint_per_gb
```

Verified at eu-west-1: 1 AZ, 1 endpoint, 10 GB/h, 10 new conn/s, 10s dur → GLBCU=10 → `730 * (0.0125 + 10 * 0.004) + 730 * 0.0125 + 7300 * 0.0035 = $9.13 + $29.20 + $9.13 + $25.55 = $73.01`. Capture says `$73.15`. Within $0.15 — rounding-tolerable.

## configSummary template

Match the captured phrasing per sub-service, then space-join across present sub-services:

```
Number of Application Load Balancers (<N>) Number of Network Load Balancers (<N>), Processed bytes per NLB for TCP (<X> GB per hour), Average number of new TCP connections (<X> per second), Average TCP connection duration (<X> seconds), Processed bytes per NLB for UDP (<X> GB per hour), Average number of new UDP Flows (<X> per second), Average UDP Flow duration (<X> seconds), Processed bytes per NLB for TLS (<X> GB per hour), Average number of new TLS connections (<X> per second), Average TLS connection duration (<X> seconds) Number of Availability Zones that Gateway Load Balancer is deployed to (<N>), Number of Gateway Load Balancer Endpoints (<N>), Total processed bytes (<X> GB per hour), Average number of new connections/flows (<X> per second), Average connection/flow duration (<X> seconds)
```

Omit a sub-service's segment entirely if its count is `"0"` — the SPA drops zero-count load balancers from the body before submit.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfApplicationLoadBalancers | "0" | Only include if the user mentions ALB / Application LB |
| numberOfNetworkLoadBalancers | "0" | Only include if the user mentions NLB / Network LB |
| numberOfGatewayLoadBalancerEndpoints | "0" | Only include if the user mentions GWLB / Gateway LB / firewall insertion |
| averageNumberOfRuleEvaluationsPerRequest | "10" | AWS default; rule evals only contribute to LCU above 10 |
| averageConnectionDuration | "60" (sec) | Reasonable typical for HTTP keep-alive — user should override for long-lived sockets |
| averageNumberOfRequestsPerALBPerSecond | "100" | Mid-range — call out the default in the breakdown |
| sizeOfDataProcessedForEC2InstanceAndIPAddressTargets | "1" GB/h | Low default; LCU is bytes-dominated for most workloads, so flag the assumption |
| sizeOfBytesProcessedForLambdaFunctionTargets | "0" GB/h | Only set if user has Lambda targets |
| sizeOfProcessedDataPerNLBForTCP / UDP / TLS | "1" GB/h each | Same caveat as ALB processed-bytes |
| averageTCPConnectionDuration / UDP / TLS | "60" (sec) | TCP long-lived; UDP/TLS shorter — adjust per workload |
| numberOfGatewayAZs | match `numberOfGatewayLoadBalancerEndpoints` | One AZ per endpoint is the typical 1:1 |

If the user mentions "load balancer" without a type, ask. ALB is the safe default only for HTTP(S); pick NLB for TCP/UDP/TLS workloads and GWLB only when the user mentions virtual appliances, IDS/IPS, or third-party firewalls.

## Verification

- Captured HAR: `captures/calculator.aws_new_3.har` (local capture, not in repo) → `captures/saveAs/per-service/elasticLoadBalancing.json` (eu-west-1, single line item, 3 sub-services).
- NLB formula reproduces the captured `$149.80` exactly.
- GWLB formula reproduces the captured `$73.15` within $0.15.
- **ALB formula reconstructs the captured `$222.80` only if the EC2 and Lambda processed-byte dimensions are summed rather than max'd with the other dimensions** — this is the working hypothesis from the single capture. Capture a second saveAs with only the Lambda byte dimension set (everything else "0"), then a third with only EC2 bytes, to confirm whether the SPA sums byte dimensions or takes the max. The published AWS LCU documentation says max-across-dimensions, so this is worth confirming before quoting tight ALB estimates.
- Classic Load Balancer (CLB) is **not** in this form — the SPA renders it under a different `serviceCode`. Don't try to slot it in here.

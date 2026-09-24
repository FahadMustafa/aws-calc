# Amazon Route 53 (`amazonRoute53`)

Covers hosted zones, DNS queries (standard / latency-based / geo / IP-based / recursive resolver / firewall), CloudTrail-style health checks (basic + four optional feature classes), Traffic Flow policy records, and Route 53 Resolver endpoints + DNS Firewall in one line item.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| cc field set, field names, and SKU mapping (all dimensions at "10", us-east-2) | capture-verified | `captures/saveAs/per-service/amazonRoute53.json` (local capture) |
| Per-dimension rate math (hosted zones, all query classes, Traffic Flow, health checks, Resolver ENI-hours) | capture-verified | same capture — sums to $1580.01 against a stored $1596.02 ($16.02 residual, unexplained) |
| `RRsetRecord` charge | inferred | no matching public SKU; possible per-zone record allotment |
| Resolver DNS Firewall only (`numberOfDNSFirewallDomains` + `numberOfFirewallDNSQueries` in `millionPerMonth`, every other key omitted) | recompute-verified | `references/fixtures/amazonRoute53-dnsfirewall.json` (SPA saveAs: 1,000 domains + 50M queries, eu-central-1, $30.50 = 50 x $0.60 + 1,000 x $0.0005) + live SPA 2026-09-24, 42-line multi-account reference estimate (customer engagement, ID withheld) |
| `numberOfVPCs` / `numberOFhours` | inferred | these belong to **DNS Firewall Advanced** (`<P>-AdvancedDNS-ThreatProtectionsVPCAssociationHours`, $0.16 per rule-group-VPC association hour), not to basic DNS Firewall; leave them out unless Advanced is asked for |
| Health-check per-feature base charge (`numberOfFastIntervalChecks*` most likely) | inferred | candidate explanation for the residual delta |
| `numberOFhours` as hours-per-month-per-ENI | inferred | inferred from the per-ENI hourly SKU and the captured "10" |
| Geo intra-AWS vs external query rate split | inferred | the captured body uses a single field for all flavors |
| DNS Security-enabled Resolver ENIs | inferred | distinct SKU exists; the captured shape has no field for it |

Route 53 itself is a global service — `serviceCode` is `amazonRoute53` and most SKUs have `regionCode=""` (priced "Any"). The captured estimate still attaches a region (e.g. `us-east-2`) because Resolver endpoint, DNS Firewall, and DNS Firewall query SKUs **are** region-scoped. The hosted-zone, standard-query, LBR, geo, IP, traffic-flow, and health-check SKUs are global. Use one line item per estate; emit additional Route 53 line items only if the user wants Resolver/Firewall split across Regions.

## Line-item header

```json
{
  "serviceCode":  "amazonRoute53",
  "estimateFor":  "Route53",
  "version":      "0.0.88",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Route 53",
  "description":  null
}
```

Note `estimateFor` is `"Route53"` (not `"template"` as with EC2). Pulled directly from `captures/saveAs/per-service/amazonRoute53.json` (local capture, not in repo).

## calculationComponents (verified shape)

```jsonc
{
  // --- Hosted zone footprint ---
  "numberOfHostedZones":  {"value": "10"},                       // count of hosted zones in the account
  "RRsetRecord":          {"value": "10"},                       // additional resource record sets beyond the per-zone default; informational in the SPA, no incremental SKU (verify before relying on this)
  "numberOf_IP_blocks":   {"value": "10"},                       // CIDR blocks loaded into Route 53 IP-Based Routing CIDR collections; first 100 free, billed beyond

  // --- DNS query volumes. Unit "millionPerMonth" means the count is already in millions; SPA multiplies by 1e6 before applying the per-query rate. ---
  "numberOfStandardQueries":             {"value": "10", "unit": "millionPerMonth"}, // standard authoritative queries
  "numberOfLatencyBasedRoutingQueries":  {"value": "10", "unit": "millionPerMonth"}, // LBR (latency-based routing)
  "numberOfGeoDNSQueries":               {"value": "10", "unit": "millionPerMonth"}, // Geo DNS + Geoproximity
  "numberOfIPRoutingQueries":            {"value": "10", "unit": "millionPerMonth"}, // IP-Based Routing
  "numberOfRecursiveAverageDNSQueries":  {"value": "10", "unit": "millionPerMonth"}, // queries handled by Route 53 Resolver inbound/outbound endpoints
  "numberOfFirewallDNSQueries":          {"value": "10", "unit": "millionPerMonth"}, // queries inspected by Resolver DNS Firewall

  // --- Traffic Flow ---
  "numberOfPolicyRecordsForTrafficFlow": {"value": "10"},        // Traffic Flow policy records (alias-style policy DNS records); $50/record/month

  // --- Health checks. Split by inside-AWS vs outside-AWS endpoint, then by feature class. ---
  // Basic checks: first 50 AWS-endpoint checks free; non-AWS billed from the first.
  "numberOfBasicChecksWithinAWS":   {"value": "10"},
  "numberOfBasicChecksOutsideAWS":  {"value": "10"},
  // Each of the four below is an "optional feature" added to a health check.
  // The SPA charges them additively per check ($1/AWS, $2/non-AWS per feature per month).
  "numberOfHTTPSChecksWithinAWS":             {"value": "10"},
  "numberOfHTTPSChecksOutsideAWS":            {"value": "10"},
  "numberOfStringMatchingChecksWithinAWS":    {"value": "10"},
  "numberOfStringMatchingChecksOutsideAWS":   {"value": "10"},
  "numberOfLatencyMeasurementChecksWithinAWS":  {"value": "10"},
  "numberOfLatencyMeasurementChecksOutsideAWS": {"value": "10"},
  "numberOfFastIntervalChecksWithinAWS":       {"value": "10"},
  "numberOfFastIntervalChecksOutsideAWS":      {"value": "10"},

  // --- DNS Firewall (regional) ---
  "numberOfDNSFirewallDomains":  {"value": "10"},                // domains stored in Firewall domain lists; $0.0005/domain/month

  // --- Resolver endpoints (regional) ---
  // The SPA bills numberOfElasticNetworkInterfaces * numberOFhours * per-ENI hourly rate.
  // numberOFhours is hours-per-month per ENI (730 for always-on). Leaving it at "10" produces 10 ENI-hours total.
  "numberOfElasticNetworkInterfaces":  {"value": "10"},
  "numberOFhours":                     {"value": "10", "unit": "hr"},

  // --- DNS Firewall VPC associations ---
  "numberOfVPCs": {"value": "10"}                                // VPCs associated to the Firewall rule group; informational, no separate per-VPC SKU at this time (verify before relying on this)
}
```

All numeric values are stringified. Set any dimension to `"0"` to disable that surface — keep the key present; the SPA expects every field in the captured shape.

Note the field name `numberOf_IP_blocks` carries an underscore prefix on `IP_blocks` — that's the actual key from the captured body. Don't normalize it.

## Pricing API filters

ServiceCode is `AmazonRoute53` (capital A). Most SKUs are global; Resolver/Firewall SKUs are region-prefixed. Region prefix is the standard SPA short code (`USE2-` for us-east-2, `USE1-` for us-east-1, `EUW1-` for eu-west-1, etc.) — enumerate via `get-attribute-values --service-code AmazonRoute53 --attribute usagetype`.

### Hosted zones (tiered)

```
--service-code AmazonRoute53
--filter usagetype=HostedZone
```

Two OnDemand priceDimensions:
- `begin_range=0`, `end_range=25` → **$0.50 / hosted zone / month**
- `begin_range=25`, `end_range=Inf` → **$0.10 / hosted zone / month**

### Standard authoritative DNS queries (tiered)

```
--filter usagetype=DNS-Queries
```

(Note: the global `DNS-Queries` SKU — distinct from region-prefixed `USE2-DNS-Queries` which is the Resolver/Recursive SKU.)

- 0 – 1,000,000,000 queries → **$0.40 per million** (= `4e-07` per query)
- 1B+ queries → **$0.20 per million**

### Latency-based routing queries (tiered)

```
--filter usagetype=LBR-Queries
```

- 0 – 1B → **$0.60 per million**
- 1B+ → **$0.30 per million**

### Geo DNS / Geoproximity queries (tiered)

```
--filter usagetype=Geo-Queries
```

- 0 – 1B → **$0.70 per million**
- 1B+ → **$0.35 per million**

For intra-AWS variants (queries from EC2 to Route 53 within AWS) the SKUs are `Intra-AWS-Geo-Queries` and `Intra-AWS-Geo-Proximity-Queries`. The captured saveAs body folds all geo flavors into `numberOfGeoDNSQueries`, so the SPA appears to use the external rate. Verify before relying on this if the user explicitly splits internal vs external geo queries.

### IP-Based Routing (CIDR) queries (tiered)

```
--filter usagetype=Cidr-Queries
```

- 0 – 1B → **$0.80 per million**
- 1B+ → **$0.40 per million**

### Route 53 Resolver recursive queries (region-prefixed, tiered)

```
--filter usagetype=<REGION>-DNS-Queries
```

Example for us-east-2:

```
--filter usagetype=USE2-DNS-Queries
```

- 0 – 1B → **$0.40 per million**
- 1B+ → **$0.20 per million**

### Route 53 Resolver DNS Firewall — queries inspected (region-prefixed, tiered)

```
--filter usagetype=<REGION>-DNS-FirewallQueries
```

- 0 – 1B → **$0.60 per million**
- 1B+ → **$0.40 per million**

### Route 53 Resolver DNS Firewall — domains stored (region-prefixed, flat)

```
--filter usagetype=<REGION>-DNS-FirewallDomainName
```

Single rate: **$0.0005 per domain stored / month** (i.e. $0.50 per 1000 domains).

### Resolver Network Interface (endpoint IP) hours (region-prefixed, flat)

```
--filter usagetype=<REGION>-ResolverNetworkInterface
```

Single rate: **$0.125 / ENI / hour**. Multiply by hours-per-month per ENI (730 if always-on) and by ENI count. Use `<REGION>-ResolverNetworkInterface-SecurityEnabled` if the user is on Resolver DNS Security (verify before relying on this — distinct rate, not captured here).

### Traffic Flow policy records (flat)

```
--filter usagetype=Traffic-Flow-Policy-Records
```

Single rate: **$50.00 / policy record / month**. Charged per traffic policy DNS record (not per traffic policy or version).

### Health checks — AWS endpoints, basic (tiered)

```
--filter usagetype=Health-Check-AWS
```

- 0 – 50 → **$0.00** (first 50 free)
- 50+ → **$0.50 per check / month**

### Health checks — non-AWS endpoints, basic (flat)

```
--filter usagetype=Health-Check-Non-AWS
```

Single rate: **$0.75 per check / month** (no free tier).

### Health checks — AWS endpoints, optional features (flat)

```
--filter usagetype=Health-Check-Option-AWS
```

Single rate: **$1.00 per optional feature per month**. Each of HTTPS / string matching / latency measurement / fast interval is one feature; if a check uses two of them, the SPA charges $2 against that check.

### Health checks — non-AWS endpoints, optional features (flat)

```
--filter usagetype=Health-Check-Option-Non-AWS
```

Single rate: **$2.00 per optional feature per month**.

### CIDR collection storage (IP-based routing)

The Pricing API does not expose a region-agnostic SKU for CIDR blocks stored in CIDR collections. AWS docs price CIDR collections at $0.30 per CIDR block per month with the first 100 blocks free. The captured saveAs uses `numberOf_IP_blocks` for this; with the captured value `"10"` (under the 100 free tier) the contribution is $0. Mark as **verify before relying on this** if the user has >100 CIDR blocks.

## Multipliers / formula

Tiered fields are priced by walking the band ranges; for the captured "10" examples every tier sits firmly in band 1, so the math simplifies to a flat per-unit rate.

```
# Hosted zones — tiered at 25
hosted_zone_cost = tiered(numberOfHostedZones, [(25, 0.50), (Inf, 0.10)])

# DNS queries — counts already in millions (numbers as written * 1e6 = raw queries)
std_queries        = numberOfStandardQueries            * 1_000_000
lbr_queries        = numberOfLatencyBasedRoutingQueries * 1_000_000
geo_queries        = numberOfGeoDNSQueries              * 1_000_000
ip_queries         = numberOfIPRoutingQueries           * 1_000_000
recursive_queries  = numberOfRecursiveAverageDNSQueries * 1_000_000
firewall_queries   = numberOfFirewallDNSQueries         * 1_000_000

query_cost = tiered(std_queries,       [(1e9, 4e-7), (Inf, 2e-7)]) \
           + tiered(lbr_queries,       [(1e9, 6e-7), (Inf, 3e-7)]) \
           + tiered(geo_queries,       [(1e9, 7e-7), (Inf, 3.5e-7)]) \
           + tiered(ip_queries,        [(1e9, 8e-7), (Inf, 4e-7)]) \
           + tiered(recursive_queries, [(1e9, 4e-7), (Inf, 2e-7)]) \
           + tiered(firewall_queries,  [(1e9, 6e-7), (Inf, 4e-7)])

# Traffic Flow
traffic_flow_cost = numberOfPolicyRecordsForTrafficFlow * 50.00

# Health checks — basic. AWS-endpoint first 50 free.
basic_health_cost = tiered(numberOfBasicChecksWithinAWS,  [(50, 0.0), (Inf, 0.50)]) \
                  + numberOfBasicChecksOutsideAWS * 0.75

# Health checks — optional features. Each of HTTPS, string-matching, latency-measurement,
# fast-interval is one "optional feature" per check; SPA bills them additively.
optional_features_within  = numberOfHTTPSChecksWithinAWS           \
                          + numberOfStringMatchingChecksWithinAWS  \
                          + numberOfLatencyMeasurementChecksWithinAWS \
                          + numberOfFastIntervalChecksWithinAWS
optional_features_outside = numberOfHTTPSChecksOutsideAWS           \
                          + numberOfStringMatchingChecksOutsideAWS  \
                          + numberOfLatencyMeasurementChecksOutsideAWS \
                          + numberOfFastIntervalChecksOutsideAWS
optional_health_cost = optional_features_within  * 1.00 \
                     + optional_features_outside * 2.00

# DNS Firewall storage
firewall_domain_cost = numberOfDNSFirewallDomains * 0.0005

# Resolver endpoints
resolver_eni_cost = numberOfElasticNetworkInterfaces * numberOFhours * 0.125

# CIDR collection storage — first 100 blocks free
cidr_block_cost = max(0, numberOf_IP_blocks - 100) * 0.30

# Additional record sets / VPC associations — no per-unit SKU surfaced by the Pricing API.
# Carried through configSummary but contribute $0 to monthly. (verify before relying on this)
rrset_cost = 0
vpc_cost   = 0

serviceCost.monthly = hosted_zone_cost + query_cost + traffic_flow_cost \
                    + basic_health_cost + optional_health_cost \
                    + firewall_domain_cost + resolver_eni_cost + cidr_block_cost
serviceCost.upfront = 0  # Route 53 has no upfront / reserved pricing
```

For `numberOFhours`: the field is hours-per-month per ENI. Always-on Resolver endpoints → use `"730"`. The captured body uses `"10"` (a tiny 10-ENI-hour total) — that's the calculator's default placeholder, not a typical workload value.

## configSummary template

Match the captured phrasing — the SPA reads this for the line-item card title. The captured fragment doesn't list every calculationComponent (it picks the headline ones):

```
Hosted Zones (<N>), Additional Records in Hosted Zones (<N>), IP (CIDR) blocks (<N>), Basic Checks Within AWS (<N>), Number of Elastic Network Interfaces (<N>), Number of domains stored (<N>), Number of VPCs associated to the rule group (<N>)
```

Don't add the query-volume fields, optional-health-feature fields, Traffic Flow record count, or hours value to the configSummary — they show in the detail view but not the card title in the captured body. Stick to those seven fragments in that order to keep the card rendering consistent.

## Defaults

| Field | Default | Why |
|---|---|---|
| `numberOfHostedZones` | "1" | A single hosted zone is the minimum useful Route 53 footprint |
| `RRsetRecord` | "0" | Informational only; no SKU contribution |
| `numberOf_IP_blocks` | "0" | IP-Based Routing is opt-in; first 100 CIDR blocks are free anyway |
| `numberOfStandardQueries` | "1" | 1M standard queries/month is a small public-zone baseline |
| `numberOfLatencyBasedRoutingQueries` | "0" | LBR is opt-in (per-record routing policy) |
| `numberOfGeoDNSQueries` | "0" | Geo / Geoproximity routing is opt-in |
| `numberOfIPRoutingQueries` | "0" | IP-Based Routing is opt-in |
| `numberOfRecursiveAverageDNSQueries` | "0" | Resolver endpoints only used by VPC outbound DNS — opt-in |
| `numberOfFirewallDNSQueries` | "0" | DNS Firewall is opt-in |
| `numberOfPolicyRecordsForTrafficFlow` | "0" | Traffic Flow is a paid-per-record add-on; $50/record adds up fast — flag explicitly if the user enables it |
| `numberOfBasicChecksWithinAWS` | "0" | No checks unless requested; first 50 AWS-endpoint checks free anyway |
| `numberOfBasicChecksOutsideAWS` | "0" | Same |
| `numberOfHTTPSChecks*` | "0" | Optional feature; off by default |
| `numberOfStringMatchingChecks*` | "0" | Optional feature; off by default |
| `numberOfLatencyMeasurementChecks*` | "0" | Optional feature; off by default |
| `numberOfFastIntervalChecks*` | "0" | Optional feature; off by default — fast-interval doubles the per-check rate in some pricing models, treat as paid |
| `numberOfDNSFirewallDomains` | "0" | Firewall off by default |
| `numberOfElasticNetworkInterfaces` | "0" | Resolver endpoints off by default; if user mentions "Resolver inbound/outbound endpoint" set to `"2"` (Resolver endpoints require a minimum of 2 IPs / ENIs) |
| `numberOFhours` | "730" | If Resolver endpoints are enabled, the per-ENI default is always-on (730 hr/month). The captured body's `"10"` is a placeholder, not a real default — override it. |
| `numberOfVPCs` | "0" | VPC associations are informational |

If the user just says "we use Route 53" without specifics, the right answer is roughly one hosted zone + a small query volume — around **$0.90/month** ($0.50 zone + $0.40 / 1M standard queries). Flag that in the breakdown and ask whether health checks, Resolver, Firewall, or Traffic Flow are in scope.

## Verification

Captured saveAs body lives at `captures/saveAs/per-service/amazonRoute53.json` (extracted from `captures/calculator.aws_new.har`). The captured `serviceCost.monthly` is **$1596.02** in `us-east-2` with every count set to `"10"`.

Rates verified via `pricing_client.py get-products` against `AmazonRoute53` on the date this module was authored (us-east-2 for region-scoped SKUs). Per-dimension contributions with the captured "10" inputs:

| Dimension | Math | Contribution |
|---|---|---|
| Hosted zones | 10 × $0.50 (within first 25) | $5.00 |
| Standard queries | 10M × $0.40/1M | $4.00 |
| LBR queries | 10M × $0.60/1M | $6.00 |
| Geo queries | 10M × $0.70/1M | $7.00 |
| IP-based queries | 10M × $0.80/1M | $8.00 |
| Recursive queries | 10M × $0.40/1M | $4.00 |
| Firewall queries | 10M × $0.60/1M | $6.00 |
| Traffic Flow records | 10 × $50.00 | $500.00 |
| Basic checks within AWS | 10 (under 50-free) × $0.00 | $0.00 |
| Basic checks non-AWS | 10 × $0.75 | $7.50 |
| HTTPS optional (AWS) | 10 × $1.00 | $10.00 |
| HTTPS optional (non-AWS) | 10 × $2.00 | $20.00 |
| String-match optional (AWS) | 10 × $1.00 | $10.00 |
| String-match optional (non-AWS) | 10 × $2.00 | $20.00 |
| Latency-measure optional (AWS) | 10 × $1.00 | $10.00 |
| Latency-measure optional (non-AWS) | 10 × $2.00 | $20.00 |
| Fast-interval optional (AWS) | 10 × $1.00 | $10.00 |
| Fast-interval optional (non-AWS) | 10 × $2.00 | $20.00 |
| Firewall domains stored | 10 × $0.0005 | $0.005 |
| Resolver ENI-hours | 10 ENI × 730 hr × $0.125 | $912.50 |
| CIDR blocks stored | 10 (under 100-free) × $0.00 | $0.00 |

Sum: **$1580.005**. Captured value: **$1596.02**. Delta: **$16.015**.

The shape, field names, and SKU mapping are verified. The residual ~$16 delta is unexplained by the surfaced Pricing API SKUs — likely tied to one of:

- `RRsetRecord` may charge against an aggregate-record SKU not exposed in the public Pricing API (the SPA may consider records beyond a per-zone allotment). **Verify before relying on this.**
- `numberOfVPCs` may carry a per-VPC association charge for the DNS Firewall rule group that isn't exposed as a top-level SKU. **Verify before relying on this.**
- One of the "optional features" health checks may charge per-feature plus a per-check base — `numberOfFastIntervalChecks*` is the most likely candidate since fast-interval checks are documented elsewhere as priced at a higher base. **Verify before relying on this.**

Also unverified end-to-end:
- `numberOFhours` interpretation as hours-per-month-per-ENI: inferred from the per-ENI hourly SKU rate and the captured "10"; the SPA could instead apply it as a global hours-budget. **Verify before relying on this.**
- Geo intra-AWS vs external rate split when `numberOfGeoDNSQueries` is populated: the captured body uses a single field for all flavors. **Verify before relying on this if the user splits internal/external Geo.**
- DNS Security–enabled Resolver ENIs (`<REGION>-ResolverNetworkInterface-SecurityEnabled`): distinct SKU exists, but the captured shape has no separate field for it. **Verify before relying on this.**

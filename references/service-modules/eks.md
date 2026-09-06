# Amazon EKS (`awsEks`)

Single line item covering the EKS **control plane** (Standard Support + Extended Support), **EKS Hybrid Nodes** vCPU billing, and the **EKS platform-capabilities add-ons** (Argo CD, ACK, KRO). EKS worker nodes on EC2 are **not** modeled here — bill those as a separate EC2 line item. Fargate pods on EKS are **not** modeled here either — use the `awsFargate` module for those.

## Coverage

| Path | Confidence | Anchor |
|---|---|---|
| Control plane Standard + Extended Support (us-east-2) | capture-verified | `captures/saveAs/per-service/awsEks.json` (local capture, 2026-05-11) — $73.00 + $365.00 |
| Hybrid Nodes at tier 1 (7,300 vCPU-hr) | capture-verified | same capture — $146.00 |
| Capabilities add-ons (Argo CD + ACK + KRO, all non-zero) | capture-verified | same capture — $301.56 + $36.00 + $36.00; total $957.57 within $0.01 |
| Per-component rates (Pricing API and `eks.json` runtime feed agree) | capture-verified | `pricing_client.py get-products` + `meteredUnitMaps/eks/USD/current/eks.json` |
| Hybrid Nodes tiers 2-5 | inferred | rates known, but the SPA's tiered walk is only round-tripped at tier 1 |
| A single capability enabled with the others at "0" | inferred | assumed to zero those lines; not separately captured |
| EKS Auto Mode | inferred | no `*AutoMode*` cc fields in the capture — field names unknown |
| EKS on EC2 worker nodes / on Fargate pods | inferred | not modeled here — emit `ec2Enhancement` or `awsFargate` lines instead |

## Line-item header

```json
{
  "serviceCode":  "awsEks",
  "estimateFor":  "Amazon EKS",
  "version":      "0.0.40",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon EKS",
  "description":  null
}
```

**`estimateFor` is the literal string `"Amazon EKS"` — with a space, mixed case.** It is not a kebab/camel-case form id like other modules; the SPA carries the human-readable form title here. Do not rewrite it.

## calculationComponents (verified shape)

```jsonc
{
  // Control plane
  "numberOfEKSClusters":           {"value": "1"},                   // Standard Support clusters
  "numberOfEKSClusters_es":        {"value": "1"},                   // Extended Support clusters (Kubernetes versions past standard EOL); "" or absent for none

  // Hybrid Nodes (on-prem / edge nodes attached to an EKS control plane; billed per vCPU-hour)
  "numberOfHybridNodes":           {"unit": "perMonth", "value": "1"}, // ALWAYS unit "perMonth"; value is a steady-state node count
  "numberOfVCPUperNode":           {"value": "10"},                  // vCPU per hybrid node

  // EKS Capabilities (platform add-ons; each capability is independent)
  // Argo CD — GitOps controller managing N Argo CD Applications per capability
  "argoCDCapabilities":            {"value": "10"},
  "argoCDApplicationsPerCapability": {"value": "10"},
  // ACK — AWS Controllers for Kubernetes managing N AWS resources per capability
  "ackCapabilities":               {"value": "10"},
  "ackResourcesPerCapability":     {"value": "10"},
  // KRO — Kube Resource Orchestrator managing N ResourceGroupDefinition instances per capability
  "kroCapabilities":               {"value": "10"},
  "kroRGDInstancesPerCapability":  {"value": "10"}
}
```

**Unit interpretation:**

- `numberOfHybridNodes.unit` is fixed to `"perMonth"` by the form (the UI only offers "per month" as a frequency option). Despite the name, the SPA treats `value` as a steady-state node count and bills `value × numberOfVCPUperNode × 730` vCPU-hours per month. Captured `value: "1"` × `numberOfVCPUperNode: 10` × 730 hr × $0.02 = **$146/mo**, not $0.02. Do **not** interpret `perMonth` as "one node hour-equivalent per month."
- All `*Capabilities` and `*PerCapability` fields are billed per-hour (multiplied by 730). Capability rates and per-item rates are independent — a capability with zero items still bills the capability rate.

**EKS Auto Mode is NOT in the captured shape.** The captured form has three cards: cluster pricing, EKS Capabilities, and Hybrid Nodes. The form *also* references EKS Auto Mode metered units (`AutoMode` eksproducttype exists in the Price List API for management-hour rates per EC2 instance type), but no `*AutoMode*` calculationComponents fields were captured. If a user asks for EKS Auto Mode pricing, capture a fresh HAR before quoting — the field names are unknown.

## Pricing API filters

ServiceCode: `AmazonEKS`. Filterable attributes include `regionCode`, `usagetype`, `capabilitytype` (`ACK`/`ArgoCD`/`KRO`), `ekscapabilityunits` (`Hours:perCapability` / `CR-Hours:perCustomResource`), `eksproducttype` (`AutoMode`/`HybridNodes`).

us-east-2 usage type prefix is `USE2-`; substitute the standard region prefix for other regions.

### Control plane — Standard Support (captured)

```
--service-code AmazonEKS
--filter regionCode=<region>
--filter "usagetype=<PREFIX>-AmazonEKS-Hours:perCluster"
```

us-east-2: `$0.10` / cluster-hour. Description: `"Amazon EKS cluster usage in US East (Ohio)"`.

### Control plane — Extended Support (captured)

```
--filter "usagetype=<PREFIX>-AmazonEKS-Hours:extendedSupport"
```

us-east-2: `$0.50` / cluster-hour. Description: `"Amazon EKS extended support usage in US East (Ohio)"`. Bills only for clusters running a Kubernetes version past its standard-support window — usually 14 months after the version's GA.

### Hybrid Nodes (captured, tiered)

```
--filter "usagetype=<PREFIX>-AmazonEKSHybridNodes-Hours:pervCPU"
```

Returns five OnDemand priceDimensions with `begin_range` / `end_range` in vCPU-hours/month. us-east-2 rates:

| Tier | vCPU-hour range | Rate |
|---|---|---|
| 1 | 0 – 576,000 | $0.0200 |
| 2 | 576,001 – 1,152,000 | $0.0140 |
| 3 | 1,152,001 – 5,760,000 | $0.0100 |
| 4 | 5,760,001 – 11,520,000 | $0.0080 |
| 5 | > 11,520,000 | $0.0060 |

Walk the user's monthly vCPU-hours across the bands the same way EC2 outbound data transfer does. For a typical quote (a handful of nodes × tens of vCPU each) the entire month falls in tier 1 at $0.02.

### EKS Capabilities — Argo CD / ACK / KRO (captured)

Two SKUs per capability type: one per-capability-hour, one per-managed-item-hour (the latter labeled `CR-Hours:perCustomResource` in the Price List API). us-east-2 rates:

| Capability | Per-capability $/hr | Per-item $/hr | Item term in calculator | Per-item field id |
|---|---|---|---|---|
| Argo CD | $0.02771 | $0.00136 | Application | `argoCDApplicationsPerCapability` |
| ACK | $0.004482 | $0.000045 | Resource | `ackResourcesPerCapability` |
| KRO | $0.004482 | $0.000045 | RGD instance | `kroRGDInstancesPerCapability` |

ACK and KRO share the same per-capability and per-item rates in us-east-2; Argo CD is roughly 6× more expensive per capability and 30× more expensive per managed item. Pull fresh rates per region — the Price List API returns the same field shape for every region.

```
--filter capabilitytype=ArgoCD|ACK|KRO
--filter ekscapabilityunits=Hours:perCapability|CR-Hours:perCustomResource
```

## Multipliers / formula

All rates are per-hour. The SPA uses **730 hours/month** consistently across every card on this form.

```
H = 730

# Control plane
cluster_std_cost = numberOfEKSClusters    * cluster_std_rate * H            # us-east-2: ×$0.10×730 = $73/cluster/mo
cluster_ext_cost = numberOfEKSClusters_es * cluster_ext_rate * H            # us-east-2: ×$0.50×730 = $365/cluster/mo

# Hybrid Nodes (tiered on monthly vCPU-hours)
vcpu_hours = numberOfHybridNodes * numberOfVCPUperNode * H
hybrid_cost = walk_tiers(vcpu_hours, hybrid_tier_rates)

# Capabilities (each block: capability_rate * caps + per_item_rate * caps * items_per_cap, all × 730)
argo_cost = (argoCDCapabilities * argoCD_cap_rate
             + argoCDCapabilities * argoCDApplicationsPerCapability * argoCD_app_rate) * H
ack_cost  = (ackCapabilities * ack_cap_rate
             + ackCapabilities * ackResourcesPerCapability * ack_res_rate) * H
kro_cost  = (kroCapabilities * kro_cap_rate
             + kroCapabilities * kroRGDInstancesPerCapability * kro_inst_rate) * H

serviceCost.monthly = cluster_std_cost + cluster_ext_cost + hybrid_cost + argo_cost + ack_cost + kro_cost
serviceCost.upfront = 0
```

**Total-items-per-capability rule:** the SPA computes `caps × items_per_cap` first (e.g. `argoCDCapabilities × argoCDApplicationsPerCapability`), then multiplies by the per-item hourly rate and by 730. Setting one of the pair to 0 zeros out the entire per-item line for that capability type but the per-capability line still bills if `caps > 0`.

## configSummary template

Match the captured phrasing — the SPA reads this for the line-item card title. Field order matters for display parity.

```
Number of EKS Clusters (<N>), Number of hybrid nodes (<H> per month), Number of EKS Clusters (<N_es>), Number of Argo CD capabilities (<A_caps>), Number of Argo CD Applications per Argo CD capability (<A_apps>), Number of ACK capabilities (<K_caps>), Number of ACK resources per ACK capability (<K_res>), Number of KRO capabilities (<R_caps>), Number of KRO RGD instances managed per KRO capability (<R_inst>), Number of vCPU per hybrid node (<V>)
```

The captured summary lists "Number of EKS Clusters" twice (once for standard support, once for extended support) — leave the duplicate in; that's the SPA's actual rendering.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfEKSClusters | "1" | One cluster minimum to make the line item meaningful |
| numberOfEKSClusters_es | "" (empty) or "0" | Most users are on standard-support K8s versions; do NOT default to 1 — it triggers a $365/mo silent surcharge |
| numberOfHybridNodes | "0" or absent | Most EKS users run nodes on EC2/Fargate; hybrid is a niche on-prem feature |
| numberOfVCPUperNode | "" or "0" | Pair with numberOfHybridNodes |
| argoCDCapabilities, argoCDApplicationsPerCapability | "0" | Capabilities add-ons opt-in; flag if user mentions GitOps/ArgoCD |
| ackCapabilities, ackResourcesPerCapability | "0" | Opt-in; flag if user mentions ACK or controller-based AWS resource provisioning |
| kroCapabilities, kroRGDInstancesPerCapability | "0" | Opt-in; flag if user mentions KRO or Kubernetes-native AWS composition |

**Capability terminology is ambiguous.** A "capability" in the EKS sense is a deployed instance of the controller (one Argo CD installation, one ACK controller, one KRO controller) — not a feature flag. Each capability bills hourly regardless of whether it's actively reconciling anything. If a user says "we want ArgoCD," that typically means **one** Argo CD capability (`argoCDCapabilities: 1`) plus however many Applications they actually deploy.

## Verification

- Shape captured from a working saveAs body the calculator round-tripped on 2026-05-11 in `us-east-2`: see `captures/saveAs/per-service/awsEks.json` (local capture, not in repo).
- Per-component rates verified two ways:
  - Pricing API (`pricing_client.py get-products --service-code AmazonEKS --filter regionCode=us-east-2 ...`) — returns the same numbers as the runtime JSON for every metered unit checked.
  - SPA runtime feed `https://calculator.aws/pricing/2.0/meteredUnitMaps/eks/USD/current/eks.json` (captured in `calculator.aws_new_2.har`) — keyed by regionless metered-unit hash, returns the same prices.
- Captured math reproduction (us-east-2, captured values):
  - Cluster Std: 1 × $0.10 × 730 = **$73.00**
  - Cluster Ext: 1 × $0.50 × 730 = **$365.00**
  - Hybrid Nodes: 1 × 10 × 730 = 7,300 vCPU-hr (tier 1) × $0.02 = **$146.00**
  - Argo CD caps: 10 × $0.02771 × 730 = **$202.283**; apps: (10×10) × $0.00136 × 730 = **$99.280**; subtotal **$301.563**
  - ACK caps: 10 × $0.004482 × 730 = **$32.7186**; resources: 100 × $0.000045 × 730 = **$3.285**; subtotal **$36.0036**
  - KRO caps: 10 × $0.004482 × 730 = **$32.7186**; instances: 100 × $0.000045 × 730 = **$3.285**; subtotal **$36.0036**
  - **Total: $957.5702**, captured `serviceCost.monthly: 957.58` — matches within $0.01 (SPA rounds half-cents).
- Not yet verified end-to-end (capture before relying on these):
  - **EKS Auto Mode** — the SPA references an `AutoMode` product type (per-EC2-instance management-hour rates in the Price List API) but no `*AutoMode*` calculationComponents fields appear in the captured shape. Field names unknown.
  - **EKS on EC2 worker nodes** — not modeled here at all. Bill EC2 worker nodes via the `ec2Enhancement` module as a separate line item.
  - **EKS on Fargate pods** — not modeled here. Use the `awsFargate` module as a separate line item.
  - **Hybrid Nodes at tiers 2–5** — rate values verified via Pricing API and runtime JSON, but the SPA's tiered-pricing walk has only been round-tripped at tier 1 (7,300 vCPU-hr). For very large hybrid-node fleets (> 789 vCPU on continuous 730-hr/mo billing crosses into tier 2), confirm the line-item total matches the SPA before quoting.
  - **Multiple capability types simultaneously** — captured shape has all three (Argo CD + ACK + KRO) at non-zero values and reproduces; that's well-exercised. Setting only one and leaving the others as `"0"` is inferred to zero the corresponding lines but not separately captured.

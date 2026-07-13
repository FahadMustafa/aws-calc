# saveAs body schema

Top-level shape, derived from a verified successful POST. Only the keys listed below are needed; do not invent extras.

```jsonc
{
  "name": "AWS Estimate 2026-05-09",         // free-form; user-supplied or auto-generated

  "services": {                              // ungrouped line items keyed by `<serviceCode>-<uuid4>`
    "ec2Enhancement-12532786-d389-4453-a05b-9e77c6993c96": { ... see service module ... }
  },

  "groups": {                                // optional estimate groups (named buckets of line items)
    "Prod-e693d1fb-dc3c-4fbb-b297-662457529836": { ... see "Groups" section below ... }
  },

  "groupSubtotal": { "monthly": 0 },         // sum over the top-level `services` only (NOT including grouped services)
  "totalCost":     { "monthly": 0, "upfront": 0 },   // body.groupSubtotal + sum of every group's totalCost (recursive)
  "support": {},                             // {} unless AWS Support added

  "metaData": {
    "locale":    "en_US",
    "currency":  "USD",
    "createdOn": "2026-05-09T18:31:23.509Z", // UTC ISO with milliseconds, suffix Z
    "source":    "calculator-platform"
  }
}
```

## Groups

The calculator's "Groups" feature lets users organize line items into named, optionally-nested buckets. Each group renders as a collapsible section in the SPA with its own subtotal.

A group lives under the body's `groups` dict, keyed by `<userGivenName>-<uuid4>` (the SPA generates this key when the user creates the group; `<userGivenName>` is the display string, `<uuid4>` is fresh). The same key pattern repeats for nested groups under a parent group's own `groups` dict — groups are arbitrarily deep.

```jsonc
"groups": {
  "Prod-e693d1fb-dc3c-4fbb-b297-662457529836": {        // key = "<name>-<uuid4>"; name segment must match `name` field below
    "name":          "Prod",                            // display name; the SPA shows this, not the key
    "services": {                                       // line items in this group (same shape as top-level services)
      "amazonMQ-f50d9ce9-c557-4427-854c-1e189193cfc6": { ... per-line-item shape ... }
    },
    "groups": {},                                       // {} for leaf groups; recursive same shape for nested groups
    "groupSubtotal": { "monthly": <sum of immediate `services` only, this group> },
    "totalCost":     { "monthly": <groupSubtotal + sum of every nested groups[*].totalCost>, "upfront": <sum> }
  }
}
```

### Building a body with groups

1. Decide which line items belong in groups vs at the top level. If the user did not mention buckets/teams/environments/projects/clients, emit no groups — leave `body.groups: {}`.
2. For each group, generate a fresh uuid4 and build the key as `<name>-<uuid>`. The `<name>` segment must contain only characters legal in display (letters, digits, hyphens, spaces are fine; the SPA will round-trip whatever you put). The `name` field inside the group object must equal the `<name>` segment of the key.
3. Put each grouped line item under `body.groups[<group-key>].services[<lineItemKey>]` instead of `body.services[<lineItemKey>]`. The line-item shape is identical — only its location changes.
4. Compute subtotals bottom-up:
   - For each leaf group: `groupSubtotal.monthly = sum(this group's immediate services[*].serviceCost.monthly)`. `totalCost` is the same as `groupSubtotal` for leaf groups (since nested groups contribute 0). Include `upfront` only if any line item is reserved.
   - For each parent group: `totalCost.monthly = groupSubtotal.monthly + sum(child groups[*].totalCost.monthly)`.
   - For the body: `groupSubtotal.monthly = sum(body.services[*].serviceCost.monthly)` (top-level ungrouped services only). `totalCost.monthly = body.groupSubtotal.monthly + sum(body.groups[*].totalCost.monthly)`.
5. Float sum precision: the SPA uses native JS addition, so `1.02 + 8167.30` may serialize as `8168.320000000001`. Don't pre-round to two decimals on totals — the calculator accepts either, but matching exact captured values requires letting the floating-point sum stand.

### Anchor example

A real grouped body is at `references/examples/groups-example-body.json` (one ungrouped line + one grouped line). Inspect it before constructing your first multi-group estimate.

## Per-line-item shape (flat services)

For services without sub-services (EC2, RDS, etc.):

```jsonc
{
  "serviceCode":  "<canonical>",             // e.g. "ec2Enhancement"
  "estimateFor":  "<form-id>",               // e.g. "template" — see service module
  "version":      "<form-version>",          // e.g. "0.0.68" — see service module
  "region":       "us-east-2",               // region code
  "regionName":   "US East (Ohio)",          // display name (matches Pricing API location)
  "serviceName":  "Amazon EC2",              // display
  "description":  null,                      // user note; usually null
  "calculationComponents": { ... per service module ... },
  "serviceCost": { "monthly": 0, "upfront": 0 },
  "configSummary": "Tenancy (...), Operating system (...), ..." // human-readable line; reproduce same style as captured examples
}
```

## Per-line-item shape (group services)

For services that aggregate sub-services (S3 group, VPC):

```jsonc
{
  "serviceCode":  "amazonSimpleStorageServiceGroup",
  "estimateFor":  "simpleStorageServiceClassesGroup",
  "version":      "<form-version>",
  "region":       "us-east-2",
  "regionName":   "US East (Ohio)",
  "serviceName":  "Amazon Simple Storage Service (S3)",
  "description":  null,
  "subServices":  [ { ...flat-shape line item... }, { ... } ],
  "serviceCost":  { "monthly": <sum of subServices>, "upfront": <sum> },
  "configSummary": "S3 Standard storage (...), ..."
}
```

## Region code → Region name

Used for both `regionName` and Pricing API `location` filter values.

| code | name |
|---|---|
| us-east-1 | US East (N. Virginia) |
| us-east-2 | US East (Ohio) |
| us-west-1 | US West (N. California) |
| us-west-2 | US West (Oregon) |
| ca-central-1 | Canada (Central) |
| eu-west-1 | EU (Ireland) |
| eu-west-2 | EU (London) |
| eu-west-3 | EU (Paris) |
| eu-central-1 | EU (Frankfurt) |
| eu-north-1 | EU (Stockholm) |
| eu-south-1 | EU (Milan) |
| ap-south-1 | Asia Pacific (Mumbai) |
| ap-southeast-1 | Asia Pacific (Singapore) |
| ap-southeast-2 | Asia Pacific (Sydney) |
| ap-northeast-1 | Asia Pacific (Tokyo) |
| ap-northeast-2 | Asia Pacific (Seoul) |
| sa-east-1 | South America (Sao Paulo) |
| me-south-1 | Middle East (Bahrain) |
| me-central-1 | Middle East (UAE) |
| af-south-1 | Africa (Cape Town) |
| il-central-1 | Israel (Tel Aviv) |

If a region is not in this table, use `aws ec2 describe-regions` or the Pricing API `get-attribute-values --service-code AmazonEC2 --attribute location` to find the correct display name. Always verify; the SPA's `regionName` must match what the Price List API returns.

## Generating a UUID for the line-item key

The `<uuid4>` portion is a fresh uuid4 per line item. In Python: `str(uuid.uuid4())`.

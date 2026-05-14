# saveAs body schema

Top-level shape, derived from a verified successful POST. Only the keys listed below are needed; do not invent extras.

```jsonc
{
  "name": "AWS Estimate 2026-05-09",         // free-form; user-supplied or auto-generated

  "services": {                              // line items keyed by `<serviceCode>-<uuid4>`
    "ec2Enhancement-12532786-d389-4453-a05b-9e77c6993c96": { ... see service module ... }
  },

  "groups": {},                              // estimate groups; {} unless user grouped
  "groupSubtotal": { "monthly": 0, "upfront": 0 },
  "totalCost":     { "monthly": 0, "upfront": 0 },
  "support": {},                             // {} unless AWS Support added

  "metaData": {
    "locale":    "en_US",
    "currency":  "USD",
    "createdOn": "2026-05-09T18:31:23.509Z", // UTC ISO with milliseconds, suffix Z
    "source":    "calculator-platform"
  }
}
```

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

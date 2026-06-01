# Resolving the calculator.aws SPA's opaque cc tokens

Some service modules' `calculationComponents` fields contain 43-character URL-safe-base64 tokens (e.g. `5hcZU6WguRUktrgs8rMw8I50JgkU3TyzOOdhtsRRjXs`). These are NOT secrets and they do NOT require per-configuration HAR captures to discover. They are `RegionlessRateCode` values from a per-service catalog that the SPA fetches at runtime from a world-readable CloudFront URL.

## Catalog URL pattern

```
https://calculator.aws/pricing/2.0/meteredUnitMaps/<service>/USD/current/<service>.json
```

The response is JSON, served gzip-compressed. Known catalog slugs:

| Service module | Catalog slug | Friendly-key support |
|---|---|---|
| `amazon-mq.md` | `mq` | Yes — `regions[*][<friendly key>]` is keyed by strings like `"RabbitMQ Active Standby mq m5.large"` |
| `bedrock.md` | `bedrock`, `bedrockfoundationmodels` | **No friendly keys** — `regions[*]` is keyed only by `RegionlessRateCode` itself. Model-name → token mapping must come from bundle.js or from a separate descriptor file (e.g. `https://d1qsjq9pzbk1k6.cloudfront.net/data/amazonBedrock/en_US.json`) — investigation in progress |
| (Most other services use readable strings directly and don't need this) | — | n/a |

## Catalog shape

```jsonc
{
  "manifest": { "serviceId": "...", ... },
  "sets":     { "<set-name>": [<sku-string>, ...], ... },   // groups of related SKUs; may be empty
  "regions": {
    "<region display name>": {                              // e.g. "EU (Ireland)"
      "<key>": {                                            // <key> is one of: SKU rateCode string, RegionlessRateCode, or a friendly catalog key
        "rateCode": "V2KECZY9KZJEQ6AT.JRTCKXETXF.6YS6EN2CT7",
        "price": "0.9630000000",
        "RegionlessRateCode": "5hcZU6WguRUktrgs8rMw8I50JgkU3TyzOOdhtsRRjXs",
        "Instance Type": "m5.large",
        "vCPU": "2",
        "Memory": "8 GiB"
      },
      ...
    },
    ...
  }
}
```

`RegionlessRateCode` is the opaque token used in `calculationComponents`. The same token appears in every region under multiple keys (the SKU rateCode-derived key, the RegionlessRateCode itself, and — for some services — friendly keys). All point to the same record, with per-region `price`.

## Helper script

`scripts/resolve_token.py` fetches and caches catalogs and resolves friendly keys to tokens:

```
# resolve one friendly key
python3 scripts/resolve_token.py mq --friendly "RabbitMQ Active Standby mq m5.large"
# -> 5hcZU6WguRUktrgs8rMw8I50JgkU3TyzOOdhtsRRjXs

# dump every friendly→token mapping for a service
python3 scripts/resolve_token.py mq --dump-friendly

# bypass the on-disk cache (~/.cache/aws-calc/<service>.json)
python3 scripts/resolve_token.py mq --refresh
```

For services without friendly keys (Bedrock), the script's `build_friendly_map` returns an empty dict — you'll need to either chain through the bundle's model registry or capture a HAR to harvest tokens.

## Anti-pattern reminder

If a module's token table doesn't cover the user's exact configuration, **do not** substitute a known-but-wrong token while overriding `serviceCost.monthly`. The SPA recomputes `serviceCost` from `calculationComponents` on load and will render a `$0` line item if the token is wrong, regardless of what value you wrote into the body. Either resolve the correct token (via the catalog) or refuse that line and ask for a fresh HAR.

# `<serviceCode>`

Use this template when adding a new service module. Copy to `<service-name>.md` (kebab-case based on the user-friendly name) and fill in.

## Line-item header

```json
{
  "serviceCode":  "<serviceCode>",
  "estimateFor":  "<form-id>",
  "version":      "<form-version>",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "<display>",
  "description":  null
}
```

Pull `estimateFor`, `version`, and `serviceName` from a captured saveAs body.

## calculationComponents (verified shape)

Paste the captured `calculationComponents` object here. Annotate any fields whose meaning is non-obvious.

## Pricing API filters

```
--service-code <Pricing API ServiceCode>
--filter ...
```

Use `scripts/pricing_client.py describe-attributes --service-code <X>` to list filterable attributes; `get-attribute-values` to enumerate valid values per attribute.

## Multipliers / formula

Document how to combine the user's inputs and the Pricing API rates to derive `serviceCost.monthly` and `serviceCost.upfront`. Be explicit about edge cases (tiered pricing, free tiers, RI/SP discounts, deployment-option multipliers).

## configSummary template

Reproduce the exact phrasing style from a captured saveAs body. The SPA reads this for the line-item card title; deviating may produce odd display.

## Defaults

| Field | Default | Why |
|---|---|---|
|  |  |  |

## Verification

Note here:
- The captured HAR file (or other ground truth) used to derive the shape
- Which (instance type / region / config) you tested end-to-end
- Anything that's still inferred and not yet verified

If a field is inferred from the bundle rather than a captured working POST, mark it as "verify before relying on this".

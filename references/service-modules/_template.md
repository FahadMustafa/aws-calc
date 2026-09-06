# `<serviceCode>`

Use this template when adding a new service module. Copy to `<service-name>.md` (kebab-case based on the user-friendly name) and fill in.

## Coverage

Fill one row per configuration path this module covers, derived from your own Verification
section — never a label the module cannot back up. If in doubt, `inferred`.

| Path | Confidence | Anchor |
|---|---|---|
| <config / sub-service / pricing mode> | recompute-verified | <live-SPA note + date> |
| <config / sub-service / pricing mode> | capture-verified | <capture file / fixture / share URL> |
| <config / sub-service / pricing mode> | inferred | <form definition, bundle, docs — or "—"> |

Keep it to 12 rows or fewer; collapse variants (e.g. "Standard RI 1Y/3Y all payment options").
See "Confidence vocabulary" under Verification for what each label means. Callers refuse
`inferred` paths by default (SKILL.md step 2).

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

Before defining any percent, "millions"/`perMonth`, or free-tier field, check `references/conventions.md` — those three encodings are proven recompute hazards with module-specific rules.

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

### Confidence vocabulary (label every covered path)

Model this on amazon-mq.md's coverage matrix: give each configuration/path you cover exactly one of the two labels below. State the anchor (capture file or share URL) next to it.

- **capture-verified** — the formula reconciles a captured saveAs `serviceCost` (ideally to the cent); the field shape is lifted verbatim from a HAR / saveAs body. Proves the *save* is well-formed and the math matches one observed snapshot.
- **recompute-verified** — the share URL was opened in the live SPA, "Update estimate" was clicked, and the line survived non-zero (did not collapse or drop). Proves the encoding round-trips through the SPA's recompute layer — the stronger guarantee, since percent/million/free-tier encoding bugs pass the save but fail here.

recompute-verified implies capture-verified. A path with neither label is inferred — mark it "verify before relying on this". Do not relabel existing modules to this scheme retroactively.

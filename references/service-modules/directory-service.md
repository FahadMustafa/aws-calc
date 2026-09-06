# AWS Directory Service (`aWSDirectoryService`, AWS Managed Microsoft AD)

`serviceCode` is `aWSDirectoryService` (lowercase `a`, uppercase `WS`). `estimateFor` is `managedMicrosoftActiveDirectory` — this module covers the **AWS Managed Microsoft AD** form only. The other Directory Service offerings (AD Connector, Simple AD) use different `estimateFor` values and are **not in this capture**.

This is a **flat** line item — no `subServices` array. The two priced features (directory hosting and directory sharing) appear as separate keys inside the single `calculationComponents` object.

## Line-item header

```json
{
  "serviceCode":  "aWSDirectoryService",
  "estimateFor":  "managedMicrosoftActiveDirectory",
  "version":      "0.0.61",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Directory Service",
  "description":  null,
  "serviceCost":  { "monthly": <computed> },
  "configSummary": "<see template below>"
}
```

## calculationComponents (verified shape)

Unique shape alert: both fields are `columnFormIPM_*` and their `value` is an **array of row objects whose keys are the human-readable form-label strings** (with spaces and Title Case), not camelCase identifiers. The SPA matches these strings literally — copy verbatim, capitalization and spacing included.

```jsonc
{
  "columnFormIPM_MicrosoftAD": {
    "value": [
      {
        "Directory Size":                       {"value": "Enterprise"},   // "Standard" | "Enterprise"
        "Number of Directories":                {"value": "1"},
        "Number Of Addl Domain Controllers":    {"value": "1"}             // "Addl" not "Additional"; "Of" not "of"
      }
      // one row object per distinct (size, additional-DC-count) combination — usually exactly one row
    ]
  },
  "columnFormIPM_SharedMicrosoftAD": {
    "value": [
      {
        "Directory Size":                       {"value": "Enterprise"},
        "Number Of Shared Directories":         {"value": "1"},
        "Number Of Addl Accounts":              {"value": "1"}             // accounts shared *to*, per directory
      }
      // one row per (size, shared count) combination; omit the whole columnFormIPM_SharedMicrosoftAD if no sharing
    ]
  }
}
```

Key-name quirks to copy exactly:
- `"Number of Directories"` — lowercase `of`
- `"Number Of Addl Domain Controllers"` and `"Number Of Addl Accounts"` and `"Number Of Shared Directories"` — capital `Of`, and `Addl` (not `Additional`)
- `"Directory Size"` — accepted values are `"Standard"` and `"Enterprise"` (case-sensitive)

## Pricing API filters

```
--service-code AWSDirectoryService
--filter productFamily="Directory Service"
--filter regionCode=<region>
```

Filter further by:
- `productType` and `directoryType` to scope to "Microsoft Active Directory" (Standard vs Enterprise)
- `usagetype` for the per-hour SKUs: directory hosting hourly, additional-domain-controller hourly, and per-account sharing hourly

`get-attribute-values --service-code AWSDirectoryService --attribute directoryType` enumerates the directory variants.

## Multipliers / formula

```
# Directory hosting (per row in columnFormIPM_MicrosoftAD)
host.monthly  = numberOfDirectories * 730 * directory_hourly_rate(size)
              + numberOfDirectories * additionalDCs * 730 * additional_dc_hourly_rate(size)

# Directory sharing (per row in columnFormIPM_SharedMicrosoftAD)
share.monthly = numberOfSharedDirectories * additionalAccounts * 730 * shared_account_hourly_rate(size)

serviceCost.monthly = sum(host.monthly over MicrosoftAD rows)
                    + sum(share.monthly over SharedMicrosoftAD rows)
```

Verified at eu-west-1: 1 Enterprise directory, 1 additional DC, 1 shared directory shared to 1 account → captured `$481.80/month`. A best-effort reconstruction using AWS-published rates (Enterprise hosting $0.40/h, additional DC $0.20/h, shared account $0.05/h) yields:

```
1 * 730 * 0.40  = $292.00   # directory hosting
1 * 1 * 730 * 0.20 = $146.00   # additional DC
1 * 1 * 730 * 0.05 = $ 36.50   # sharing
total           = $474.50
```

Captured `$481.80` is $7.30 higher — the eu-west-1 rates differ slightly from the assumed US rates. **Pull live rates from the Pricing API and re-derive before quoting.** The shape is verified; the exact per-region per-size rate table needs to come from `get-products`, not memory.

> **CAVEAT — Directory Service is expensive; the hourly rates above are illustrative US-only.** The hardcoded per-hour edition rates (Enterprise hosting $0.40/h, additional DC $0.20/h, shared account $0.05/h) are assumed US numbers and already miss the captured eu-west-1 total by ~$7.30. A small directory runs hundreds of dollars/month, so rate error compounds fast. **NEVER quote without running `get-products` for the user's exact region and edition** (Standard vs Enterprise) and re-deriving from the live rates.

## configSummary template

Match captured phrasing exactly — the SPA reads this for the line-item card title:

```
Total number of directories (<N>), Number of total additional domain controllers (<N>), Edition (<Standard|Enterprise>), Number of directories to be shared (<N>), Number of additional accounts to which each directory is shared (<N>), Shared Directory edition (<Standard|Enterprise>)
```

If the user did not enable sharing, drop the three sharing segments and just keep `Total number of directories (<N>), Number of total additional domain controllers (<N>), Edition (<size>)`.

## Defaults

| Field | Default | Why |
|---|---|---|
| Directory Size | "Standard" | Enterprise is 3x+ the cost; ask before defaulting to Enterprise |
| Number of Directories | "1" | Almost always one when the user mentions Managed Microsoft AD |
| Number Of Addl Domain Controllers | "0" | The default 2 DCs are included in the directory hourly; charge only what user explicitly adds |
| Number Of Shared Directories | "0" (omit the `columnFormIPM_SharedMicrosoftAD` key entirely if not sharing) | Sharing is opt-in |
| Number Of Addl Accounts | "0" | Same — only set if user mentions multi-account sharing |
| Shared Directory edition | match `Directory Size` (the source directory's edition determines sharing rates) | Same edition is the safe default |

If the user mentions "Active Directory" or "AD" without specifying AWS Managed AD vs AD Connector vs Simple AD, ask — AD Connector has a different `estimateFor` and is not covered by this module.

## Verification

- Captured HAR: `captures/calculator.aws_new_3.har` (local capture, not in repo) → `captures/saveAs/per-service/aWSDirectoryService.json` (eu-west-1, single flat line item, no subServices array).
- Shape is verified verbatim, including the unusual `columnFormIPM_*.value` array-of-row-objects pattern and the human-readable string keys.
- Pricing math reconstructs the captured `$481.80` within ~$7 using assumed US rates; **always pull live eu-west-1 (or the user's region) rates from the Pricing API before quoting**.
- AD Connector and Simple AD are **NOT covered** — capture HAR before quoting them.

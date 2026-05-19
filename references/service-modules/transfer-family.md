# AWS Transfer Family (`aWSTransferForSFTP` group)

Transfer Family is a **group** service. The captured form has one sub-service: **Web Apps**. The legacy SFTP/FTP/FTPS server endpoints (the original "Transfer for SFTP" product) and the protocol-specific data-transferred + user-hour SKUs are **not in this capture** — do not quote them from this module without first capturing a HAR that includes them.

Key naming quirk: the group `serviceCode` is `aWSTransferForSFTP` (lowercase `a`, uppercase `WS`) even though Transfer Family covers more than SFTP. Copy verbatim.

## Group-level header

```json
{
  "serviceCode":  "aWSTransferForSFTP",
  "estimateFor":  "TransferFamilySubServiceSelector",
  "version":      "0.0.16",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "AWS Transfer Family",
  "description":  null,
  "subServices":  [ ... ],
  "serviceCost":  { "monthly": <sum> }
}
```

## subServices

### Web Apps (`webApps`)

```jsonc
{
  "serviceCode":  "webApps",
  "estimateFor":  "awsTransferForWebApps",
  "version":      "0.0.7",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "numberOfWebApps": {"value": "2"}     // web-app units; each unit = one entitlement of capacity
  },
  "serviceCost": { "monthly": <computed> }
}
```

`numberOfWebApps` is in **units**, not user counts. One unit covers a fixed capacity baseline (currently ~200 concurrent users per unit per AWS documentation — verify in the AWS pricing page when quoting; units scale linearly).

### Other Transfer Family sub-services seen in the form but NOT in this capture

| Capability | Suspected sub-service serviceCode | Notes |
|---|---|---|
| SFTP server endpoint | TBD (likely `sftpEndpoint` or `protocolEnabledServer`) | Per-hour server-enabled SKU + per-GB upload/download |
| FTPS server endpoint | TBD | Same per-hour + per-GB pattern |
| FTP server endpoint | TBD | Same per-hour + per-GB pattern |
| AS2 connectors | TBD | Per-message or per-hour |
| SFTP connectors | TBD | Per-call SKU |

Capture a HAR that exercises a non-Web-Apps Transfer Family flow before populating any of the above. The selector `TransferFamilySubServiceSelector` does support them — the SPA renders them on the same form.

## Pricing API filters

```
--service-code AWSTransfer
--filter regionCode=<region>
```

For Web Apps look for SKUs with `usagetype` containing `WebApps-Units-Hrs` (or similar) — eu-west-1 rate from capture is exactly $0.50/unit/hour (`$730 / 730h / 2 units`).

For the legacy SFTP/FTP/FTPS endpoints, filter further by `operation` and `usagetype`: per-protocol server-hour and per-GB-up/down SKUs. Run `get-attribute-values --service-code AWSTransfer --attribute usagetype` to enumerate.

## Multipliers / formula

```
# Web Apps
webApps.monthly = numberOfWebApps * webapp_unit_per_hour_rate * 730
```

Verified at eu-west-1: `2 * $0.50 * 730 = $730.00`. **Matches captured `$730` exactly.**

```
# Server-endpoint protocols (NOT captured here — do not use without verification)
protocol.monthly = (server_hours * per_hour_rate)
                 + (data_uploaded_GB * upload_per_gb_rate)
                 + (data_downloaded_GB * download_per_gb_rate)
```

## configSummary template

Captured:

```
Total number of web app units (<N>)
```

For protocol endpoints, when those sub-services are added: AWS's standard phrasing is something like `SFTP server (<N> enabled), Upload (<X> GB/month), Download (<X> GB/month)` — re-check against a capture before relying on the wording.

## Defaults

| Field | Default | Why |
|---|---|---|
| numberOfWebApps | "0" (omit `webApps` sub-service entirely if not mentioned) | Per-unit hourly is non-trivial ($0.50/h ≈ $365/unit/mo); never assume a unit |

If the user says "Transfer Family" or "Transfer for SFTP" without specifying web apps vs SFTP/FTPS/FTP endpoints, **ask** — the price models are completely different and cost varies by an order of magnitude.

## Verification

- Captured HAR: `captures/calculator.aws_new_3.har` → `captures/saveAs/per-service/aWSTransferForSFTP.json` (eu-west-1, single line item, 1 sub-service: web apps with `numberOfWebApps: "2"`).
- Web Apps formula matches captured `$730` exactly (2 units × $0.50/h × 730h).
- **SFTP/FTPS/FTP server endpoints and AS2/SFTP connectors are NOT covered** — refuse to quote them from this module; capture HAR first.

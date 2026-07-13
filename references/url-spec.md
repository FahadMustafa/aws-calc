# Calculator endpoint contracts

Verified May 2026 against `calculator.aws`. All endpoints are public and unauthenticated; no SigV4, no Cognito, no API key.

## Save

```
POST https://dnd5zrqcec4or.cloudfront.net/Prod/v2/saveAs
Content-Type: application/json
Origin: https://calculator.aws
Referer: https://calculator.aws/

<saveAs body — see references/body-schema.md>
```

Response is an API Gateway Lambda-proxy envelope:

```json
{"statusCode": 201,
 "body": "{\"message\":\"The file name is <40hex>\",\"savedKey\":\"<40hex>\"}",
 "isBase64Encoded": false,
 "headers": {...}}
```

`savedKey` is 40 lowercase hex chars. The server normalizes the body before persisting, so the savedKey is not a stable hash of what you POSTed — read it from the response.

`scripts/create_estimate.py` already implements this. Use it; do not hand-roll the POST.

## Load

```
GET https://d3knqfixx3sbls.cloudfront.net/<savedKey>
```

Returns the saved JSON body verbatim (pretty-printed by the server). HTTP 200 with a non-empty payload means the share URL will render. Use this in the verification step.

## Share URL

The SPA constructs the share URL by substituting the `id=` query param. Final form:

```
https://calculator.aws/#/estimate?id=<savedKey>
```

When opened, the SPA fetches the load URL, hydrates its state, and displays the **stored** `serviceCost`/`totalCost` verbatim — it does **not** silently recompute. Recompute is user-initiated: the SPA shows a "prices may be out of date" affordance, and only when the recipient clicks **Update** does it re-derive each line from `calculationComponents` against the current Price List API. See SKILL.md's operating note "On what the recipient actually sees" for the full model. Implications:

- The stored `serviceCost` is the default display — a recipient who never clicks Update sees exactly the numbers you stored, so its accuracy is first-class.
- `calculationComponents` must survive a recompute: wrong field names/types or a bad opaque token makes Update render `$0` or fail with *"isn't compatible with your original inputs"*, leaving a broken line the recipient cannot fix.
- Both must agree — the `serviceCost` you store should equal what the cc recomputes to at today's prices, or the estimate visibly jumps on Update.

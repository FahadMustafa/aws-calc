# Amazon Bedrock (`amazonBedrock` group)

`serviceCode` is `amazonBedrock`, `estimateFor` is `amazonBedrockClassesGroup`. **Group** service whose `subServices[]` array carries one entry per model family. The captured sub-service is for the Anthropic family (`serviceCode: anthropic`, `estimateFor: anthropic`); other model providers (Amazon, Cohere, Meta, AI21, Mistral, Stability) are separate sub-service `serviceCode` values that the SPA renders on their own forms — **not in this capture**.

This module covers **Anthropic** + **In-Region On-Demand Standard tier** only. Other inference routes (Cross-region, Provisioned Throughput, Batch) and other tiers/feature flags use distinct sets of cc keys with different suffixes.

> **Hard precondition (silent-$0 hazard).** The model and cache rates are selected by opaque tokens (`modelSelectionIRstan`, `selectedModelIRstan`, `cacheReadIRstan`, `cacheWriteIRstan`). If any token is wrong or unknown, the SPA cannot decode it and renders the line as **$0** on the recipient's "Update" — regardless of what `serviceCost.monthly` you stored. Therefore: **only emit a Bedrock line when every token is either (a) the captured Anthropic token set below, or (b) harvested from a fresh HAR for the exact model.** After computing, assert `serviceCost.monthly > 0` for any non-zero request volume (the skill's global invariant); if it's $0 with real usage, you used a bad token — refuse the line instead. The model-name → token mapping is not yet reverse-engineered, so in practice this module can only price the one captured model without a new HAR.

## Group-level header

```json
{
  "serviceCode":  "amazonBedrock",
  "estimateFor":  "amazonBedrockClassesGroup",
  "version":      "0.0.52",
  "region":       "<code>",
  "regionName":   "<display>",
  "serviceName":  "Amazon Bedrock",
  "description":  null,
  "subServices":  [ ... one per model family ... ],
  "serviceCost":  { "monthly": <sum> }
}
```

`configSummary` on the group is the joined sub-service summaries.

## subServices

### Anthropic — In-Region On-Demand Standard (`anthropic` / `estimateFor: anthropic`)

```jsonc
{
  "serviceCode":  "anthropic",
  "estimateFor":  "anthropic",
  "version":      "0.0.37",
  "region":       "<code>",
  "description":  null,
  "calculationComponents": {
    "location":                       {"value": "ir"},          // "ir" = In-Region; cross-region paths use different code
    "tierIR":                         {"value": "standard"},    // "standard" tier (other inference tier values not captured)

    "modelSelectionIRstan":           {"value": "<opaque-token>"},   // model family selector — opaque hash
    "selectedModelIRstan":            {"value": "<opaque-token>"},   // specific model within the family — opaque hash

    "avgRequestsPerMinIRstan":        {"value": "1"},
    "hoursPerDayAtThisRateIRstan":    {"value": "8"},
    "avgInputTokensPerRequestIRstan": {"value": "1"},
    "avgOutputTokensPerRequestIRstan":{"value": "1"},

    // Image inputs (Claude vision); set imageInputIRstan: "0" to disable image fields
    "imageInputIRstan":               {"value": "1"},            // "1" = images enabled, "0" = text-only
    "avgImagesPerRequestIRstan":      {"value": "1"},
    "avgImageLengthInPixelsIRstan":   {"value": "100"},          // image height L (pixels)
    "avgImageWidthInPixelsIRstan":    {"value": "100"},          // image width W (pixels)

    // Prompt caching
    "withPromptCachingIRstan":        {"value": "1"},            // "1" = caching enabled
    "cacheRateIRstan":                {"value": "50"},           // cache hit rate as a percentage 0-100
    "cacheReadIRstan":                {"value": "<opaque-token>"}, // cache-read-rate enum token (read-from-cache rate variant)
    "cacheWriteIRstan":               {"value": "<opaque-token>"}  // cache-write-rate enum token (write-to-cache rate variant)
  },
  "serviceCost": { "monthly": <computed> }
}
```

Field-name conventions to copy verbatim:
- The suffix `IRstan` stands for **I**n-**R**egion **stan**dard tier. Cross-region inference and other tiers use different suffixes — capture HAR before using them.
- `location: "ir"` and `tierIR: "standard"` together select the In-Region Standard form. Other valid `location` values include cross-region variants (`xr*`-prefixed fields, not captured).

### Opaque tokens: model selection + cache rates

Four cc fields carry opaque 43-char URL-safe-base64 tokens that the SPA dereferences in its pricing-catalog lookup at calculation time:

| Field | Purpose | Captured token | Maps to |
|---|---|---|---|
| `modelSelectionIRstan` | Model family selector | `IL0BVf3Bmmr22TrGlUfHnPwVaiStbtOD-UyMVzK25bg` | Anthropic (captured); other families would have different tokens |
| `selectedModelIRstan` | Specific model within the family | `VAgU0B18jsXx-EUOFzoOdJKya4ShUCjz2HUNlOpDZLM` | (model not derivable from configSummary alone) |
| `cacheReadIRstan` | Cache-read pricing variant | `n9r1OkCw7sahKrcm5k_dLlzEu09FwTSCVv5QwmP_Hs4` | Cache-read rate enum |
| `cacheWriteIRstan` | Cache-write pricing variant | `mJCg-f97ByF7pKaysTOJs737vV6RxBfUYYMwhpWBEvU` | Cache-write rate enum |

These tokens are `RegionlessRateCode` values from the SPA's public catalogs at:

- `https://calculator.aws/pricing/2.0/meteredUnitMaps/bedrock/USD/current/bedrock.json` (~2 MB)
- `https://calculator.aws/pricing/2.0/meteredUnitMaps/bedrockfoundationmodels/USD/current/bedrockfoundationmodels.json` (~1.1 MB)

Unlike `amazon-mq.md`'s `mq.json` catalog (which has friendly keys like `"RabbitMQ Active Standby mq m5.large"` that resolve directly to tokens), **the Bedrock catalogs are keyed only by `RegionlessRateCode`** — no model-name metadata is embedded in `regions[*][<token>]`. The model-name → token mapping must come from one of:

1. **bundle.js's amazonBedrock model registry** (location and structure not yet fully reverse-engineered)
2. **`https://d1qsjq9pzbk1k6.cloudfront.net/data/amazonBedrock/en_US.json`** — a ~2 KB descriptor file that the SPA also fetches; investigation in progress.

Until that mapping is documented (tracked as a follow-up beads issue), the safe path is:

1. **For the one known Anthropic model token combo above**: emit using the captured tokens verbatim and quote with the standard formula.
2. **For any other model / cache configuration**: capture a fresh HAR with the SPA configured for the target model and harvest its four tokens, or refuse the line item and ask the user.

See `references/opaque-tokens.md` for the general resolution pattern and the `scripts/resolve_token.py` helper (which already handles the catalog fetch; the Bedrock-specific name→token chain is the missing piece).

**Do not** substitute a different model's tokens while overriding `serviceCost.monthly` — the SPA recomputes from cc on load and renders a `$0` line when unknown tokens don't decode.

## Pricing API filters

```
--service-code AmazonBedrock
--filter regionCode=<region>
```

Then filter by `usagetype` and `feature`. Look for:
- `<region>-Bedrock-input-tokens-<model-id>` — per-1K input tokens
- `<region>-Bedrock-output-tokens-<model-id>` — per-1K output tokens
- `<region>-Bedrock-cache-read-tokens-<model-id>` — discounted per-1K read-from-cache rate (typically ~10% of input)
- `<region>-Bedrock-cache-write-tokens-<model-id>` — premium per-1K write-to-cache rate (typically 1.25× input)
- Image-input SKUs (per-image, varies by resolution bracket)

Run `get-attribute-values --service-code AmazonBedrock --attribute usagetype` to enumerate. The `<model-id>` segment is the long human-readable model identifier (e.g. `claude-sonnet-4-6-20251130`), not the opaque token from the saveAs body — the mapping must be kept manually.

## Multipliers / formula

```
# Tokens per month
requests_per_month   = avgRequestsPerMin * 60 * hoursPerDayAtThisRate * 30        # SPA uses 30-day month for Bedrock
input_tokens_month   = requests_per_month * avgInputTokensPerRequest
output_tokens_month  = requests_per_month * avgOutputTokensPerRequest

# Cache impact (only when withPromptCaching = "1") — UNVERIFIED, see warning below
cache_hit_fraction   = cacheRate / 100
cache_read_tokens    = input_tokens_month * cache_hit_fraction
cache_write_tokens   = input_tokens_month * (1 - cache_hit_fraction)              # tokens written into the cache
billable_input_tok   = input_tokens_month * (1 - cache_hit_fraction)              # uncached portion at full input rate

input_cost           = billable_input_tok / 1000 * input_per_1k
output_cost          = output_tokens_month / 1000 * output_per_1k
cache_read_cost      = cache_read_tokens / 1000 * cache_read_per_1k
cache_write_cost     = cache_write_tokens / 1000 * cache_write_per_1k

# Image inputs (when imageInputIRstan = "1")
images_per_month     = requests_per_month * avgImagesPerRequest
image_cost           = images_per_month * image_rate(L, W)                        # rate depends on resolution bracket

serviceCost.monthly  = input_cost + output_cost + cache_read_cost + cache_write_cost + image_cost
```

> **Two unverified assumptions in this formula — flag both, and prefer to disable caching until reconciled:**
> 1. **30-day month.** Bedrock uses `× 30` (line above), unlike the 730-hour convention everywhere else in the skill. At the captured $1.02 volume this can't be confirmed; if the SPA actually uses 730/24 ≈ 30.42 days or another constant, request volume (and cost) is off by ~1.4%.
> 2. **Prompt-cache split likely double-counts.** As written, the uncached fraction `input_tokens × (1 - hit)` is charged the **full input rate** (`billable_input_tok`) **and** the **cache-write rate** (`cache_write_tokens`) simultaneously. Real Anthropic caching charges cache *writes* (premium, ~1.25×) on the first miss of *cacheable* content and cache *reads* (discount, ~0.1×) on hits; plain non-cacheable input pays the input rate once. Charging the same token pool at both full-input and cache-write overstates cost. Until this is reconciled against a cache-enabled, non-trivial-volume capture, set `withPromptCachingIRstan: "0"` (and `cacheRateIRstan: "0"`) and quote without caching, or capture a HAR.

Captured `serviceCost.monthly: $1.02` at eu-west-1 with the captured inputs is a near-minimum estimate (1 req/min × 8h × 1 token each, 50% cache, 1 small image). Exact rate confirmation needs a higher-volume capture — at $1.02/month the math is dominated by image fees and rounding, so it's not a useful arithmetic anchor for the per-1K-token rates. **Build a follow-up capture with avgRequestsPerMin=100, both image and cache disabled, to isolate the per-1K input/output rates for whichever model the captured tokens select.**

## configSummary template

Match captured phrasing exactly:

```
Select the inference route (In Region), Select the inference type (On Demand - Standard), Average requests per minute (<N>), Hours per day at this rate (<N>), Average input tokens per request (<N>), Average output tokens per request (<N>), Average input images per request (<N>), Average input image length in pixels (L) (<N>), Average input image width in pixels (W) (<N>)
```

Add cache fields to the summary when `withPromptCachingIRstan: "1"` (the SPA appends them; exact phrasing not captured for the cache-enabled case at non-zero volume).

## Defaults

| Field | Default | Why |
|---|---|---|
| location | "ir" | Only In-Region captured; refuse cross-region requests until a capture exists |
| tierIR | "standard" | Only Standard tier captured |
| modelSelectionIRstan + selectedModelIRstan | none — **ask for a HAR** unless using the captured Anthropic token pair | Tokens are opaque; can't be set without a per-model HAR |
| avgRequestsPerMinIRstan | "1" | Low default; ask the user for realistic volume — order-of-magnitude impacts cost massively |
| hoursPerDayAtThisRateIRstan | "8" | One business shift — flag the assumption in breakdown |
| avgInputTokensPerRequestIRstan | "500" | Typical short prompt; flag |
| avgOutputTokensPerRequestIRstan | "500" | Typical short response; flag |
| imageInputIRstan | "0" | Default off; only enable when user mentions vision/images |
| avgImagesPerRequestIRstan | "0" when imageInputIRstan is "0", else "1" | |
| withPromptCachingIRstan | "0" | Off by default; cache-rate fields only meaningful when caching is on |
| cacheRateIRstan | "0" | 0% hit rate when caching is off |
| cacheReadIRstan + cacheWriteIRstan | none — **use captured tokens** | Opaque enum tokens |

If the user says "Bedrock" without specifying a model, **ask** — per-token rates differ by 100x+ across model families and sizes. Refuse to quote without a known model.

## Verification

- Captured HAR: `captures/calculator.aws_new_6.har` → `captures/saveAs/per-service/amazonBedrock.json` (eu-west-1, group with one Anthropic sub-service).
- `serviceCost.monthly: $1.02` is too small to reconstruct meaningfully from per-1K-token rates (volume too low; rounding and image fees dominate). **Formula is structural — rates must be confirmed with a second, higher-volume capture before quoting.**
- Only one model+cache token combination is known. Cross-region inference, Provisioned Throughput, and Batch inference paths are **NOT covered**.
- Image-input rate tables are unknown — capture a HAR with high image volume to derive.
- Non-Anthropic providers (Amazon Nova, Cohere, Meta, AI21, Mistral, Stability) are **NOT covered** — each is a separate sub-service `serviceCode` with its own form.

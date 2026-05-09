# aws-calc

Generate populated, shareable `https://calculator.aws/#/estimate?id=...` links by calling the calculator's backend directly. Verdict: **yes**, the save endpoint is unauthenticated; the SPA recomputes prices from `calculationComponents` on load, so faithful estimates only require the right field shapes plus accurate Pricing API rates.

## Outputs

- [`findings.md`](findings.md) — write-up: endpoints, auth, request/response schemas, share-URL derivation, replay instructions
- [`poc/create_estimate.py`](poc/create_estimate.py) — minimal Python replay (input JSON → share URL)
- **`~/.claude/skills/aws-calc/`** — Claude skill that turns a natural-language brief into a populated share URL by combining the AWS Price List API with the calculator's saveAs body shape. Supports EC2, RDS Postgres, S3, VPC; extension recipe in `references/service-modules/_template.md`. Smoke-tested end-to-end (Pricing API rates → skill formulas → SPA serviceCost match exactly: $68.62).

## Repo layout

- `captures/` — HAR + extracted bundle/config used during discovery
- `poc/` — Python replay script + sample saveAs body
- `notes.md` — running observations from the spike
- `findings.md` — final write-up

## Running the PoC standalone

```
cd poc
pip install -r requirements.txt
python create_estimate.py sample_input.json
```

Prints a share URL on stdout, non-zero exit on failure.

## Using the skill

Invoke from any Claude Code session:

> Use aws-calc to build a share link for: 3× t3.medium Linux on-demand us-east-2, 100% util, 50 GB gp3 each.

The skill reads the brief, queries the Pricing API via `--profile zaintech-cloudtools` (override per-invocation), constructs the saveAs body, posts it, and prints the share URL plus a Markdown line-item breakdown.

Spec for the original spike: `~/.claude/plans/i-want-to-automate-robust-pizza.md`.

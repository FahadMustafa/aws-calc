# aws-calc

Generate populated, shareable `https://calculator.aws/#/estimate?id=...` links by calling the calculator's backend directly. Save endpoint is unauthenticated; the SPA recomputes prices from `calculationComponents` on load, so faithful estimates only require the right field shapes plus accurate Pricing API rates.

This repo is the source of truth for the **aws-calc** Claude skill. The deployed copy at `~/.claude/skills/aws-calc/` is a mirror; deploy with `./deploy.sh`.

## Repo layout

- `SKILL.md` — skill entry point (read by Claude). Holds the workflow, versioned via the frontmatter `version` field.
- `scripts/` — `pricing_client.py` (Price List API queries), `create_estimate.py` (POSTs saveAs body, prints share URL).
- `references/`
  - `body-schema.md`, `url-spec.md`, `service-codes.md` — top-level conventions.
  - `service-modules/` — one file per supported service (33 services as of v0.2.0). `_template.md` is the extension recipe.
- `poc/` — minimal standalone Python replay (input JSON → share URL).
- `captures/` — gitignored. HAR captures + extracted bundle/config used to derive `calculationComponents` shapes. `extract_saveas.py` streams a HAR and emits per-service saveAs bodies under `captures/saveAs/per-service/`.
- `findings.md`, `notes.md` — original discovery write-up.
- `deploy.sh` — rsync skill content (`SKILL.md`, `scripts/`, `references/`) to `~/.claude/skills/aws-calc/`.

## Develop → deploy loop

```
# edit SKILL.md, scripts/, references/, bump SKILL.md version when shape changes
./deploy.sh           # mirrors to ~/.claude/skills/aws-calc/
git commit -am "..."
```

The `references/service-modules/_template.md` recipe and the `captures/saveAs/per-service/<serviceCode>.json` ground-truth files are how new service modules get added — anchor every new module to a real captured saveAs body, don't improvise shapes.

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

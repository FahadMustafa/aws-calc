# aws-calc

Generate populated, shareable [AWS Pricing Calculator](https://calculator.aws) estimate links (`https://calculator.aws/#/estimate?id=...`) programmatically, by calling the calculator's backend save endpoint directly. Packaged as a [Claude Code](https://claude.com/claude-code) skill, with a minimal standalone Python proof of concept.

> **Unofficial.** This project is not affiliated with or endorsed by AWS. It uses an undocumented, unauthenticated endpoint discovered by inspecting the calculator SPA's network traffic; AWS may change or remove it at any time without notice. Estimates it produces carry the same non-binding status as ones built by hand in the calculator UI.

## How it works

The calculator's save endpoint is unauthenticated. On load the SPA displays the **stored** `serviceCost` verbatim — it does not silently recompute; recompute is user-initiated (the recipient clicks **Update**, re-deriving each line from `calculationComponents` against the current Pricing API). So a faithful estimate needs both an accurate stored `serviceCost` (the default display) and a recompute-safe `calculationComponents` shape, and the two must agree. See SKILL.md's operating note "On what the recipient actually sees".

## Repo layout

- `SKILL.md` — skill entry point (read by Claude). Holds the workflow, versioned via the frontmatter `version` field.
- `scripts/` — `pricing_client.py` (Price List API queries), `create_estimate.py` (POSTs saveAs body, prints share URL), `check_versions.py` (form-version drift check), `extract_saveas.py` (streams a HAR capture, extracts saveAs bodies).
- `references/`
  - `body-schema.md`, `url-spec.md`, `service-codes.md` — top-level conventions.
  - `service-modules/` — one file per supported service (42 services as of v0.8.x; see `references/service-codes.md` for the current index). `_template.md` is the extension recipe.
- `poc/` — minimal standalone Python replay (input JSON → share URL).
- `captures/` — gitignored (HAR files are large and may contain session tokens). Holds local HAR captures and the extracted ground-truth saveAs bodies under `captures/saveAs/per-service/`.
- `findings.md` — original discovery write-up (endpoints, auth, schema, verification log).
- `deploy.sh` — rsync skill content (`SKILL.md`, `scripts/`, `references/`) to `~/.claude/skills/aws-calc/`.

## Using the skill

Install by mirroring the skill content into your Claude Code skills directory:

```
./deploy.sh           # copies SKILL.md, scripts/, references/ to ~/.claude/skills/aws-calc/
```

Then invoke from any Claude Code session:

> Use aws-calc to build a share link for: 3× t3.medium Linux on-demand us-east-2, 100% util, 50 GB gp3 each.

The skill reads the brief, queries the AWS Price List API (using your configured AWS credentials — set a profile with `--profile <your-profile>`), constructs the saveAs body, posts it, and prints the share URL plus a Markdown line-item breakdown.

## Running the PoC standalone

No Claude required — the PoC replays a prepared input JSON:

```
cd poc
pip install -r requirements.txt
python create_estimate.py sample_input.json
```

Prints a share URL on stdout, non-zero exit on failure.

## Contributing new service modules

The `references/service-modules/_template.md` recipe and captured `saveAs` ground-truth files are how new service modules get added — anchor every new module to a real captured saveAs body (record a HAR while building the estimate in the calculator UI, then extract with `scripts/extract_saveas.py`), don't improvise shapes.

## License

[MIT](LICENSE)

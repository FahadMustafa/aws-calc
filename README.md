# aws-calc

Generate populated, shareable [AWS Pricing Calculator](https://calculator.aws) estimate links (`https://calculator.aws/#/estimate?id=...`) programmatically, by calling the calculator's backend save endpoint directly. Packaged as a [Claude Code](https://claude.com/claude-code) skill, with scripts that also work standalone.

> **Unofficial.** This project is not affiliated with or endorsed by AWS. It uses an undocumented, unauthenticated endpoint discovered by inspecting the calculator SPA's network traffic; AWS may change or remove it at any time without notice. Estimates it produces carry the same non-binding status as ones built by hand in the calculator UI.

## Install

```bash
git clone https://github.com/FahadMustafa/aws-calc.git
cd aws-calc
pip install -r requirements.txt
./deploy.sh    # installs the skill to ~/.claude/skills/aws-calc/
```

`deploy.sh` mirrors the skill content (`SKILL.md`, `scripts/`, `references/`) into your Claude Code skills directory. For the Pricing API queries you need AWS credentials reachable via the standard boto3 chain (any account works — the Price List API is a global, low-cost read).

## Usage

### As a Claude Code skill

Ask Claude in any session:

> Use aws-calc to build a share link for: 3× t3.medium Linux on-demand us-east-2, 100% util, 50 GB gp3 each.

The skill reads the brief, queries the AWS Price List API (name an AWS profile in your brief, or it uses the default credential chain), constructs the saveAs body, posts it, and replies with the share URL plus a Markdown line-item breakdown.

### Standalone: post a prepared body

No Claude required — replay any saveAs body JSON and get a share URL back:

```bash
python scripts/create_estimate.py references/examples/sample-saveas-body.json
# → https://calculator.aws/#/estimate?id=<40-hex-key>
```

Exit 0 on success; warns on stderr if any line item carries a suspicious $0 cost.

### Standalone: query the Pricing API

```bash
python scripts/pricing_client.py --profile <your-profile> get-products \
  --service-code AmazonEC2 --filter regionCode=us-east-2 --filter instanceType=t3.medium
```

## How it works

The calculator's save endpoint is unauthenticated. On load the SPA displays the **stored** `serviceCost` verbatim — it does not silently recompute; recompute is user-initiated (the recipient clicks **Update**, re-deriving each line from `calculationComponents` against the current Pricing API). So a faithful estimate needs both an accurate stored `serviceCost` (the default display) and a recompute-safe `calculationComponents` shape, and the two must agree. See SKILL.md's operating note "On what the recipient actually sees". Full discovery write-up (endpoints, auth, schema, verification log): [`findings.md`](findings.md).

## Repo layout

- `SKILL.md` — skill entry point (read by Claude). Holds the workflow, versioned via the frontmatter `version` field.
- `scripts/` — `pricing_client.py` (Price List API queries), `create_estimate.py` (POSTs saveAs body, prints share URL), `check_versions.py` (form-version drift check), `extract_saveas.py` (streams a HAR capture, extracts saveAs bodies).
- `references/`
  - `body-schema.md`, `url-spec.md`, `service-codes.md` — top-level conventions.
  - `examples/` — captured ground-truth saveAs bodies, including `sample-saveas-body.json` (EC2 ×2 + RDS PostgreSQL + S3 + VPC).
  - `service-modules/` — one file per supported service (42 services as of v0.8.x; see `references/service-codes.md` for the current index). `_template.md` is the extension recipe.
- `captures/` — gitignored (HAR files are large and may contain session tokens). Holds local HAR captures and extracted saveAs bodies.
- `findings.md` — original discovery write-up.
- `deploy.sh` — rsync skill content to `~/.claude/skills/aws-calc/`.

## Contributing new service modules

The `references/service-modules/_template.md` recipe and captured `saveAs` ground-truth files are how new service modules get added — anchor every new module to a real captured saveAs body (record a HAR while building the estimate in the calculator UI, then extract with `scripts/extract_saveas.py`), don't improvise shapes.

## License

[MIT](LICENSE)

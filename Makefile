.PHONY: test check-versions deploy

# Run the test suite. No network: every test works off local files.
test:
	python3 -m pytest -q

# Compare each module's pinned form version against live calculator.aws (hits the network).
check-versions:
	python3 scripts/check_versions.py

# Mirror SKILL.md, scripts/ and references/ into ~/.claude/skills/aws-calc/.
deploy:
	./deploy.sh

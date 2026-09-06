#!/usr/bin/env bash
# Sync the skill source from this repo to ~/.claude/skills/aws-calc/.
# Source of truth is the repo; ~/.claude/skills/aws-calc/ is the deploy target.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${HOME}/.claude/skills/aws-calc"

mkdir -p "$TARGET"
rsync -a --delete --delete-excluded \
    --exclude='__pycache__/' \
    --include='SKILL.md' \
    --include='scripts/***' \
    --include='references/***' \
    --exclude='*' \
    "$REPO_DIR/" "$TARGET/"

VERSION=$(awk -F'"' '/^version:/ {print $2; exit}' "$REPO_DIR/SKILL.md")
echo "Deployed aws-calc v${VERSION} to ${TARGET}"

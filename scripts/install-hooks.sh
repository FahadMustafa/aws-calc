#!/usr/bin/env bash
# Install a post-commit hook that deploys the skill automatically after every
# commit on this repo. Idempotent: safe to re-run.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="$REPO_ROOT/.git/hooks/post-commit"
MARKER="# aws-calc-deploy"

if [[ -e "$HOOK" ]] && ! grep -qF "$MARKER" "$HOOK"; then
  echo "post-commit hook exists and is not ours; not overwriting ($HOOK)" >&2
  exit 1
fi

cat > "$HOOK" <<EOF
#!/usr/bin/env bash
$MARKER
exec "\$(git rev-parse --show-toplevel)/deploy.sh" >/dev/null 2>&1 || true
EOF
chmod +x "$HOOK"

echo "Installed post-commit hook at $HOOK"

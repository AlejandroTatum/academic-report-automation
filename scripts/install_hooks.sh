#!/usr/bin/env bash
# Point this clone's Git hooks at the versioned .githooks/ directory.
#
#   ./scripts/install_hooks.sh
#
# Run once per clone. `.git/hooks/` is not versioned, so hooks committed to the
# repository only take effect after Git is told where to find them. This sets
# `core.hooksPath`, which is per-clone configuration and is why a fresh clone
# needs this step even though the hooks themselves travel with the repo.
#
# After this, a `git pull` that changes anything under skills/ re-syncs the
# agent runtimes automatically.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HOOKS_DIR=".githooks"

if [[ ! -d "$HOOKS_DIR" ]]; then
  echo "!! $HOOKS_DIR/ not found — are you running this from the repository?" >&2
  exit 1
fi

# The hooks must be executable in the index too, or a fresh clone gets files
# Git will refuse to run.
for hook in "$HOOKS_DIR"/post-* "$HOOKS_DIR"/lib/*.sh; do
  [[ -f "$hook" ]] || continue
  if [[ ! -x "$hook" ]]; then
    echo "!! $hook is not executable — fix with: chmod +x $hook" >&2
    exit 1
  fi
done

CURRENT="$(git config --local --get core.hooksPath || true)"

if [[ "$CURRENT" == "$HOOKS_DIR" ]]; then
  echo "Already installed: core.hooksPath = $HOOKS_DIR"
else
  git config --local core.hooksPath "$HOOKS_DIR"
  echo "Installed: core.hooksPath = $HOOKS_DIR"
  [[ -n "$CURRENT" ]] && echo "  (replaced previous value: $CURRENT)"
fi

echo
echo "Active hooks:"
for hook in "$HOOKS_DIR"/post-*; do
  [[ -f "$hook" ]] && echo "  - $(basename "$hook")"
done
echo
echo "A pull that changes skills/ now re-syncs the agent runtimes."
echo "To sync by hand at any time: ./scripts/sync_skills.sh --apply"

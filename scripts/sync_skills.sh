#!/usr/bin/env bash
# Sync skills from this repo (source of truth) to both agent runtimes.
#
#   ./scripts/sync_skills.sh          # show what would change
#   ./scripts/sync_skills.sh --apply  # write the changes
#
# The repo is authoritative. Anything edited directly in a runtime directory is
# overwritten, so edit here and sync outward — never the other way around.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/skills"

TARGETS=(
  "$HOME/.config/opencode/skills"
  "$HOME/.claude/skills"
)

SKILLS=(
  academic-report-builder
  academic-visual-builder
  research-workflow
)

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

if [[ $APPLY -eq 0 ]]; then
  echo "DRY RUN — nothing is written. Re-run with --apply to sync."
  RSYNC_FLAGS=(-ai --dry-run)
else
  RSYNC_FLAGS=(-ai)
fi

# Gate the sync on the static contract tests. A skill that fails its own
# routing contract must never reach a runtime directory.
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  echo "==> Running skill contract tests"
  "$REPO_ROOT/.venv/bin/python" -m pytest "$REPO_ROOT/tests/skills/" -q
else
  echo "!! .venv not found — skipping contract tests (run: python3 -m venv .venv)" >&2
fi

for target in "${TARGETS[@]}"; do
  echo "==> $target"
  if [[ ! -d "$target" ]]; then
    echo "    skipped: runtime directory does not exist"
    continue
  fi
  for skill in "${SKILLS[@]}"; do
    [[ -d "$SRC/$skill" ]] || continue
    [[ $APPLY -eq 1 ]] && mkdir -p "$target/$skill"
    # --delete keeps the runtime an exact mirror: reference files removed here
    # must disappear there too, or a stale rule keeps loading.
    # Exclusions are deliberate: *.bak-* are local rollback copies, and the
    # dot-directories are agent-harness scratch that must never reach a runtime.
    rsync "${RSYNC_FLAGS[@]}" --delete \
      --exclude '*.bak-*' \
      --exclude '.claude/' \
      --exclude '.opencode/' \
      --exclude '.DS_Store' \
      "$SRC/$skill/" "$target/$skill/"
  done
done

if [[ $APPLY -eq 0 ]]; then
  echo
  echo "DRY RUN complete. Re-run with --apply to write."
fi

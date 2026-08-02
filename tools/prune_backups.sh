#!/usr/bin/env bash
set -euo pipefail

root="/config/portfolio-architect-backups"
keep=5
apply=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --root) root="$2"; shift 2 ;;
    --keep) keep="$2"; shift 2 ;;
    --apply) apply=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ "$keep" =~ ^[0-9]+$ ]] || { echo "--keep must be a non-negative integer" >&2; exit 2; }
[ -d "$root" ] || { echo "Backup directory does not exist: $root" >&2; exit 1; }

mapfile -t backups < <(
  for directory in "$root"/*/; do
    [ -d "$directory" ] || continue
    printf '%s\t%s\n' "$(stat -c '%Y' "$directory")" "${directory%/}"
  done | sort -nr | cut -f2-
)

for ((index=keep; index<${#backups[@]}; index++)); do
  if [ "$apply" -eq 1 ]; then
    printf 'Removing %s\n' "${backups[$index]}"
    rm -rf -- "${backups[$index]}"
  else
    printf 'Would remove %s\n' "${backups[$index]}"
  fi
done

if [ "$apply" -eq 0 ]; then
  echo "Dry run only. Add --apply to remove the listed backups."
fi

#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 BACKUP_DIRECTORY [--restart]" >&2
  exit 2
}

[ "$#" -ge 1 ] || usage
backup="${1%/}"
restart="${2:-}"
[ -d "$backup/custom-component" ] || { echo "Missing $backup/custom-component" >&2; exit 1; }

stamp="$(date +%Y%m%d-%H%M%S)"
safety="/config/portfolio-architect-backups/pre-rollback-$stamp"
mkdir -p -- "$safety"
cp -a -- /config/custom_components/portfolio_architect "$safety/custom-component"
if [ -d /config/portfolio-architect ]; then
  cp -a -- /config/portfolio-architect "$safety/portfolio-data"
fi

rm -rf -- /config/custom_components/portfolio_architect
cp -a -- "$backup/custom-component" /config/custom_components/portfolio_architect
if [ -d "$backup/portfolio-data" ]; then
  rm -rf -- /config/portfolio-architect
  cp -a -- "$backup/portfolio-data" /config/portfolio-architect
fi

ha core check
printf 'Rollback restored from %s\nSafety backup created at %s\n' "$backup" "$safety"
if [ "$restart" = "--restart" ]; then
  ha core restart
else
  echo "Home Assistant was not restarted. Run 'ha core restart' after reviewing the result."
fi

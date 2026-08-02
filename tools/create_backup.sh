#!/usr/bin/env bash
set -euo pipefail

backup_root="${1:-/config/portfolio-architect-backups}"
stamp="$(date +%Y%m%d-%H%M%S)"
version="$(sed -n 's/^VERSION: Final = "\([^"]*\)"/\1/p' /config/custom_components/portfolio_architect/const.py)"
[ -n "$version" ] || version="unknown"
destination="$backup_root/v${version}-$stamp"

mkdir -p -- "$destination"
cp -a -- /config/custom_components/portfolio_architect "$destination/custom-component"
if [ -d /config/portfolio-architect ]; then
  cp -a -- /config/portfolio-architect "$destination/portfolio-data"
fi
printf '%s\n' "$destination"

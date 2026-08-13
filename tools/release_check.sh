#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

python -m compileall -q custom_components gateway/src home_assistant_app/portfolio_architect_gateway/src home_assistant_app/portfolio_architect_gateway_dkb/src home_assistant_app/portfolio_architect_gateway_trade_republic/src
python - <<'PY'
import json
from pathlib import Path
import yaml
root = Path('.')
for path in root.rglob('*.json'):
    if any(part in {'.git', 'dist', '.pytest_cache'} for part in path.parts):
        continue
    json.loads(path.read_text(encoding='utf-8'))
for path in root.rglob('*.yaml'):
    if any(part in {'.git', 'dist', '.pytest_cache'} for part in path.parts):
        continue
    yaml.safe_load(path.read_text(encoding='utf-8'))
PY
python tools/check_publication.py
python tools/check_privacy.py --root .
pytest -q
python tools/build_release.py --output dist
python tools/verify_release.py --dist dist
python tools/check_privacy.py --root . --dist dist

#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

dist="${1:-dist}"
expected_image="ghcr.io/gitleaks/gitleaks@sha256:691af3c7c5a48b16f187ce3446d5f194838f91238f27270ed36eef6359a574d9"
: "${GITLEAKS_IMAGE:?GITLEAKS_IMAGE must be set by the reviewed GitHub workflow}"
test "$GITLEAKS_IMAGE" = "$expected_image" || {
  echo "Unexpected Gitleaks image: the reviewed v8.30.0 digest is required" >&2
  exit 1
}

command -v docker >/dev/null
command -v git >/dev/null
command -v tar >/dev/null

git_dir="$(git rev-parse --git-dir)"
test -d "$git_dir"
commit_count="$(git rev-list --all --count)"
test "$commit_count" -gt 0 || {
  echo "Refusing secret scan: Git history is empty" >&2
  exit 1
}
echo "Gitleaks history preflight: ${commit_count} commit(s) reachable"

base="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/portfolio-architect-gitleaks-${GITHUB_RUN_ID:-local}-$$"
source_stage="${base}/source"
artifact_stage="${base}/artifacts"
rm -rf "$base"
mkdir -p "$source_stage"
trap 'rm -rf "$base"' EXIT

# Scan the exact tracked tree without .git metadata, local caches, or untracked files.
git archive --format=tar HEAD | tar -xf - -C "$source_stage"
python tools/check_privacy.py \
  --root . \
  --history \
  --dist "$dist" \
  --stage-dist-for-gitleaks "$artifact_stage"

docker run --rm \
  --network=none \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  -v "${source_stage}:/scan:ro" \
  "$GITLEAKS_IMAGE" dir -v /scan

# Feed Git's complete patch history explicitly to stdin. This avoids relying on
# Gitleaks' internal `git log` invocation and fails the pipeline if git itself
# cannot produce the history stream.
git log -p --all --no-ext-diff --text -- . | \
  docker run --rm -i \
    --network=none \
    --cap-drop=ALL \
    --security-opt=no-new-privileges \
    "$GITLEAKS_IMAGE" stdin -v

docker run --rm \
  --network=none \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  -v "${artifact_stage}:/scan:ro" \
  "$GITLEAKS_IMAGE" dir -v /scan

echo "Validated Gitleaks current tree, complete Git history, and release artifacts"

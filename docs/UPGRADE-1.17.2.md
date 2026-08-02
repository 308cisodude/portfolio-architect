# Upgrade to Portfolio Architect 1.17.2

Version 1.17.2 fixes the HACS archive layout shipped with v1.17.1. Runtime
behavior is unchanged from v1.17.1; the release retains its publication,
software-supply-chain, and local REST transport hardening.

## 1. Recover from an attempted v1.17.1 HACS download

The broken v1.17.1 HACS asset may have created this ignored nested integration:

```text
/config/custom_components/portfolio_architect/custom_components/portfolio_architect
```

Do not restart Home Assistant while the active root-level version markers still
report `1.17.0`. Remove only the nested directory:

```bash
rm -rf /config/custom_components/portfolio_architect/custom_components
```

Confirm that the working outer installation remains:

```bash
find /config/custom_components/portfolio_architect \
  -type f \
  -name manifest.json \
  -print \
  -exec grep -n '"version"' {} \;
```

At this point the command should find only the active root-level manifest.

## 2. Install v1.17.2 through HACS

Download v1.17.2 from the Portfolio Architect HACS page. A **Pending restart**
state is expected after the download.

Before restarting, verify the active files:

```bash
grep -n '"version"' \
  /config/custom_components/portfolio_architect/manifest.json

grep -n '^VERSION' \
  /config/custom_components/portfolio_architect/const.py

grep -n '^__version__' \
  /config/custom_components/portfolio_architect/engine/__init__.py

find /config/custom_components/portfolio_architect \
  -type f \
  -name manifest.json \
  -print \
  -exec grep -n '"version"' {} \;
```

All three active version markers must report `1.17.2`, and the `find` command must
show exactly one Portfolio Architect manifest at:

```text
/config/custom_components/portfolio_architect/manifest.json
```

Then run `ha core check` and restart Home Assistant. After restart, verify
`sensor.portfolio_architect_version` reports `1.17.2` and the existing live or
last-known-good portfolio remains available.

## 3. Manual installation

For a manual installation, upload
`portfolio-architect-v1.17.2-ha-dropin.zip` to `/config`, back up the current
custom component and Portfolio Architect data directory, extract the archive over
`/config`, run `ha core check`, and restart Home Assistant.

The manual drop-in intentionally contains the
`custom_components/portfolio_architect/` wrapper. Do not use the HACS
`portfolio_architect.zip` asset for a manual `/config` extraction.

## 4. Dashboard and Gateway

No dashboard replacement is required. The existing v1.16.3 bilingual dashboard
remains compatible.

No Gateway update is required. Gateway App v1.16.1 and later remain compatible.
The v1.17.2 Gateway package aligns release metadata only.

## 5. Publication source

Use a fresh v1.17.2 complete source archive rather than publishing from the
v1.17.1 tree. Configure the real repository metadata and validate the release:

```bash
python tools/configure_publication.py \
  --repository OWNER/portfolio-architect \
  --codeowner @OWNER
python tools/check_publication.py --strict
./tools/release_check.sh
```

The release verifier now enforces both channel-specific ZIP layouts and payload
identity after prefix normalization.
